"""
    Embed bokeh server session into flask framework
    Adapted from bokeh-master/examples/howto/serve_embed/flask_gunicorn_embed.py
"""

import os

try:
    import asyncio
except ImportError:
    raise RuntimeError("This example requires Python3 / asyncio")

from threading import Thread

from flask import Flask, render_template
from flask_cors import CORS

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.embed import server_document
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.sampledata.sea_surface_temperature import sea_surface_temperature
from bokeh.server.server import BaseServer
from bokeh.server.tornado import BokehTornado
from bokeh.server.util import bind_sockets


app = Flask(__name__)

app.config['CORS_HEADERS'] = 'Content-Type'
cors = CORS(app)


def graph_func(doc):
    dataframe = sea_surface_temperature.copy()
    source = ColumnDataSource(data=dataframe)

    plot = figure(x_axis_type='datetime', y_range=(0, 25),
                  y_axis_label='Temperature (Celsius)',
                  title="Sea Surface Temperature at 43.18, -70.43")
    plot.line(x='time', y='temperature', source=source)
    return doc.add_root(plot)



# can't use shortcuts here, since we are passing to low level BokehTornado
graph_app = Application(FunctionHandler(graph_func))


# each process will listen on its own port
sockets, port = bind_sockets("localhost", 0)


@app.route('/graph', methods=['GET'])
def graph_route():
    script = server_document(f"http://localhost:{port}/graph")
    return render_template("embed.html", script=script, framework="Flask")


@app.route('/env', methods=['GET'])
def env_route():
    env = '<p>'
    for  key, value in os.environ.items():
        env += f"<br>{key}: {value}"
    return env + '</p>'


def bk_worker():
    """ Worker thread to run the bokeh server once, so Bokeh document can be
        extracted for every http request.
    """
    asyncio.set_event_loop(asyncio.new_event_loop())

    env_port = os.environ.get('PORT', default='8000')

    websocket_origins = [f"0.0.0.0:{env_port}",
                         'localhost:{env_port}',
                         '127.0.0.1:8000',
                         f"safe-scrubland-67589.herokuapp.com:{env_port}"]

    bokeh_tornado = BokehTornado({'/graph': graph_app},
                                 extra_websocket_origins=websocket_origins)
    bokeh_http = HTTPServer(bokeh_tornado)
    bokeh_http.add_sockets(sockets)

    server = BaseServer(IOLoop.current(), bokeh_tornado, bokeh_http)
    server.start()
    server.io_loop.start()

t = Thread(target=bk_worker)
t.daemon = True
t.start()
