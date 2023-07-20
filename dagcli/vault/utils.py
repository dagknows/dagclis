
from pprint import pprint
import typer
import json
import os
from enum import Enum
from typing import List
from rich.prompt import Prompt, Confirm

def select_role(ctx, role=None, ensure=False):
    if not role:
        vapi = ctx.obj.vault_api
        all_roles = vapi.list_roles()
        if not all_roles:
            ctx.fail("Roles do not exist.  Add one")
        role = Prompt.ask("Select a role", choices=all_roles)
    if ensure and not role:
        ctx.fail("Role not provided.  Either pass it or select it")
    return role

def select_credlabel(ctx, cred_label=None, role=None, ensure=False):
    if not cred_label:
        vapi = ctx.obj.vault_api
        all_roles = vapi.list_roles()
        if role:
            all_cred_labels = set(vapi.list_credentials(role))
        else:
            all_cred_labels = set([vapi.list_credentials(role) for role in all_roles])
        cred_label = Prompt.ask("Select a cred label", choices=list(all_cred_labels))
    if ensure and not cred_label:
        ctx.fail("Cred label not provided.  Either pass it or select it")
    return cred_label
