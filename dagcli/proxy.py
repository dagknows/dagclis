import typer
import os
from typing import List
import requests

from pkg_resources import resource_string
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
disable_warnings(InsecureRequestWarning)

app = typer.Typer()

@app.command()
def new(ctx: typer.Context,
        label: str = typer.Argument(..., help="Label of the new proxy to create"),
        dagknows_url: str = typer.Option("", help="Custom dagknows_url if not host")):
    sesscli = ctx.obj.client
    from dagcli.client import make_url
    dagknows_url = dagknows_url or sesscli.host
    url = make_url(sesscli.host, "/addAProxy")
    payload = { "alias": label, "dagknows_url": dagknows_url}
    resp = requests.post(url, json=payload, headers=ctx.obj.headers, verify=False)
    print(resp.json())

@app.command()
def update(ctx: typer.Context,
           folder: str = typer.Option("./", help="Directory to check for a proxy in.  Current folder if not provided.")):
    """ Update the proxy in the current folder if any. """
    resdata = resource_string("dagcli", f"scripts/Makefile.proxy")
    folder = os.path.abspath(os.path.expanduser(folder))
    respath = os.path.join(folder, "Makefile")
    with open(respath, "w") as resfile:
        resfile.write(resdata.decode())

@app.command()
def get(ctx: typer.Context,
        label: str = typer.Argument(..., help="Label of the new proxy to create"),
        folder: str = typer.Option(None, help="Directory to install proxy files in.  Default to ./{label}"),
        host: str = typer.Option(None, help="Reqrouter Host to connect to.  Will default to --reqrouter_host value")):
    sesscli = ctx.obj.client
    folder = os.path.abspath(os.path.expanduser(folder or label))
    proxy_bytes = sesscli.download_proxy(label, ctx.obj.access_token)
    if not proxy_bytes:
        print(f"Proxy {label} not found.  You can create one with 'proxy new {label}'")
        return

    import tempfile
    with tempfile.NamedTemporaryFile() as outfile:
        if not os.path.isdir(folder): os.makedirs(folder)
        outfile.write(proxy_bytes)
        import subprocess
        p = subprocess.run(["tar", "-zxvf", outfile.name])
        print(p.stderr)
        print(p.stdout)
        subprocess.run(["chmod", "a+rw", os.path.abspath(os.path.join(folder, "vault"))])

@app.command()
def list(ctx: typer.Context):
    """ List proxies on this host. """
    sesscli = ctx.obj.client
    resp = sesscli.list_proxies(ctx.obj.access_token)
    for k in resp: print(k)

@app.command()
def delete(ctx: typer.Context, label: str = typer.Argument(..., help="Label of the proxy to delete")):
    sesscli = ctx.obj.client
    resp = sesscli.delete_proxy(label, ctx.obj.access_token)
    if resp.get("responsecode", False) in (False, "false", "False"):
        print(resp["msg"])
