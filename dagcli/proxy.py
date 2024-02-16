import subprocess
import typer
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
    print("Next steps:")
    print(f"1. If you have not already cloned the proxy repo: ")
    print(f"     git clone https://github.com/dagknows/dkproxy.git")
    print(f"2. cd dkproxy")
    print(f"3. dk proxy getenv {label}")
    print(f"4. make pull")
    print(f"5. make up logs")

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

@app.command()
def initk8s(ctx: typer.Context,
            env_file: typer.FileText = typer.Argument("./.env", help = "Env file for your proxy.  If you do not have one then run the `dk getenv` command"),
            dest_dir: str = typer.Argument(None, help = "Destination folder where k8s files will be generated for your proxy.  If not provided `./proxies/<PROXY_ALIAS>` will be used"),
            storage_type: str = typer.Option("local", help = "Storage type - options: 'local', 'efs'"),
            efs_fs_id: str = typer.Option("", help = "Filesystem ID of the EFS volume if using EFS for storage"),
            eks_cluster_name: str = typer.Option("", help = "Name of the EKS cluster to run against.  Will be needed if storage_type is efs"),
            aws_region: str = typer.Option("us-east-2", help = "Region to use if using AWS"),
            local_pv_root: str = typer.Option(None, help = "Root folder of the local PVs.  Will default to '<dest_dir>/localpv'"),
            minikube_mount_root: str = typer.Option("/minikubemount", help = "Folder on the Minikube VM where the storage will be mounted to local_pv_root on"),
            sidecar_root: str = typer.Option("/app/sidecar", help = "Root folder for our sidecar libs"),
            pyrunner_root: str = typer.Option(None, help = "Root folder for pyrunner related files.  Will default to <sidecar_root>/pyrunner"),
            pyenv_root: str = typer.Option(None, help = "Root folder for pyenv related files.  Will default to <pyrunner_root>/pyenv"),
            k8s_namespace: str = typer.Option(None, help = "Namespace for your proxy.  A proxy will be created within a particular namespace in the selected cluster.  If a namespace is not provided then `proxy-<PROXY_ALIAS>` will be used")):
    if not os.path.isdir("./templates"):
        raise Exception("Please run this command from your dkproxy/k8s_build folder")

    envvars = {}
    envfile = env_file.read()
    for l in [l.strip() for l in envfile.split("\n") if l.strip()]:
        eqpos = l.find("=")
        if eqpos < 0: continue
        key, value = l[:eqpos].strip(), l[eqpos + 1:].strip()
        envvars[key] = value

    if not dest_dir: dest_dir = f"./proxies/{envvars['PROXY_ALIAS']}"
    if not local_pv_root: local_pv_root = os.path.join(os.path.abspath(dest_dir), "localpv")
    if not k8s_namespace: k8s_namespace = f"proxy-{envvars['PROXY_ALIAS']}"

    pyrunner_root = pyrunner_root or f"{sidecar_root}/pyrunner"
    pyenv_root = pyenv_root or f"{pyrunner_root}/pyenv"

    # Create basic dirs and copy files
    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(local_pv_root, exist_ok=True)
    os.makedirs(os.path.join(dest_dir, "vault", "config", "ssl"), exist_ok=True)
    with open(os.path.join(dest_dir, "vault", "config", "local.json"), "w") as f: f.write(open("./vault/config/local.json").read())
    with open(os.path.join(dest_dir, "vault", "config", "ssl", "vault.crt"), "w") as f: f.write(open("../vault/config/ssl/vault.crt").read())
    with open(os.path.join(dest_dir, "vault", "config", "ssl", "vault.key"), "w") as f: f.write(open("../vault/config/ssl/vault.key").read())

    envvars["SIDECAR_ROOT"] = sidecar_root
    envvars["PYENV_ROOT"] = pyenv_root
    envvars["PYRUNNER_ROOT"] = pyrunner_root
    envvars["PROXY_NAMESPACE"] = k8s_namespace
    envvars["LOCAL_PV_ROOT"] = local_pv_root
    envvars["MINIKUBE_MOUNT_ROOT"] = minikube_mount_root
    envvars["EFS_FILESYSTEM_ID"] = efs_fs_id
    envvars["EKS_CLUSTER_NAME"] = eks_cluster_name
    envvars["AWS_REGION"] = aws_region

    if storage_type == "efs":
        assert efs_fs_id not in ("", None), "efs_fs_id param must be specified if storage type is efs"
        assert eks_cluster_name not in ("", None), "eks_cluster_name param must be specified if storage type is efs"
        assert aws_region not in ("", None), "aws_region param must be specified if storage type is efs"

    for tmplfile in os.listdir("./templates"):
        if tmplfile in ("storage",): continue
        tf = open(os.path.join("./templates", tmplfile)).read()
        ofpath = os.path.join(dest_dir, tmplfile)
        with open(ofpath, "w") as outfile:
            for k,v in envvars.items():
                tf = tf.replace("{{" + k + "}}", v)
            outfile.write(tf)

    # Storage specific things
    for tmplfile in os.listdir(f"./templates/storage/{storage_type}"):
        tf = open(os.path.join("./templates/storage", storage_type, tmplfile)).read()
        ofpath = os.path.join(dest_dir, tmplfile)
        with open(ofpath, "w") as outfile:
            for k,v in envvars.items():
                tf = tf.replace("{{" + k + "}}", v)
            outfile.write(tf)

    # Save the updated env file too
    with open(os.path.join(dest_dir, ".env"), "w") as outenvfile:
        outenvfile.write("\n".join([f"{k}={v}" for k,v in envvars.items()]))

    # Save daglib too
    # with open(os.path.join(dest_dir, "daglib.py"), "w") as daglibfile: daglibfile.write(open("../outpost/jobs/daglib.py").read())
