import typer
import os
from typing import List
import requests

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
