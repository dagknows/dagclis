
import typer, time
from enum import Enum
from dagcli.client import newapi
from dagcli.utils import present
from dagcli.transformers import *
from typing import List

app = typer.Typer()

@app.command()
def run(ctx: typer.Context,
        file = typer.Argument(..., help = "Python file to submit for running")):
    """ Run a raw python file on the proxy."""
    # ctx.obj.tree_transformer = lambda obj: rich_job_info(obj["job"])
    present(ctx, newapi(ctx.obj, f"/jobs/{job_id}", { }, "GET"))

