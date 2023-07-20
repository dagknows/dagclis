
import typer
import json
import os
from enum import Enum
from typing import List
from rich.prompt import Prompt, Confirm
from dagcli.vault.utils import select_role, select_credlabel

app = typer.Typer()

class ConnType(str, Enum):
    SSH = "ssh"
    WINRM = "winrm"

class LoginType(str, Enum):
    SSH_KEY = "ssh_key_file"
    UNAME_PASSWORD = "password"

@app.command()
def add(ctx: typer.Context,
        label: str = typer.Argument(..., help="Label of the credentials to add"),
        role: str = typer.Option(..., help = "Role to add credential to"),
        conn_type: ConnType = typer.Option(ConnType.SSH, help = "Type of connection this credential allows acccess to"),
        ssh_key_file : typer.FileText= typer.Option(None, help='Key file name to use for ssh login associated with this credential'),
        password : str = typer.Option(None, help='Password to use for passowrd login login associated with this credential.  Will be prompted for if empty'),
        username: str = typer.Option(..., help = "Credential user name")):
    vapi = ctx.obj.vault_api
    ssh_key_file_name = None
    login_type = "password"
    if ssh_key_file:
        login_type = "ssh_key_file"
        ssh_key_file_name = ssh_key_file.name
    else:
        password = password or Prompt.ask("Please enter login password: ", password=True)
        if not password:
            ctx.fail("Either password is required or provide a ssh_key_file value")
    res = vapi.add_credentials(role=role, label=label,
                         username=username,
                         typ=login_type,
                         ssh_key_file_name=ssh_key_file_name,
                         password=password,
                         conn_type=conn_type)
    print("Added credentials: " + label + " for role: " + role)

@app.command()
def delete(ctx: typer.Context,
           label: str = typer.Argument(..., help="Name of the new credentials to delete"),
           role: str = typer.Option(..., help="Role from which to remove the credential")):
    vapi = ctx.obj.vault_api
    role = select_role(ctx, role, ensure=True)
    vapi.delete_credentials(role, label)
    print("Deleted latest version of credentials: ", role, label)

@app.command()
def list(ctx: typer.Context,
         role: str = typer.Option(None, help = "Role in which to list credentials")):
    """ List all credentials in a role """
    vapi = ctx.obj.vault_api
    role = select_role(ctx, role)
    if role:
        all_roles = [role]
    else:
        all_roles = vapi.list_roles()

    for role in all_roles:
        print(f"Credentials in role {role}: ")
        print('\n'.join(vapi.list_credentials(role)))

@app.command()
def get(ctx: typer.Context,
        cred_label: str = typer.Argument(..., help = "Label of specific credential go get details for."),
        role: str = typer.Option(None, help = "Role in which get details of a credential from.  If not specified returns details of label in all roles it exists in")):
    vapi = ctx.obj.vault_api
    if role:
        return vapi.get_credentials(role, cred_label)
    else:
        roles = vapi.list_roles()
        return [vapi.get_credentials(role, cred_label) for role in roles]
