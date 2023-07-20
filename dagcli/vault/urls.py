

from pprint import pprint
import typer
import json
import os
from enum import Enum
from typing import List
from rich.prompt import Prompt, Confirm
from dagcli.vault.utils import select_role, select_credlabel, select_url_label

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

@app.command()
def addlabel(ctx: typer.Context,
             url: str = typer.Argument(..., help="URL to assign label to"),
             label: str = typer.Argument(..., help="Label to assign to url")):
    assert url.startswith("http://") or url.startswith("https://"), "URL MUST start with http:// or https://"
    vapi = ctx.obj.vault_api
    vapi.add_url_label(url, label)
    print("Created label: ", label, " for URL: ", url)

@app.command()
def getlabel(ctx: typer.Context,
             label: str = typer.Argument(..., help="Label to describe")):
    """ Get infomation about a label. """
    vapi = ctx.obj.vault_api
    label = select_url_label(ctx, label, ensure=True)
    ip_addr = vapi.get_ip_label(label)
    print("The label: ", label, " is pointing to: ", ip_addr)

@app.command()
def labels(ctx: typer.Context,
           url_labels: List[str] = typer.Argument(None, help="List of url labels to to get info about")):
    """ List all url labels in the vault. """
    vapi = ctx.obj.vault_api
    if not url_labels:
        url_labels = vapi.list_url_labels()
    return {label: vapi.get_url_label(label) for label in url_labels}

@app.command()
def deletelabel(ctx: typer.Context,
                 url_label: str = typer.Argument(..., help="URL Label to remove")):
    vapi = ctx.obj.vault_api
    vapi.delete_url_label(url_label)
    print("Deleted the label: " + url_label)
