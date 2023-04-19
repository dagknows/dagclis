import typer
from dagcli.configs import DagKnowsConfig
import os, sys

app = typer.Typer(pretty_exceptions_show_locals=False)

# This callback applies to *all* commands
@app.callback()
def common_params(ctx: typer.Context,
                  profile: str = typer.Option("default", envvar="DagKnowsProfile", help="DagKnows profile to use"),
                  access_token: str = typer.Option(None, envvar='DagKnowsAccessToken', help='Access token for accessing DagKnows APIs'),
                  dagknows_home: str = typer.Option("~/.dagknows", envvar="DagKnowsHomeDir", help="Dir for DagKnows configs"),
                  log_request: bool = typer.Option(False, help='Enables logging of requests'),
                  log_response: bool = typer.Option(False, help='Enables logging of responses'),
                  format: str = typer.Option("tree", help='Output format to print as - json, yaml, tree')):
    assert ctx.obj is None

    api_host = os.environ.get('DagKnowsApiGatewayHost', "http://localhost:8080/api")
    # reqrouter_host = os.environ.get('DagKnowsReqRouterHost', "https://demo.dagknows.com:8443")
    reqrouter_host = os.environ.get('DagKnowsReqRouterHost', "https://localhost:443")
    dkconfig = DagKnowsConfig(os.path.expanduser(dagknows_home),
                             api_host = api_host,
                             reqrouter_host=reqrouter_host,
                             access_token=access_token,
                             output_format=format,
                             log_request=log_request,
                             log_response=log_response,
                             dagknows_home=os.path.expanduser(dagknows_home),
                             profile=profile,
                             headers={
                                "Authorization": f"Bearer {access_token}",
                                "DagKnowsReqRouterHost": reqrouter_host,
                             })
    ctx.obj = dkconfig

def ensure_access_token(ctx: typer.Context):
    if not ctx.obj.access_token:
        print("Access token needed.  Either login to install one or pass one via --access-token or set the DagKnowsAccessToken environment variable to it.")
        sys.exit(1)

@app.command()
def config(ctx: typer.Context, as_json: bool=typer.Option(False, help="Control whether print as json or yaml")):
    """ Show all defaults and environments. """
    if as_json:
        from pprint import pprint
        pprint(ctx.obj.data)
    else:
        import yaml
        print(yaml.dump(ctx.obj.data))

@app.command()
def init(ctx: typer.Context):
    """ Initializes DagKnows config and state folders. """
    # Initialize the home directory
    homedir = ctx.obj.data["dagknows_home"]

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
