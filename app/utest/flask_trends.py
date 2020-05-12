"""Bokeh App with Flask

Returns:
    Bokeh Document -- Bokeh document
"""
import asyncio

from threading import Thread

from flask import Flask, render_template, request
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.embed import server_document

from bokeh.server.server import BaseServer
from bokeh.server.tornado import BokehTornado
from bokeh.server.util import bind_sockets
from bokeh.themes import Theme

from trends import Trends


app = Flask(__name__)


def bkapp(doc):
    """Trend Application

    Arguments:
        doc {Bokeh Document} -- DOM document
    """
    trend = Trends()
    doc.add_root(trend.layout())
    doc.theme = Theme(filename="theme.yaml")

# can't use shortcuts here, since we are passing to low level BokehTornado
bkapp = Application(FunctionHandler(bkapp))

# This is so that if this app is run using something like "gunicorn -w 4" then
# each process will listen on its own port
sockets, port = bind_sockets("localhost", 0)

@app.route('/', methods=['GET'])
def bkapp_page():
    script = server_document('http://localhost:%d/bkapp' % port)

    name = request.args.get("name")

    if name is None:
        name = 'Hector'

    return render_template("embed.html",
                           script=script,
                           template="Flask", name=name)

def bk_worker():
    asyncio.set_event_loop(asyncio.new_event_loop())

    bokeh_tornado = BokehTornado({'/bkapp': bkapp}, extra_websocket_origins=["localhost:8000"])
    bokeh_http = HTTPServer(bokeh_tornado)
    bokeh_http.add_sockets(sockets)

    server = BaseServer(IOLoop.current(), bokeh_tornado, bokeh_http)
    server.start()
    server.io_loop.start()

tread = Thread(target=bk_worker)
tread.daemon = True
tread.start()
