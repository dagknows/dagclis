import typer
import tempfile
import time
import pickle
import os
import re
from ipdb import set_trace
import json
import requests
from pprint import pprint
from typing import List

from dagcli.root import app, ensure_access_token
from dagcli import dags
from dagcli import nodes
from dagcli import execs
from dagcli import sessions
from dagcli import tokens
from dagcli import proxy

app.add_typer(dags.app, name="dags", callback=ensure_access_token)
app.add_typer(sessions.app, name="sessions", callback=ensure_access_token)
app.add_typer(nodes.app, name="nodes", callback=ensure_access_token)
app.add_typer(execs.app, name="execs", callback=ensure_access_token)
app.add_typer(tokens.app, name="tokens", callback=ensure_access_token)
app.add_typer(proxy.app, name="proxy", callback=ensure_access_token)

if __name__ == "__main__":
    app()
