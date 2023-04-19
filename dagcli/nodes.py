import typer
from typing import List
from dagcli.client import newapi
from dagcli.utils import present
from dagcli.transformers import *
app = typer.Typer()

@app.command()
def get(ctx: typer.Context,
        dag_id: str = typer.Option(None, help="Dag ID in the context of which to get the Node - only for single gets"),
        node_ids: List[str] = typer.Argument(None, help = "IDs of the Nodes to be fetched")):
    if not node_ids:
        ctx.obj.tree_transformer = lambda obj: node_list_transformer(obj["nodes"])
        present(ctx, newapi(ctx, "/v1/nodes", { }, "GET"))
    elif len(node_ids) == 1:
        ctx.obj.tree_transformer = lambda obj: node_info_transformer(obj["node"])
        payload = {}
        if dag_id:
            payload["dag_id"] = dag_id
        present(ctx, newapi(ctx, f"/v1/nodes/{node_ids[0]}", payload, "GET"))
    else:
        ctx.obj.tree_transformer = lambda obj: node_list_transformer(obj["nodes"].values())
        present(ctx, newapi(ctx, "/v1/nodes:batchGet", { "ids": node_ids }, "GET"))

@app.command()
def search(ctx: typer.Context, title: str = typer.Option("", help = "Title to search for Nodes by")):
    return present(ctx, newapi(ctx, "/v1/nodes", {
        "title": title,
    }, "GET"))

@app.command()
def modify(ctx: typer.Context, node_id: str = typer.Argument(..., help = "ID of the Dag to be updated"),
           title: str = typer.Option(None, help="New title to be set for the Dag"),
           description: str = typer.Option(None, help="New description to be set for the Dag")):
    update_mask = []
    params = {}
    if title: 
        update_mask.append("title")
        params["title"] = title
    if description: 
        update_mask.append("description")
        params["description"] = description

    present(ctx, newapi(ctx, f"/v1/nodes/{node_id}", {
        "node": {
            "node": params,
        },
        "update_mask": ",".join(update_mask),
    }, "PATCH"))

@app.command()
def delete(ctx: typer.Context, node_ids: List[str] = typer.Argument(..., help = "List of ID of the Nodes to be deleted")):
    for nodeid in node_ids:
        present(ctx, newapi(ctx, f"/v1/nodes/{nodeid}", None, "DELETE"))

@app.command()
def create(ctx: typer.Context,
        dag_id: str = typer.Option(None, help = "ID of Dag to create a node in"),
        title: str = typer.Option(..., help = "Title of the new Node"),
        description: str = typer.Option("", help = "Description string for your Node"),
        input_params: str = typer.Option("", help = 'Comma separated list of names of all parameters to be passed to detection script, eg "ip, host, username"'),
        detection_script: typer.FileText = typer.Option(None, help = "File containing the detection script for this Node"),
        remediation_script: typer.FileText = typer.Option(None, help = "File containing the remediation script for this Node")):

    inparams = [p.strip() for p in input_params.split(",") if p.strip()]
    payload = {
        "node": {
            "node": {
                "title": title,
                "description": description,
                "input_params": dict({p: p for p in inparams})
            }
        }
    }
    if dag_id: payload["node"]["dag_id"] = dag_id
    if detection_script:
        payload["node"]["node"]["detection"] = {
            "script": detection_script.read()
        }
    if remediation_script:
        payload["node"]["node"]["remediation"] = {
            "script": remediation_script.read()
        }
    present(ctx, newapi(ctx, f"/v1/nodes", payload, "POST"))
