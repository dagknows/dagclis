import typer
from typing import List

app = typer.Typer()

@app.command()
def new(ctx: typer.Context,
        label: str = typer.Argument(..., help="Label of the new proxy to create")):
    sesscli = SessionClient(ctx.obj)
    resp = sesscli.add_proxy(label)
    if resp.get("responsecode", False) in (False, "false", "False"):
        print(resp["msg"])
    else:
        print("OK")

@app.command()
def get(ctx: typer.Context,
        label: str = typer.Argument(..., help="Label of the new proxy to create"),
        folder: str = typer.Option(None, help="Directory to install proxy files in.  Default to ./{label}"),
        host: str = typer.Option(None, help="Reqrouter Host to connect to.  Will default to --reqrouter_host value")):
    sesscli = SessionClient(ctx.obj)
    folder = os.path.abspath(os.path.expanduser(folder or label))
    proxy_bytes = sesscli.download_proxy(label)
    if not proxy_bytes:
        print(f"Proxy {label} not found.  You can create one with 'proxy new {label}'")
        return

    with tempfile.NamedTemporaryFile() as outfile:
        if not os.path.isdir(folder): os.makedirs(folder)
        outfile.write(proxy_bytes)
        import subprocess
        p = subprocess.run(["tar", "-zxvf", outfile.name, "--directory", folder])
        print(p.stderr)
        print(p.stdout)

@app.command()
def list(ctx: typer.Context):
    """ List proxies on this host. """
    sesscli = SessionClient(ctx.obj)
    resp = sesscli.list_proxies()
    for k in resp: print(k)

@app.command()
def delete(ctx: typer.Context, label: str = typer.Argument(..., help="Label of the proxy to delete")):
    sesscli = SessionClient(ctx.obj)
    resp = sesscli.delete_proxy(label)
    if resp.get("responsecode", False) in (False, "false", "False"):
        print(resp["msg"])
