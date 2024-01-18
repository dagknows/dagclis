
import typer, time
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
    """Search for tasks."""
    if with_pending_perms: userid = "me"
    ctx.obj.tree_transformer = lambda obj: task_list_transformer(obj["tasks"])
    present(ctx, newapi(ctx.obj, f"/tasks/?q={query}&userid={userid}&with_pending_perms={with_pending_perms}&tags={tags}&order_by={order_by}&collaborator={collaborator}", { }, "GET"))

@app.command()
def genai(ctx: typer.Context,
          query: str = typer.Argument(..., help = f"Query to create a task with GenAI")):
    """ Generate a Task with AI. """
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj["descendants"])
    present(ctx, newapi(ctx.obj, f"/tasks/gen/?q={query}", { }, "GET"))

@app.command()
def get(ctx: typer.Context,
        task_id: str = typer.Argument(None, help = "IDs of the Tasks to be fetched"),
        recurse: bool = typer.Option(True, help="Whether to recursively get task and its children")):
    """ Gets one or more tasks given IDs.  If no IDs are specified then a list of all tasks are returned."""
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj["descendants"])
    present(ctx, newapi(ctx.obj, f"/tasks/{task_id}?recurse={recurse}", { }, "GET"))

@app.command()
def clone(ctx: typer.Context,
          taskid: str = typer.Argument(..., help = "ID of the task to clone"),
          shallow: bool = typer.Option(False, help = "Whether to do a shallow or a deep copy")):
    """ Clones a task into a new task. """
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj["descendants"])
    result = newapi(ctx.obj, f"/tasks/{taskid}/copy/", {}, "POST")["task"]
    newtaskid = result["id"]
    present(ctx, newapi(ctx.obj, f"/tasks/{newtaskid}?recurse=true", { }, "GET"))

@app.command()
def join(ctx: typer.Context,
         taskid: str = typer.Argument(..., help = "ID of the task to clone"),
         roles: List[str] = typer.Argument(None, help = "List of more roles to request")):
    """ Request to a join a task as a collaborator. """
    all_roles = roles
    newapi(ctx.obj, f"/tasks/{taskid}/users/join/", {"roles": all_roles}, "POST")

    # Now get it again
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj["descendants"])
    present(ctx, newapi(ctx.obj, f"/tasks/{taskid}?recurse=true", { }, "GET"))


@app.command()
def run(ctx: typer.Context,
        taskid: str = typer.Argument(..., help = "ID of the task to execute"),
        runbook_task_id: str = typer.Option("", help = "ID of the top level runbook being executed.  Will default to taskid"),
        proxy_alias: str= typer.Option("", help="Alias of the proxy to execute on", envvar="DagKnowsProxyAlias"),
        proxy_token: str= typer.Option("", help="Token of the proxy to execute on", envvar="DagKnowsProxyToken"),
        params: str = typer.Option(None, help = "Json dictionary of parameters"),
        forever: bool = typer.Option(False, help = "Whether to repeat for ever"),
        start_in: int = typer.Option(0, help = "Delayed start in this many seconds, 0 => schedule immediately"),
        end_in: int = typer.Option(-1, help = "Do not schedule job after this many seconds (used when repeating jobs)"),
        num_times: int = typer.Option(0, help = "How many times to repeat"),
        interval: int = typer.Option(-1, help = "How often to repeat the job in between.  -ve => no repetitions"),
        interval_type: str = typer.Option("seconds", help = "Interval type - 'seconds', 'minutes', 'hours', 'days'"),
        file: typer.FileText = typer.Option(None, help = "File containing a json of the parameters")):
    """ Execute a task. """
    job = {
        "proxy_alias": proxy_alias,
        "proxy_token": proxy_token,
        "schedule": {
            "start_at": time.time() + start_in,
            "repeat": interval >= 0,
            "forever": forever,
            "num_times": num_times,
            "interval": interval,
            "interval_type": interval_type,
        }
    }
    if end_in > 0:
        job["schedule"]["end_at"] = time.time() + end_in

    job["param_values"] = {}
    if file: payload["param_values"].update(json.load(file))
    if params: job["param_values"].update(json.loads(params))

    present(ctx, newapi(ctx.obj, f"/tasks/{taskid}/execute/", {"job": job}, "POST"))

@app.command()
def delete(ctx: typer.Context,
           task_ids: List[str] = typer.Argument(..., help = "List of ID of the Tasks to be deleted"),
           recurse: bool = typer.Option(False, help="Whether to recursively delete task and its children")):
    """ Delete all tasks with the given IDs. """
    for taskid in task_ids:
        present(ctx, newapi(ctx.obj, f"/tasks/{taskid}?recurse={recurse}", None, "DELETE"))

@app.command()
def removeusers(ctx: typer.Context, 
             task_id: str = typer.Argument(..., help = "Task ID where user permissions are to be added"),
             userids: List[str] = typer.Argument(..., help = "List of userids to remove from a task"),
             recursive: bool = typer.Option(True, help = "Whether to apply recursively to all owned subtasks")):
    """ Remove users from being collaborators on a task.  All their pending and approved permissions are removed. """
    result = newapi(ctx.obj, f"/tasks/{task_id}/users", { "removed_users": userids, "recursive": recursive }, "PUT")
    task = newapi(ctx.obj, f"/tasks/{task_id}?recurse=true")
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj.get("descendants", {}))
    present(ctx, task)

@app.command()
def addperms(ctx: typer.Context, 
             task_id: str = typer.Argument(..., help = "Task ID where user permissions are to be added"),
             perms: List[str] = typer.Argument(..., help = "User perms of the form userid:perm1,perm2,..permN"),
             recursive: bool = typer.Option(True, help = "Whether to apply recursively to all owned subtasks")):
    """ Adds permissions for users on a particular task.  Each permission is of the form:

        userid=perm1,perm2,perm3,....,permN
    """
    payload = {}
    for perm in perms:
        userid,roles = perm.split("=")
        roles = [r.strip() for r in roles.split(",") if r.strip()]
        if userid not in payload:
            payload[userid] = {"roles": []}
        payload[userid]["roles"] = list(set(roles + payload[userid]["roles"]))

    result = newapi(ctx.obj, f"/tasks/{task_id}/users", { "added_permissions": payload, "recursive": recursive }, "PUT")
    task = newapi(ctx.obj, f"/tasks/{task_id}?recurse=true")
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj.get("descendants", {}))
    present(ctx, task)

@app.command()
def removeperms(ctx: typer.Context, 
                task_id: str = typer.Argument(..., help = "Task ID where user permissions are to be removed"),
                perms: List[str] = typer.Argument(..., help = "User perms of the form userid:perm1,perm2,..permN"),
                recursive: bool = typer.Option(True, help = "Whether to apply recursively to all owned subtasks")):
    """ Removes user permissions form a task.  Each permission is of the form:

        userid=perm1,perm2,perm3,....,permN
    """
    payload = {}
    for perm in perms:
        userid,roles = perm.split("=")
        roles = [r.strip() for r in roles.split(",") if r.strip()]
        if userid not in payload:
            payload[userid] = {"roles": []}
        payload[userid]["roles"] = list(set(roles + payload[userid]["roles"]))

    result = newapi(ctx.obj, f"/tasks/{task_id}/users", { "removed_permissions": payload, "recursive": recursive }, "PUT")
    task = newapi(ctx.obj, f"/tasks/{task_id}?recurse=true")
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"], obj.get("descendants", {}))
    present(ctx, task)

@app.command()
def create(ctx: typer.Context,
           title: str = typer.Option(..., help = "Title of the new task"),
           description: str = typer.Option("", help = "Description string for the new task"),
           customid: str = typer.Option("", help = "A custom ID to assign instead of a randomly generated one"),
           tags: str = typer.Option("", help = "Comma separated list of tags, eg 'java,frontend,kubernetes'"),
           file: typer.FileText = typer.Option(None, help = "File containing more task parameters")
       ):
    """ Creates a new task with the given title, description and other parameters from a file. """
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"])
    task_params = {}
    if file: task_params.update(json.load(file))
    if title: task_params["title"] = title
    if description: task_params["description"] = description
    if tags: task_params["tags"] = tags.split(",")
    if customid.strip(): task_params["id"] = customid.strip()
    newtask = newapi(ctx.obj, "/tasks/", {"task": task_params}, "POST")
    present(ctx, newtask)

@app.command()
def update(ctx: typer.Context, task_id: str = typer.Argument(..., help = "ID of the task to be updated"),
           title: str = typer.Option(None, help="New title to be set for the Task"),
           description: str = typer.Option(None, help="New description to be set for the Task"),
           file: typer.FileText = typer.Option(None, help = "File containing more task parameters update")
        ):
    """ Update a task. """
    ctx.obj.tree_transformer = lambda obj: rich_task_info(obj["task"])
    update_mask = []
    params = {}
    sub_task_ops = []
    if file:
        contents = json.load(file)
        for k,v in contents.items():
            if k == "sub_task_ops":
                # we have subtask ops
                sub_task_ops = v
            else:
                params[k] = v
                update_mask.append(k)
    if title: 
        update_mask.append("title")
        params["title"] = title
    if description: 
        update_mask.append("description")
        params["description"] = description
    payload = {
        "task": params,
        "update_mask": update_mask,
        "sub_task_ops": sub_task_ops ,
    }
    resp = newapi(ctx.obj, f"/tasks/{task_id}", payload, "PATCH")
    present(ctx, resp)

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
    present(ctx, newapi(ctx.obj, "/tasks/sync", {
        # "source_info": {
            "source_url": source_url,
            "source_id": source_task_id,
        # },
        "resync": resync,
    }, "GET"))

@app.command()
def push(ctx: typer.Context,
         task_id: str = typer.Argument(None, help = "IDs of the Tasks to push to the community"),
         recurse: bool = typer.Option(True, help="Whether to recursively get task and its children"),
         dest: str = typer.Argument(None, help = "Name of the config use to access the destination.  Make sure you 'dk config init' with this profile first before using it.  If not provided then the default COMMUNITY_URL on the host is used.  This instance cannot be same as your current instance")):
    """ Syncs a task from an external source. """
    payload = { "recurse": recurse, }
    last_profile = ctx.obj.curr_profile
    if dest:
        ctx.obj.curr_profile = dest
        payload["dest_url"] = ctx.obj.resolve("api_host")
        payload["dest_token"] = ctx.obj.access_token
        # reset it
        ctx.obj.curr_profile = last_profile
    apihost = None # "http://localhost:2235/api/v1"
    resp = newapi(ctx.obj, f"/tasks/{task_id}/push/", payload=payload, method="GET", apihost=None)

    present(ctx, resp)

@app.command()
def compile(ctx: typer.Context,
            taskid: str = typer.Argument(..., help = "ID of the task to compile")):
    """ Compile a task and get its executable form. """
    present(ctx, newapi(ctx.obj, f"/tasks/{taskid}/compile/"))
