import typer
from dagcli.configs import DagKnowsConfig
import json, os, sys

app = typer.Typer(pretty_exceptions_show_locals=False)

# This callback applies to *all* commands
@app.callback()
def common_params(ctx: typer.Context,
                  dagknows_home: str = typer.Option("~/.dagknows", envvar="DagKnowsHomeDir", help="Dir for DagKnows configs"),
                  profile: str = typer.Option(None, envvar="DagKnowsProfile", help="DagKnows profile to use.  To set a default run `dk profiles set-default`"),
                  access_token: str = typer.Option(None, envvar='DagKnowsAccessToken', help='Access token for accessing DagKnows APIs'),
                  log_request: bool = typer.Option(False, help='Enables logging of requests'),
                  log_response: bool = typer.Option(False, help='Enables logging of responses'),
                  format: str = typer.Option("tree", envvar='DagKnowsOutputFormat', help='Output format to print as - json, yaml, tree')):
    assert ctx.obj is None

    # See if there is a current file
    dagknows_home_dir = os.path.expanduser(dagknows_home)
    if not profile:
        curr_config_file = os.path.join(dagknows_home_dir, "current")
        if not os.path.isdir(dagknows_home_dir):
            os.makedirs(dagknows_home_dir)
        if not os.path.isfile(curr_config_file):
            with open(curr_config_file, "w") as configfile:
                curr_config = {
                    "profile": "default"
                }
                configfile.write(json.dumps(curr_config, indent=4))
        curr_config = json.loads(open(curr_config_file).read().strip() or "{}")
        profile = curr_config["profile"]

    # For now these are env vars and not params yet
    reqrouter_host = os.environ.get('DagKnowsReqRouterHost', "")
    api_host = os.environ.get('DagKnowsApiGatewayHost', "")
    ctx.obj  = DagKnowsConfig(dagknows_home_dir, profile or "default",
                              output_format=format,
                              reqrouter_host=reqrouter_host,
                              api_host=api_host,
                              access_token=access_token,
                              log_request=log_request,
                              log_response=log_response)

def ensure_access_token(ctx: typer.Context):
    if not ctx.obj.access_token:
        ctx.fail(f"Access token missing in current config ({ctx.obj.curr_profile}).  You can manually pass an --access-token option, or set the DagKnowsAccessToken or initialize your profile with 'dk init --profile {ctx.obj.curr_profile}'")

@app.command()
def init(ctx: typer.Context,
         profile: str = typer.Option("default", help = "Name of the profie to initialize"),
         api_host: str = typer.Option(None, help='API Host to use for this profile'),
         access_token: str = typer.Option(None, help='Access token to initialize CLI with for this profile')):
    """ Initializes DagKnows config and state folders. """
    # Initialize the home directory
    dkconfig = ctx.obj

    # Enter the name of a default profile
    dkconfig.curr_profile = profile
    profile_data = dkconfig.profile_data

    if not api_host:
        api_host = typer.prompt("Enter the api host to make api calls to: ", default="http://localhost:9080/api")
        profile_data["api_host"] = api_host

    if not access_token:
        access_token = typer.prompt("Enter an access token: ")

    profile_data["access_tokens"] = [
        {"value": access_token}
    ]
    dkconfig.save()

@app.command()
def configs(ctx: typer.Context, as_json: bool=typer.Option(False, help="Control whether print as json or yaml")):
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

def get_token_for_label(homedir: str, label: str) -> str:
    pass

@app.command()
def login(ctx: typer.Context, org: str = typer.Option("dagknows", help="Organization to login to"),
          install_token: bool = typer.Option(True, help="Automatically install an access token for use"),
          username: str = typer.Option(..., help="Username/Email to login with", prompt=True),
          password: str = typer.Option(..., help="Username/Email to login with", prompt=True, hide_input=True)):
    """ Logs into DagKnows and installs a new access token. """
    sesscli = ctx.obj.client
    sesscli.reset()
    sesscli.login_with_email(username, password, org)
    if install_token:
        # TODO
        pass
    typer.echo("Congratulations.  You can now create and revoke tokens")

@app.command()
def logout(ctx: typer.Context):
    """ Logs out DagKnows and clears all sessions. """
    # TODO
    pass
