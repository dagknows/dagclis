import typer
from dagcli.configs import DagKnowsConfig
from dagcli.client import newapi
import json, os, sys

app = typer.Typer(pretty_exceptions_show_locals=False)

DISABLE_LOGIN = False

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
        ctx.fail(f"Access token missing in current config ({ctx.obj.curr_profile}).  You can manually pass an --access-token option, or set the DagKnowsAccessToken or initialize your profile with 'dk config init --profile {ctx.obj.curr_profile}'")


def get_token_for_label(homedir: str, label: str) -> str:
    pass

@app.command()
def logout(ctx: typer.Context):
    """ Logs out DagKnows and clears all sessions. """
    # TODO
    pass
