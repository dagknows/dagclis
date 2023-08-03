
import typer
from enum import Enum
from dagcli.client import newapi
from dagcli.utils import present
from dagcli.transformers import *
from typing import List

app = typer.Typer()

EXAMPLE_SYNC_URL= "https://staging.dagknows.com/api/tasks/X6vuDDycnXsn3ce2WOm7"

class OrderBy(str, Enum):
    RECENT = "recent"
    RECENTBUCKETS = "recentbuckets"
    MOSTVOTED = "mostvoted"
    MOSTLINKED = "mostlinked"

@app.command()
def list(ctx: typer.Context,
         query: str = typer.Argument("", help="Query to search for if any"),
         userid: str = typer.Option("", help = "User to get tasks for "),
         collaborator: str = typer.Option("", help = "Filter by collaborator id"),
         with_pending_perms: bool = typer.Option(False, help = "Whether to filter by tasks that have pending perms."),
         order_by: OrderBy = typer.Option(OrderBy.RECENT, help = "Order by criteria"),
         tags: str = typer.Option("", help="Comma separated list of tags to search by.  Only 1 supported now")):
    if with_pending_perms: userid = "me"
    ctx.obj.tree_transformer = lambda obj: task_list_transformer(obj["tasks"])
    present(ctx, newapi(ctx.obj, f"/tasks/?q={query}&userid={userid}&with_pending_perms={with_pending_perms}&tags={tags}&order_by={order_by}&collaborator={collaborator}", { }, "GET"))

@app.command()
def gen(ctx: typer.Context,
        query: str = typer.Argument(..., help = f"Query to create a task with GenAI")):
    """ Syncs a task from an external source. """
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj["descendants"])
    present(ctx, newapi(ctx.obj, f"/tasks/gen/?q={query}", { }, "GET"))

@app.command()
def get(ctx: typer.Context,
        task_id: str = typer.Argument(None, help = "IDs of the Tasks to be fetched"),
        recurse: bool = typer.Option(True, help="Whether to recursively get task and its children")):
    """ Gets one or more tasks given IDs.  If no IDs are specified then a list of all tasks is done.  Otherwise for each Task ID provided its info is fetched. """
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj["descendants"])
    present(ctx, newapi(ctx.obj, f"/tasks/{task_id}?recurse={recurse}", { }, "GET"))

@app.command()
def sync(ctx: typer.Context,
         full_source_url: str = typer.Argument(..., help = f"Source URL to sync from, eg {EXAMPLE_SYNC_URL}"),
         resync: bool = typer.Option(False, help="Whether to resync if already exists")):
    """ Syncs a task from an external source. """
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj["descendants"])
    parts = [p for p in full_source_url.split("/") if p]
    if len(parts) < 4 or parts[-2] != "tasks" or parts[-3] != "api"or parts[0].lower() not in ("http:", "https:"):
        ctx.fail(f"full_source_url needs to be of the form <scheme>://<domain>/api/tasks/<taskid>, eg: {EXAMPLE_SYNC_URL}")
    scheme = parts[0].lower()
    domain = parts[-4]
    source_url = f"{scheme}//{domain}/api/tasks"
    source_task_id = parts[-1]
    present(ctx, newapi(ctx.obj, "/tasks/sync/", {
        "source_info": {
            "source_url": source_url,
            "source_id": source_task_id,
        },
        "resync": resync,
    }, "POST"))

@app.command()
def clone(ctx: typer.Context,
         taskid: str = typer.Argument(..., help = "ID of the task to clone"),
          shallow: bool = typer.Option(False, help = "Whether to do a shallow or a deep copy")):
    """ Clones a task as a new task. """
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj["descendants"])
    result = newapi(ctx.obj, f"/tasks/{taskid}/copy/", {}, "POST")["task"]
    newtaskid = result["id"]
    present(ctx, newapi(ctx.obj, f"/tasks/{newtaskid}?recurse=true", { }, "GET"))

@app.command()
def join(ctx: typer.Context,
         taskid: str = typer.Argument(..., help = "ID of the task to clone"),
         roles: List[str] = typer.Argument(None, help = "List of more roles to request")):
    """ Clones a task as a new task. """
    all_roles = roles
    newapi(ctx.obj, f"/tasks/{taskid}/users/join/", {"roles": all_roles}, "POST")

    # Now get it again
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj["descendants"])
    present(ctx, newapi(ctx.obj, f"/tasks/{taskid}?recurse=true", { }, "GET"))


@app.command()
def run(ctx: typer.Context,
        taskid: str = typer.Argument(..., help = "ID of the task to clone"),
        proxy_alias: str= typer.Option("", help="Alias of the proxy to execute on", envvar="DagKnowsProxyAlias"),
        proxy_token: str= typer.Option("", help="Token of the proxy to execute on", envvar="DagKnowsProxyToken"),
        params: str = typer.Option(None, help = "Json dictionary of parameters"),
        file: typer.FileText = typer.Option(None, help = "File containing a json of the parametres")):
    job = {
        "proxy_alias": proxy_alias,
        "proxy_token": proxy_token,
    }
    job["param_values"] = {}
    if file: payload["param_values"].update(json.load(file))
    if params: job["param_values"].update(json.loads(params))
    present(ctx, newapi(ctx.obj, f"/tasks/{taskid}/execute", {"job": job}, "POST"))

@app.command()
def create(ctx: typer.Context,
           title: str = typer.Option(..., help = "Title of the new task"),
           description: str = typer.Option("", help = "Description string for the new task"),
           input_params: str = typer.Option("", help = """Input params and their default values in the form a=1,b="x",c=True,d,e=None""")
           ):
    """ Creates a new task with the given title and description. """
    ctx.obj.tree_transformer = lambda obj: task_info_with_exec(obj["task"])
    present(ctx, newapi(ctx.obj, "/tasks", {
        "title": title,
        "description": description,
    }, "POST"))

@app.command()
def delete(ctx: typer.Context,
           task_ids: List[str] = typer.Argument(..., help = "List of ID of the Tasks to be deleted"),
           recurse: bool = typer.Option(False, help="Whether to recursively delete task and its children")):
    """ Delete all tasks with the given IDs. """
    for taskid in task_ids:
        present(ctx, newapi(ctx.obj, f"/tasks/{taskid}?recurse={recurse}", None, "DELETE"))

@app.command()
def modify(ctx: typer.Context, task_id: str = typer.Argument(..., help = "ID of the task to be updated"),
           title: str = typer.Option(None, help="New title to be set for the Task"),
           description: str = typer.Option(None, help="New description to be set for the Task")):
    """ Modifies the title or description of a Task. """
    update_mask = []
    params = {}
    if title: 
        update_mask.append("title")
        params["title"] = title
    if description: 
        update_mask.append("description")
        params["description"] = description
    present(ctx, newapi(ctx.obj, f"/v1/tasks/{task_id}", {
        "task": params,
        "update_mask": ",".join(update_mask),
    }, "PATCH"))

@app.command()
def add_nodes(ctx: typer.Context, 
              task_id: str = typer.Option(..., help = "Task ID to remove nodes from"),
              node_ids: List[str] = typer.Option(..., help = "First NodeID to add to the Task"),
              nodeids: List[str] = typer.Argument(None, help = "List of more Node IDs to add to the Task")):
    """ Adds nodes (by node IDs) to a Task.  If a node already exists it is ignored. """
    all_node_ids = node_ids + nodeids
    if all_node_ids:
        result = newapi(ctx.obj, f"/v1/tasks/{task_id}", {
            "add_nodes": all_node_ids,
        }, "PATCH")
        task = newapi(ctx.obj, f"/v1/tasks/{task_id}")
        ctx.obj.tree_transformer = lambda obj: task_info_with_exec(obj["task"])
        present(ctx, task)

@app.command()
def remove_nodes(ctx: typer.Context, 
                 task_id: str = typer.Option(..., help = "Task ID to remove nodes from"),
                 node_ids: List[str] = typer.Option(..., help = "First NodeID to remove from the Task"),
                 nodeids: List[str] = typer.Argument(..., help = "List of more Node IDs to remove from the Task")):
    """ Removes nodes from a Task.  When a node is removed, its child nodes are also removed. """
    nodeids = [n for n in nodeids if n.strip()]
    all_node_ids = node_ids + nodeids
    if all_node_ids:
        newapi(ctx.obj, f"/v1/tasks/{task_id}", {
            "remove_nodes": all_node_ids,
        }, "PATCH")
        task = newapi(ctx.obj, f"/v1/tasks/{task_id}")
        ctx.obj.tree_transformer = lambda obj: task_info_with_exec(obj["task"])
        present(ctx, task)

@app.command()
def connect(ctx: typer.Context,
            task_id: str = typer.Option(..., help = "Task ID to add a new edge in"),
            src_node_id: str = typer.Option(..., help = "Source node ID to start connection from"),
            dest_node_id: str = typer.Option(..., help = "Destination node ID to add connection to")):
    """ Connect src_node_id to dest_node_id creating an edge between them in the given Task.  If adding an edge results in cycles, the request will fail. """
    result = newapi(ctx.obj, f"/v1/nodes/{src_node_id}", {
        "node": {
            "task_id": task_id,
        },
        "add_nodes": [ dest_node_id ]
    }, "PATCH")
    task = newapi(ctx.obj, f"/v1/tasks/{task_id}")
    ctx.obj.tree_transformer = lambda obj: task_info_with_exec(obj["task"])
    present(ctx, task)

@app.command()
def disconnect(ctx: typer.Context,
            task_id: str = typer.Option(..., help = "Task ID to remove an new edge from"),
            src_node_id: str = typer.Option(..., help = "Source node ID to remove connection from"),
            dest_node_id: str = typer.Option(..., help = "Destination node ID to remove connection in")):
    """ Removes the edge between src_node_id and dest_node_id in the given Task """
    newapi(ctx.obj, f"/v1/nodes/{src_node_id}", {
        "node": {
            "task_id": task_id,
        },
        "remove_nodes": [ dest_node_id ]
    }, "PATCH")
    task = newapi(ctx.obj, f"/v1/tasks/{task_id}")
    ctx.obj.tree_transformer = lambda obj: task_info_with_exec(obj["task"])
    present(ctx, task)
