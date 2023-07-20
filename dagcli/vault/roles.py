
from pprint import pprint
import typer
import json
import os
from dagcli.vault.utils import select_role, select_credlabel

app = typer.Typer()

@app.command()
def add(ctx: typer.Context,
        role: str = typer.Argument(..., help="Name of the new role to create")):
    vapi = ctx.obj.vault_api
    print("Added role: ", role, vapi.add_role(role))

@app.command()
def delete(ctx: typer.Context,
           role: str = typer.Argument(None, help="Name of the new role to delete")):
    role = select_role(ctx, role, ensure=True)
    print(f"Cannot remove role {role} yet")

@app.command()
def list(ctx: typer.Context):
    """ List all roles. """
    vapi = ctx.obj.vault_api
    pprint(vapi.list_roles())
