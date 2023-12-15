import subprocess
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
    print("Proxy created successfully: ", label)
    print("Next steps:")
    print(f"1. dk proxy get {label}")
    print(f"2. cd {label}")
    print(f"3. dk proxy getenv {label}")
    print(f"4. dk proxy update")

@app.command()
def update(ctx: typer.Context,
           folder: str = typer.Option("./", help="Directory to check for a proxy in.  Current folder if not provided.")):
    """ Update the proxy in the current folder if any. """
    resp = requests.get("https://raw.githubusercontent.com/dagknows/dkproxy/main/Makefile", verify=False)
    if resp.status_code != 200:
        print("Resp: ", resp.content)
        assert False

    resdata = resp.content.decode("utf-8")
    folder = os.path.abspath(os.path.expanduser(folder))
    respath = os.path.join(folder, "Makefile")
    with open(respath, "w") as resfile:
        resfile.write(resdata)

    subprocess.run(f"cd {folder} && make update", shell=True)

@app.command()
def getenv(ctx: typer.Context,
           label: str = typer.Argument(..., help="Label of the new proxy for which to get the environment variable"),
           envfile: str= typer.Option("./.env", help="Envfile to update.")):
    sesscli = ctx.obj.client
    from dagcli.client import make_url
    dagknows_url = sesscli.host
    url = make_url(sesscli.host, "/getProxyEnv")
    payload = { "alias": label }
    resp = requests.post(url, json=payload, headers=ctx.obj.headers, verify=False)
    if resp.status_code == 200:
        resp = resp.json()
        # print("Resp: ", resp)
        # print("=" * 80)

        newenv = []
        newenvfile = resp.get("envfile", {})
        newenvcopy = newenvfile.copy()
        envfile = os.path.abspath(os.path.expanduser(envfile))
        # print("Checking envfile: ", envfile, os.path.isfile(envfile))
        if os.path.isfile(envfile):
            lines = [l.strip() for l in open(envfile).read().split("\n") if l.strip()]
            for l in lines:
                if "=" not in l:
                    newenv.append(l)
                else:
                    pos = l.find("=")
                    k,v = l[:pos], l[pos+1:]
                    if k in newenvfile:
                        print(f"Key ({k}) Updated: [{v}] =====> [{newenvfile[k]}]")
                        newenv.append(f"{k}={newenvfile[k]}")
                        del newenvfile[k]
                    else:
                        newenv.append(f"{k}={v}")
            for k,v in newenvfile.items():
                # These were never found so add them
                newenv.append(f"{k}={v}")
        else:
            newenv = [f"{k}={v}" for k,v in newenvfile.items()]

        print("New Updated Env: ")
        print("\n".join(newenv))

        with open(envfile, "w") as ef:
            ef.write("\n".join(newenv))
    else:
        print("Failed: ", resp.content)

@app.command()
def get(ctx: typer.Context,
        label: str = typer.Argument(..., help="Label of the new proxy to create"),
        folder: str = typer.Option(None, help="Directory to install proxy files in.  Default to ./{label}")):
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
    for alias, info in resp.items():
        print("=" * 80)
        print("Name: ", alias)
        print("Token: ", info["token"])
        print("Last Updated At: ", info.get("last_update", ""))

@app.command()
def delete(ctx: typer.Context, label: str = typer.Argument(..., help="Label of the proxy to delete")):
    sesscli = ctx.obj.client
    resp = sesscli.delete_proxy(label, ctx.obj.access_token)
    if resp.get("responsecode", False) in (False, "false", "False"):
        print(resp["msg"])
