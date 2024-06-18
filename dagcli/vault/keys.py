
import typer
import json
import os
from enum import Enum
from typing import List
from rich.prompt import Prompt, Confirm
from dagcli.vault.utils import select_role, select_credlabel

app = typer.Typer()

@app.command()
def set(ctx: typer.Context,
        key: str = typer.Argument(..., help="Key whose value is to be set in the role"),
        role: str = typer.Option(..., help = "Role to add credential to"),
        value: str = typer.Option(None, help = "Value to set for this key")):
    vapi = ctx.obj.vault_api
    role = select_role(ctx, role, ensure=True)
    value = value or Prompt.ask(f"Enter value for key [{key}]: ", password=True)
    if not value:
        ctx.fail("Value must be provided")
    res = vapi.set_key(role=role, key=key, value=value)
    print(f"Set value for key ({key}) in role ({role})")

@app.command()
def list(ctx: typer.Context,
         role: str = typer.Option(None, help = "Role in which to list keys")):
    """ List all keys in a role """
    vapi = ctx.obj.vault_api
    role = select_role(ctx, role)
    if role:
        all_roles = [role]
    else:
        all_roles = vapi.list_roles()

    for role in all_roles:
        print(f"Keys in role {role}: ")
        print('\n'.join(vapi.list_keys(role)))

@app.command()
def get(ctx: typer.Context,
        key: str = typer.Argument(..., help = "Keys whose values are to be fetched."),
        role: str = typer.Option(None, help = "Role in which get details of the keys are to be fetched from.  If not specified returns details of key in all roles it exists in")):
    vapi = ctx.obj.vault_api
    if role:
        value = vapi.get_key(role, key)
        ## if "ssh_key" in creds: creds.pop("ssh_key")
        print(f"Key for {role}: ", value)
    else:
        all_roles = vapi.list_roles()
        for role in all_roles:
            keys = vapi.get_key(role, key)
            if keys:
                ## if "ssh_key" in creds: creds.pop("ssh_key")
                print(f"Keys for {role}: ", keys)
