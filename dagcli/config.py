
import typer, os
from dagcli.client import newapi
from dagcli.utils import present, copy_shellconfigs
from dagcli.transformers import *
from typing import List

app = typer.Typer()

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
        login = username or password
        if not login:
            login = Confirm.ask("Would you like to login to get your access token?", default=True)
        if login:
            org = Prompt.ask("Please enter your org: ", default="dagknows")
            if not username:
                username = Prompt.ask("Please enter your username: ")
            if not password:
                password = Prompt.ask("Please enter your password: ", password=True)
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
def profile(ctx: typer.Context, as_json: bool=typer.Option(False, help="Control whether print as json or yaml")):
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
