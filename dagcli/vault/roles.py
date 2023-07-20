
import typer
import json
import os

app = typer.Typer()

@app.command()
def add(ctx: typer.Context,
        role: typer.Argument(..., help="Name of the new role to create")):
    pass

@app.command()
def delete(ctx: typer.Context,
           role: typer.Argument(..., help="Name of the new role to delete")):
    pass

@app.command()
def list(ctx: typer.Context):
    """ List all roles. """
    pass


