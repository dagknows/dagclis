
from requests.exceptions import ConnectionError
from http.server import BaseHTTPRequestHandler, HTTPServer
import time, logging
import threading
import requests

import typer, os
from dagcli.client import newapi
from dagcli.utils import present, ensure_shellconfigs
from dagcli.transformers import *
from typing import List

from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
disable_warnings(InsecureRequestWarning)

app = typer.Typer()

logger = logging.getLogger('forwarder_logger')
logger.setLevel(logging.DEBUG)
# log to file
ch = logging.FileHandler("/tmp/forwarder.log")
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

@app.command()
def stop(ctx: typer.Context):
    """ Stops all cli blob forwarder processes. """
    pass

@app.command()
def ensure(ctx: typer.Context,
           port: int = typer.Option(0, help = "Ensure that the forwarder is running on the given port.  If 0 or port is busy with another process then a random port is picked")):
    """ Start the cli blob forwarder process. """
    dkconfig = ctx.obj

    port, running = ensure_or_find_port(dkconfig, port)
    if port > 0 and not running:
        # we are good start the server on this port
        logger.debug(f"Starting on port {port}")
        start_forwarder(port)

FWD_PORT_FILE = "current_fwdport"
def get_active_forwarder_port(ctx):
    fwdport_file = ctx.obj.getpath(FWD_PORT_FILE, profile_relative=False, is_dir=False)
    fwdport = 0
    if os.path.isfile(fwdport_file):
        fwdport = int(open(fwdport_file).read().strip() or "0")
    return fwdport

def ensure_or_find_port(dkconfig, port):
    fwdport_file = dkconfig.getpath(FWD_PORT_FILE, profile_relative=False, is_dir=False)
    if port <= 0:
        # Then see if port exists in the forwarder file
        if os.path.isfile(fwdport_file):
            port = int(open(fwdport_file).read().strip() or "12000")
    if port <= 0: port = 12000

    for p in range(port, 65000):
        # Try to start on this port - but see if it is reachable
        with open(fwdport_file, "w") as fp: fp.write(f"{p}")
        try:
            resp = requests.get(f"http://localhost:{p}/status")
            if resp.status_code == 200 and resp.content == b"DagKnowsBlobForwarder":
                # there is already a perfectly working forwarder on this port
                # so just quit
                logger.debug(f"Forwarder already running on port {p}.  Exiting")
                return p, True
        except ConnectionError as exc:
            # Bingo - we found it
            return p, False
    if os.path.isfile(fwdport_file):
        os.remove(fwdport_file)
    raise Exception("Unable to find a free port for the forwarder")
    return -1, False

def start_forwarder(serverPort, hostName="localhost"):
    # Python 3 server example
    # We write this to this!
    # from gevent.queue import Queue
    import queue
    q = queue.Queue(maxsize=0)

    def forward_requests(q):
        while True:
            next = q.get()
            if next:
                logger.debug("Got next to send: ", next)
                rrhost, reqObj, headers = next
                respObj = requests.post(f"{rrhost}/processCliBlob", json=reqObj, headers=headers, verify=False)
                logger.debug(f"Forward to processCliBlob, stauts: {respObj.status_code}")

    class Forwarder(BaseHTTPRequestHandler):
        def do_GET(self):
            logger.debug("Getting status.....")
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(bytes("DagKnowsBlobForwarder", "utf-8"))

        def do_POST(self):
            import cgi
            ctype, pdict = cgi.parse_header(self.headers.get('content-type'))

            # refuse to receive non-json content
            if ctype != 'application/json':
                logger.debug(f"Received Request: {ctype}")
                self.send_response(400)
                self.end_headers()
                return


            # read the message and convert it into a python dictionary
            length = int(self.headers.get('content-length'))
            message = json.loads(self.rfile.read(length))
            rrhost = message["rrhost"]
            reqObj = message["reqObj"]
            headers = message["headers"]

            logger.debug(f"Received Request, Lenght: {length}, Host: {rrhost}, Headers: {headers}")
            q.put((rrhost, reqObj, headers))
            logger.debug("Queing cli blob complete.")

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(bytes("OK", "utf-8"))

    threading.Thread(target=forward_requests, args=(q,)).start()
    webServer = HTTPServer((hostName, serverPort), Forwarder)
    logger.debug("Forwarder started http://%s:%s" % (hostName, serverPort))
    webServer.serve_forever()
    # try: webServer.serve_forever()
    # except KeyboardInterrupt: pass

    webServer.server_close()
    logger.debug("Server stopped.")
