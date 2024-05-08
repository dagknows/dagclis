import subprocess
import json
from base64 import b64decode
import typer
from typing_extensions import Annotated
from typing import Optional
from pathlib import Path
import os, sys
from typing import List
import requests

from pkg_resources import resource_string
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
disable_warnings(InsecureRequestWarning)

app = typer.Typer()

@app.command()
def find(ctx: typer.Context):
    sesscli = ctx.obj.client
    from dagcli.client import make_url
    dagknows_url = sesscli.host
    url = make_url(sesscli.host, "/getUnusedOrgs")
    resp = requests.post(url, headers=ctx.obj.headers, verify=False)
    if resp.status_code == 200:
        print(json.dumps(resp.json(), indent=2))
    else:
        print("Failed: ", resp.content)

@app.command()
def delete(ctx: typer.Context,
           orgname: str = typer.Argument(..., help="Name of the org to delete")):
    sesscli = ctx.obj.client
    from dagcli.client import make_url
    dagknows_url = sesscli.host
    url = make_url(sesscli.host, "/deleteOrg")
    payload = { "orgname": orgname.strip() }
    resp = requests.post(url, json=payload, headers=ctx.obj.headers, verify=False)
    if resp.status_code == 200:
        for k,v in resp.json().get("_source", {}).get("proxy_table", {}).items():
            print(k, v)
            print("")
    else:
        print("Failed: ", resp.content)

@app.command()
def ensure(ctx: typer.Context,
           orgname: str = typer.Argument(..., help="Name of the org to ensure"),
           activities: str=typer.Argument("main,tasks", help="Which activities to run: 'main', 'tasks'")):
    sesscli = ctx.obj.client
    from dagcli.client import make_url
    dagknows_url = sesscli.host

    activities = [a.strip() for a in activities.lower().split(",") if a.strip()]
    for activity in activities:
        payload = { "orgname": orgname.strip().lower() }
        if activity == "main": 
            url = make_url(sesscli.host, "/ensureOrg")
        elif activity == "tasks":
            url = make_url(sesscli.host, "/ensureOrgTasks")
        else:
            raise Exception("Invalid activity: ", activities)
        resp = requests.post(url, json=payload, headers=ctx.obj.headers, verify=False)
        if resp.status_code == 200:
            print("Activity: ", activity, "Response: ", resp.json())
        else:
            print("Failed: ", resp.content)
