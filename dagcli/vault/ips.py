
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
        cred_label: str = typer.Option(None, help = "Credential label to add the IP addresses to.  Will be prompted if not provided"),
        addrs: List[str] = typer.Argument(..., help="List of Machine IP Addresss to add, eg 203.10.12.44")):
    vapi = ctx.obj.vault_api
    cred_label = select_credlabel(ctx, cred_label, ensure=True)
    vapi.add_ip_addr(addrs, cred_label)

@app.command()
def delete(ctx: typer.Context,
           addrs: List[str] = typer.Argument(..., help="List of Machine IP Addresss to delete, eg 203.10.12.44")):
    vapi = ctx.obj.vault_api
    vapi.delete_ip_addr(addrs)
    print("Deleted IP addresses: ", addrs)

@app.command()
def list(ctx: typer.Context):
    """ List all credentials in a role """
    vapi = ctx.obj.vault_api
    addrs = vapi.list_ip_addrs()
    pprint({addr: vapi.get_ip_addr(addr) for addr in addrs})

@app.command()
def get(ctx: typer.Context,
        addrs: List[str] = typer.Argument(..., help="List of Machine IP Addresss to get details for, eg 203.10.12.44")):
    vapi = ctx.obj.vault_api
    pprint({addr: vapi.get_ip_addr(addr) for addr in addrs})
