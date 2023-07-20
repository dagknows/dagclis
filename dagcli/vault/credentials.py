
import typer
import json
import os
from enum import Enum
from typing import List

app = typer.Typer()

class ConnType(str, Enum):
    SSH = "ssh"
    WINRM = "winrm"

class LoginType(str, Enum):
    SSH_KEY = "ssh_key_file"
    UNAME_PASSWORD = "password"

@app.command()
def add(ctx: typer.Context,
        credentials: typer.Argument(..., help="Name of the credentials to add"),
        role: str = typer.Option(..., help = "Role to add credential to"),
        username: ConnType = typer.Option(..., help = "Credential user name"),
        conn_type: ConnType = typer.Option(ConnType.SSH, help = "Type of connection this credential allows acccess to"),
        login_type: LoginType = typer.Option(LoginType.SSH_KEY, help = "Type of login this credential is used for")):
    pass

@app.command()
def delete(ctx: typer.Context,
           credentials: typer.Argument(..., help="Name of the new credentials to delete")):
    pass

@app.command()
def list(ctx: typer.Context):
    """ List all credentialss. """
    pass
