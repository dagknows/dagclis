

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
def create(ctx: typer.Context,
        group_label: str = typer.Argument(..., help = "Name of the host group to create"),
        hosts: List[str] = typer.Argument(None, help = "List of all hosts or IPs in the group")):
    vapi = ctx.obj.vault_api
    vapi.create_host_group(group_label, hosts)
    print(f"Created host group {group_label} with hosts: ", hosts or [])

@app.command()
def list(ctx: typer.Context):
    """ List all host groups """
    vapi = ctx.obj.vault_api
    pprint(vapi.list_host_groups())

@app.command()
def delete(ctx: typer.Context,
           group_label: str = typer.Argument(..., help="Label of the group to delete"),
           confirm: bool = typer.Option(True, help="Whether to prompt for confirmation or not")):
    vapi = ctx.obj.vault_api
    if confirm and not Confirm.ask(f"Are you sure you want to delete the group '{group_label}'"):
        ctx.fail("Confirmation failed")
    else:
        vapi.delete_host_group(group_label)
        print("Deleted the group: " + group_label)

@app.command()
def get(ctx: typer.Context,
        group_labels: List[str] = typer.Argument(..., help="Group label(s) to get")):
    vapi = ctx.obj.vault_api
    pprint({label: vapi.get_host_group(label) for label in group_labels})

@app.command()
def addhosts(ctx: typer.Context,
             group_label: str = typer.Argument(..., help = "Name of the host group to add hosts to"),
             hosts: List[str] = typer.Argument(None, help = "List of all hosts to add to the group")):
    vapi = ctx.obj.vault_api
    curr_groups = vapi.list_host_groups()
    if group_label not in curr_groups:
        ctx.fail(f"Group {group_label} does not exist.  Create it first")
    else:
        new_host_list = vapi.add_hosts_to_group(group_label, hosts or [])
        print("The group label: ", group_label, " has hosts: ", new_host_list)

@app.command()
def deletehosts(ctx: typer.Context,
                group_label: str = typer.Argument(..., help = "Name of the host group to remove hosts from"),
                hosts: List[str] = typer.Argument(None, help = "List of all hosts to remove from the group")):
    vapi = ctx.obj.vault_api
    vapi.delete_hosts_from_group(group_label, hosts or [])
    print("Deleted: ", hosts, " from group: " + group_label)
