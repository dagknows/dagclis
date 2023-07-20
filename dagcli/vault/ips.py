
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

@app.command()
def add_label(ctx: typer.Context,
              ip_addr: str = typer.Argument(..., help="IP address to assign label to"),
              label: str = typer.Argument(..., help="Label to assign to ip address")):
    vapi = ctx.obj.vault_api
    vapi.add_ip_label(ip_addr, label)
    print("Created label: ", label, " for IP address: ", ip_addr)

@app.command()
def add_regex(ctx: typer.Context,
              ip_addr: str = typer.Argument(..., help="IP address to assign label to"),
              regex: str = typer.Argument(..., help="Label Regex to assign to ip address")):
    vapi = ctx.obj.vault_api
    vapi.add_ip_label_regex(ip_addr, regex)
    print("Created regex: ", regex, " for IP address: ", ip_addr)

@app.command()
def from_label(ctx: typer.Context,
               label: str = typer.Argument(..., help="Label to describe")):
    """ Get infomation about a label. """
    vapi = ctx.obj.vault_api
    label = select_ip_label(ctx, label, ensure=True)
    ip_addr = vapi.get_ip_label(label)
    print("The label: ", label, " is pointing to: ", ip_addr)

@app.command()
def labels(ctx: typer.Context):
    """ List all labels in the vault. """
    vapi = ctx.obj.vault_api
    print("Labels: ", vapi.list_ip_labels())

@app.command()
def regexes(ctx: typer.Context):
    """ List all label regexes in the vault. """
    vapi = ctx.obj.vault_api
    print("Label Regexes: ", vapi.list_ip_label_regex())

@app.command()
def delete_label(ctx: typer.Context,
                 label: str = typer.Argument(..., help="Label to remove")):
    vapi = ctx.obj.vault_api
    vapi.delete_ip_label(label)
    print("Deleted the label: " + label + '. The IP address is not deleted')

@app.command()
def delete_regex(ctx: typer.Context,
                 regex: str = typer.Argument(..., help="Regex to remove")):
    vapi = ctx.obj.vault_api
    vapi.delete_ip_label_regex(regex)
    print("Deleted the label regex: " + regex + '. The IP address is not deleted')
