import subprocess
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

        # See if k8s config exists
        k8s_proxy_configs = resp.get("k8s_proxy_configs", None)
        if k8s_proxy_configs:
            os.makedirs(f"./k8s/proxies", exist_ok=True)
            with open(f"./k8s/proxies/{label}.tar.gz", 'wb') as tarball:
                tarball.write(b64decode(k8s_proxy_configs))
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

def parse_envfile(envfiledata):
    envvars = {}
    for l in [l.strip() for l in envfiledata.split("\n") if l.strip()]:
        if l.startswith("#"): continue
        eqpos = l.find("=")
        if eqpos < 0: continue
        key, value = l[:eqpos].strip(), l[eqpos + 1:].strip()
        envvars[key] = value
    return envvars

@app.command()
def initk8s(ctx: typer.Context,
            env_file: typer.FileText = typer.Argument("./.env", help = "Env file for your proxy.  If you do not have one then run the `dk getenv` command"),
            params_file: typer.FileText = typer.Argument("./params", help = "Parameters file contain all the params for generated files"),
            dest_dir: str = typer.Argument(None, help = "Destination folder where k8s files will be generated for your proxy.  If not provided `./proxies/<PROXY_ALIAS>` will be used"),
            storage_type: str = typer.Option("local", help = "Storage type - options: 'local', 'efs', 'multiefs'"),
            k8sbuild_root: str = typer.Option(".", help = "Path to dkproxy/k8s_build folder which must contain a templates folder")):
    k8sbuild_root = os.path.abspath(os.path.expanduser(k8sbuild_root))
    if not os.path.isdir(k8sbuild_root):
        raise Exception(f"k8sbuild_root ({k8sbuild_root}) must point to dkproxy/k8s_build folder which must contain a templates folder")

    templates_path = os.path.join(k8sbuild_root, "templates")
    if not os.path.isdir(templates_path):
        raise Exception("Please run this command from your dkproxy/k8s_build folder or specify a valid k8sbuild_root option")
    paramvars = parse_envfile(params_file.read())
    envvars = parse_envfile(env_file.read())

    allparams = envvars.copy()
    allparams.update(paramvars)

    if not dest_dir:
        dest_dir = f"./proxies/{allparams['PROXY_ALIAS']}"

    if not allparams.get("PROXY_NAMESPACE", ""):
        allparams["PROXY_NAMESPACE"] = f"proxy-{allparams['PROXY_ALIAS']}"

    # Create basic dirs and copy files
    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(os.path.join(dest_dir, "vault", "config", "ssl"), exist_ok=True)
    with open(os.path.join(dest_dir, "vault", "config", "local.json"), "w") as f:
        f.write(open("./vault/config/local.json").read())
    with open(os.path.join(dest_dir, "vault", "config", "ssl", "vault.crt"), "w") as f:
        f.write(open("../vault/config/ssl/vault.crt").read())
    with open(os.path.join(dest_dir, "vault", "config", "ssl", "vault.key"), "w") as f:
        f.write(open("../vault/config/ssl/vault.key").read())

    if storage_type == "local":
        if not allparams.get("LOCAL_PV_ROOT", ""):
            allparams["LOCAL_PV_ROOT"] = os.path.join(os.path.abspath(dest_dir), "localpv")
        os.makedirs(allparams["LOCAL_PV_ROOT"], exist_ok=True)

    for tmplfile in os.listdir(templates_path):
        if tmplfile in ("storage",): continue
        print("Processing: ", tmplfile)
        tf = open(os.path.join(templates_path, tmplfile)).read()
        ofpath = os.path.join(dest_dir, tmplfile)
        with open(ofpath, "w") as outfile:
            for k,v in allparams.items():
                tf = tf.replace("{{" + k + "}}", v)
            outfile.write(tf)

    # Storage specific things
    for tmplfile in os.listdir(f"{templates_path}/storage/{storage_type}"):
        print("Processing: ", tmplfile)
        tf = open(os.path.join(f"{templates_path}/storage", storage_type, tmplfile)).read()
        ofpath = os.path.join(dest_dir, tmplfile)
        with open(ofpath, "w") as outfile:
            for k,v in allparams.items():
                tf = tf.replace("{{" + k + "}}", v)
            outfile.write(tf)

    # Save the updated env file too
    with open(os.path.join(dest_dir, ".env"), "w") as outenvfile:
        outenvfile.write("\n".join([f"{k}={v}" for k,v in allparams.items()]))
