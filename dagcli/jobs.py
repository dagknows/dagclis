
import typer, time
from enum import Enum
from dagcli.client import newapi
from dagcli.utils import present
from dagcli.transformers import *
from typing import List

app = typer.Typer()

@app.command()
def get(ctx: typer.Context,
        job_id: str = typer.Argument(None, help = "IDs of the Jobs to be fetched")):
    """ Gets one or more jobs given IDs.  If no IDs are specified then a list of all jobs are returned."""
    # ctx.obj.tree_transformer = lambda obj: rich_job_info(obj["job"])
    present(ctx, newapi(ctx.obj, f"/jobs/{job_id}", { }, "GET"))


@app.command()
def stop(ctx: typer.Context,
        job_id: str = typer.Argument(None, help = "IDs of the Jobs to be fetched")):
    """ Stops a jobs."""
    # ctx.obj.tree_transformer = lambda obj: rich_job_info(obj["job"])
    present(ctx, newapi(ctx.obj, f"/jobs/{job_id}/actions:stop", {}, "GET"))

