
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

def select_ip_label(ctx, ip_label=None, ensure=False):
    if not ip_label:
        vapi = ctx.obj.vault_api
        all_ip_labels = vapi.list_ip_labels()
        if not all_ip_labels:
            ctx.fail("IP Labels do not exist.  Add one")
        ip_label = Prompt.ask("Select an ip label", choices=all_ip_labels)
    if ensure and not ip_label:
        ctx.fail("IP Label not provided.  Either pass it or select it")
    return ip_label

def select_url_label(ctx, url_label=None, ensure=False):
    if not url_label:
        vapi = ctx.obj.vault_api
        all_url_labels = vapi.list_url_labels()
        if not all_url_labels:
            ctx.fail("URL Labels do not exist.  Add one")
        url_label = Prompt.ask("Select an url label", choices=all_url_labels)
    if ensure and not url_label:
        ctx.fail("URL Label not provided.  Either pass it or select it")
    return url_label
