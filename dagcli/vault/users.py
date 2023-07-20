
from pprint import pprint
import typer
import json
import os
from enum import Enum
from typing import List
from rich.prompt import Prompt, Confirm
from dagcli.vault.utils import select_role, select_credlabel

app = typer.Typer()

@app.command()
def add(ctx: typer.Context,
        uname: str = typer.Argument(..., help = "username to add"),
        role: str = typer.Option(..., help = "Role to add user to")):
    vapi = ctx.obj.vault_api
    role = select_role(ctx, role, ensure=True)
    vapi.add_user(uname, role)
    print("Added user: " + uname + " to role: " + role)

@app.command()
def delete(ctx: typer.Context,
           uname: str = typer.Argument(..., help = "username to delete")):
    vapi = ctx.obj.vault_api
    vapi.delete_user(uname)
    print("Deleted user: " + uname)

@app.command()
def list(ctx: typer.Context):
    """ List all users"""
    vapi = ctx.obj.vault_api
    users = vapi.list_users()
    pprint(users)

@app.command()
def get(ctx: typer.Context,
        uname: str = typer.Argument(..., help = "username to fetch")):
    vapi = ctx.obj.vault_api
    resp = vapi.get_user(uname)
    print("User details: ", json.dumps(resp, indent=4))
