
import typer, os
from dagcli.client import newapi
from dagcli.utils import present
from dagcli.transformers import *
from typing import List

app = typer.Typer()

def copy_shellconfigs(ctx: typer.Context):
    dkzshrc = ctx.obj.getpath("zshrc", profile_relative=False)
    with open(dkzshrc, "w") as zshrc:
        from pkg_resources import resource_string
        zshrcdata = resource_string("dagcli", "scripts/zshrc")
        zshrc.write(zshrcdata.decode())
    from rich.prompt import Prompt, Confirm
    if Confirm.ask("Would you like to source dagknows shell confings in your .zshrc?", default=True):
        usrzshrc = os.path.expanduser("~/.zshrc")
        added_line = f"source {dkzshrc}"
        if added_line not in open(usrzshrc).read().split("\n"):
            with open(usrzshrc, "a") as zshrc:
                zshrc.write(f"\n{added_line}")

@app.command()
def init(ctx: typer.Context,
         profile: str = typer.Option("default", help = "Name of the profie to initialize"),
         api_host: str = typer.Option(None, help='API Host to use for this profile'),
         username: str = typer.Option(None, help="Username/Email to login with if access_token not to be entered manually"),
         password: str = typer.Option(None, help="Password to login with if access_token not to be entered manually"),
         access_token: str = typer.Option(None, help='Access token to initialize CLI with for this profile')):
    """ Initializes DagKnows config and state folders. """
    # Initialize the home directory
    dkconfig = ctx.obj

    # copy shell configs first
    copy_shellconfigs(ctx)

    # Enter the name of a default profile
    dkconfig.curr_profile = profile
    profile_data = dkconfig.profile_data

    if not api_host:
        api_host = typer.prompt("Enter the api host to make api calls to: ", default="http://localhost:9080/api")
        profile_data["api_host"] = api_host

    if not access_token:
        from rich.prompt import Prompt, Confirm
        login = False
        if not DISABLE_LOGIN:
            login = username or password
            if not login:
                login = Confirm.ask("Would you like to login to get your access token?", default=True)
        if login:
            org = Prompt.ask("Please enter your org: ", default="dagknows")
            if not username:
                username = Prompt.ask("Please enter your username: ")
            if not password:
                password = Prompt.ask("Please enter your password: ")
            # make call and get access_token
            payload = {"org": org,
                       "username": username,
                       "credentials": { "password": password }
                       }
            resp = newapi(ctx.obj, "/v1/users/login", payload, "POST")
            all_tokens = sorted([(v["expiry"], v,k) for k,v in resp["data"].items() if not v.get("revoked", False)])
            access_token = all_tokens[-1][2]
        else:
            access_token = typer.prompt("Enter an access token: ")

    profile_data["access_tokens"] = [
        {"value": access_token}
    ]
    dkconfig.save()

@app.command()
def show(ctx: typer.Context, as_json: bool=typer.Option(False, help="Control whether print as json or yaml")):
    """ Show all defaults and environments. """
    out = {
        "curr_profile": ctx.obj.curr_profile,
        "profile_data": ctx.obj.profile_data,
        "overrides": ctx.obj.data,
    }
    if as_json:
        from pprint import pprint
        pprint(out)
    else:
        import yaml
        print(yaml.dump(out, sort_keys=False))

@app.command()
def autoexport(ctx: typer.Context, as_json: bool=typer.Option(False, help="Control whether print as json or yaml")):
    """ Show all defaults and environments. """
    out = {
        "curr_profile": ctx.obj.curr_profile,
        "profile_data": ctx.obj.profile_data,
        "overrides": ctx.obj.data,
    }
    if as_json:
        from pprint import pprint
        pprint(out)
    else:
        import yaml
        print(yaml.dump(out, sort_keys=False))