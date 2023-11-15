import typer
from typing import List
app = typer.Typer()

@app.command()
def new(ctx: typer.Context, label: str = typer.Argument(..., help="Label of the new token to generate"),
        expires_in: int = typer.Option(30*86400, help="Expiration in seconds")):
    sesscli = SessionClient(ctx.obj)
    resp = sesscli.generate_access_token(label, expires_in)
    if "access_tokens" not in resp:
        return "Access token not created"
    ctx.obj.access_tokens = resp["access_tokens"]
    return resp["access_tokens"]

@app.command()
def list(ctx: typer.Context, 
         refresh: bool = typer.Option(False, help="Whether to refresh token list from the server")):
    """ List all tokens under the current profile. """
    sesscli = SessionClient(ctx.obj)
    resp = sesscli.list_tokens()
    for token, data in ctx.obj.access_tokens.items():
        print(f'{data["label"]} - {data["expiry"]} - {token}')

@app.command()
def revoke(ctx: typer.Context, label: str = typer.Argument(..., help="Label of the token to revoke")):
    sesscli = SessionClient(ctx.obj)
    token = label # get_token_for_label(label)
    resp = sesscli.revoke_access_token(token)
