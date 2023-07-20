

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
    url = vapi.get_url_label(label)
    print("The label: ", label, " is pointing to: ", url)

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
