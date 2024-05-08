
import typer, time
from enum import Enum
from dagcli.client import newapi
from dagcli.utils import present
from dagcli.transformers import *
from typing import List

app = typer.Typer()

class OrderBy(str, Enum):
    RECENT = "recent"

@app.command()
def list(ctx: typer.Context,
         query: str = typer.Argument("", help="Query to search for if any"),
         userid: str = typer.Option("", help = "User to get workspaces for "),
         collaborator: str = typer.Option("", help = "Filter by collaborator id"),
         with_pending_perms: bool = typer.Option(False, help = "Whether to filter by workspaces that have pending perms."),
         order_by: OrderBy = typer.Option(OrderBy.RECENT, help = "Order by criteria"),
         tags: str = typer.Option("", help="Comma separated list of tags to search by.  Only 1 supported now")):
    """Search for workspaces."""
    if with_pending_perms: userid = "me"
    ctx.obj.tree_transformer = lambda obj: workspace_list_transformer(obj["workspaces"])
    present(ctx, newapi(ctx.obj, f"/workspaces/?q={query}&userid={userid}&tags={tags}&order_by={order_by}", { }, "GET"))

@app.command()
def get(ctx: typer.Context,
        workspace_id: str = typer.Argument(None, help = "IDs of the Workspaces to be fetched")):
    """ Gets one or more workspaces given IDs.  If no IDs are specified then a list of all workspaces are returned."""
    ctx.obj.tree_transformer = lambda obj: rich_workspace_info(obj["workspace"], obj["descendants"])
    present(ctx, newapi(ctx.obj, f"/workspaces/{workspace_id}", { }, "GET"))

@app.command()
def join(ctx: typer.Context,
         workspaceid: str = typer.Argument(..., help = "ID of the workspace to clone"),
         roles: List[str] = typer.Argument(None, help = "List of more roles to request")):
    """ Request to a join a workspace as a collaborator. """
    all_roles = roles
    newapi(ctx.obj, f"/workspaces/{workspaceid}/users/join/", {"roles": all_roles}, "POST")

    # Now get it again
    ctx.obj.tree_transformer = lambda obj: rich_workspace_info(obj["workspace"], obj["descendants"])
    present(ctx, newapi(ctx.obj, f"/workspaces/{workspaceid}", { }, "GET"))

@app.command()
def delete(ctx: typer.Context,
           workspace_ids: List[str] = typer.Argument(..., help = "List of ID of the Workspaces to be deleted"),
           recurse: bool = typer.Option(False, help="Whether to recursively delete workspace and its children")):
    """ Delete all workspaces with the given IDs. """
    for workspaceid in workspace_ids:
        present(ctx, newapi(ctx.obj, f"/workspaces/{workspaceid}?recurse={recurse}", None, "DELETE"))

@app.command()
def removeusers(ctx: typer.Context,
                workspace_id: str = typer.Argument(..., help = "Workspace ID where user permissions are to be added"),
                userids: List[str] = typer.Argument(..., help = "List of userids to remove from a workspace")):
    """ Remove users from being collaborators on a workspace.  All their pending and approved permissions are removed. """
    result = newapi(ctx.obj, f"/workspaces/{workspace_id}/users", { "removed_users": userids }, "PUT")
    workspace = newapi(ctx.obj, f"/workspaces/{workspace_id}")
    ctx.obj.tree_transformer = lambda obj: rich_workspace_info(obj["workspace"], obj.get("descendants", {}))
    present(ctx, workspace)

@app.command()
def create(ctx: typer.Context,
           title: str = typer.Option(..., help = "Title of the new workspace"),
           description: str = typer.Option("", help = "Description string for the new workspace"),
           customid: str = typer.Option("", help = "A custom ID to assign instead of a randomly generated one"),
           tags: str = typer.Option("", help = "Comma separated list of tags, eg 'java,frontend,kubernetes'"),
           file: typer.FileText = typer.Option(None, help = "File containing more workspace parameters")
       ):
    """ Creates a new workspace with the given title, description and other parameters from a file. """
    ctx.obj.tree_transformer = lambda obj: rich_workspace_info(obj["workspace"])
    workspace_params = {}
    if file: workspace_params.update(json.load(file))
    if title: workspace_params["title"] = title
    if description: workspace_params["description"] = description
    if tags: workspace_params["tags"] = tags.split(",")
    if customid.strip(): workspace_params["id"] = customid.strip()
    newworkspace = newapi(ctx.obj, "/workspaces/", {"workspace": workspace_params}, "POST")
    present(ctx, newworkspace)

@app.command()
def update(ctx: typer.Context, workspace_id: str = typer.Argument(..., help = "ID of the workspace to be updated"),
           title: str = typer.Option(None, help="New title to be set for the Workspace"),
           description: str = typer.Option(None, help="New description to be set for the Workspace"),
           file: typer.FileText = typer.Option(None, help = "File containing more workspace parameters update")
        ):
    """ Update a workspace. """
    ctx.obj.tree_transformer = lambda obj: rich_workspace_info(obj["workspace"])
    update_mask = []
    params = {}
    if file:
        contents = json.load(file)
        for k,v in contents.items():
            params[k] = v
            update_mask.append(k)
    if title: 
        update_mask.append("title")
        params["title"] = title
    if description: 
        update_mask.append("description")
        params["description"] = description
    payload = {
        "workspace": params,
        "update_mask": update_mask,
    }
    resp = newapi(ctx.obj, f"/workspaces/{workspace_id}", payload, "PATCH")
    present(ctx, resp)
