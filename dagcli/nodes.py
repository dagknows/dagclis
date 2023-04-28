import typer, sys
from typing import List
from dagcli.client import newapi
from dagcli.utils import present
from dagcli.transformers import *
app = typer.Typer()

@app.command()
def get(ctx: typer.Context,
        dag_id: str = typer.Option(None, help="Dag ID in the context of which to get the Node - only for single gets"),
        node_ids: List[str] = typer.Argument(None, help = "IDs of the Nodes to be fetched")):
    """ Get one or more nodes by ID. If the dag_id param is passed then child nodes are also returned in the context of the Dag. """
    payload = {}
    if dag_id:
        payload["dag_id"] = dag_id
    if not node_ids:
        ctx.obj.tree_transformer = lambda obj: node_list_transformer(obj["nodes"])
        results = newapi(ctx.obj, "/v1/nodes", payload, "GET")
    elif len(node_ids) == 1:
        ctx.obj.tree_transformer = lambda obj: node_info_transformer(obj["node"])
        results = newapi(ctx.obj, f"/v1/nodes/{node_ids[0]}", payload, "GET")
    else:
        ctx.obj.tree_transformer = lambda obj: node_list_transformer(obj["nodes"].values())
        payload["ids"] = node_ids
        results = newapi(ctx.obj, "/v1/nodes:batchGet", payload, "GET")
    present(ctx, results)

@app.command()
def search(ctx: typer.Context, title: str = typer.Option("", help = "Title to search for Nodes by")):
    """ Search for nodes by title. """
    return present(ctx, newapi(ctx.obj, "/v1/nodes", {
        "title": title,
    }, "GET"))

@app.command()
def modify(ctx: typer.Context, node_id: str = typer.Argument(..., help = "ID of the Dag to be updated"),
           title: str = typer.Option(None, help="New title to be set for the Dag"),
           description: str = typer.Option(None, help="New description to be set for the Dag"),
           comment: str = typer.Option(None, help="Comment describing the modification"),
           input_params: str = typer.Option("", help="Comma seperated list of input params for this node"),
           detection: str = typer.Option(None, help="Steps with the commands for detection"),
           detection_script: typer.FileText = typer.Option(None, help="Path of the file containing the detection script"),
           remediation: str = typer.Option(None, help="Steps with the commands for remediation"),
           remediation_script: typer.FileText = typer.Option(None, help="Path of the file containing the remediation script")):
    """ Modify a node's parameters."""
    update_mask = set()
    params = {}
    if title: 
        update_mask.add("title")
        params["title"] = title
    if description: 
        update_mask.add("description")
        params["description"] = description
    if comment: 
        update_mask.add("comment")
        params["comments"] = [{"text": comment}]
    if input_params:
        update_mask.add("inputparams")
        params["input_params"] = {k:k for k in input_params.split(",")}

    if detection:
        update_mask.add("detection")
        params["detection"] = { "script": detection }
    elif detection_script:
        update_mask.add("detection")
        params["detection"] = { "script": detection_script.read() }

    if remediation:
        update_mask.add("remediation")
        params["remediation"] = { "script": remediation }
    elif remediation_script:
        update_mask.add("remediation")
        params["remediation"] = { "script": remediation_script.read() }

    if not update_mask:
        ctx.get_help()
        ctx.fail("Atleast one option must be specified")

    if ctx.obj.output_format == "tree": ctx.obj.output_format == "yaml"
    result = newapi(ctx.obj, f"/v1/nodes/{node_id}", {
        "node": {
            "node": params,
        },
        "update_mask": ",".join(update_mask),
    }, "PATCH")
    present(ctx, result["node"])

@app.command()
def delete(ctx: typer.Context, node_ids: List[str] = typer.Argument(..., help = "List of ID of the Nodes to be deleted")):
    """ Delete one or more nodes by ID. """
    for nodeid in node_ids:
        present(ctx, newapi(ctx.obj, f"/v1/nodes/{nodeid}", None, "DELETE"))

@app.command()
def create(ctx: typer.Context,
        dag_id: str = typer.Option(None, help = "ID of Dag to create a node in"),
        title: str = typer.Option(..., help = "Title of the new Node"),
        description: str = typer.Option("", help = "Description string for your Node"),
        input_params: str = typer.Option("", help = 'Comma separated list of names of all parameters to be passed to detection script, eg "ip, host, username"'),
        detection_script: typer.FileText = typer.Option(None, help = "File containing the detection script for this Node"),
        remediation_script: typer.FileText = typer.Option(None, help = "File containing the remediation script for this Node")):
    """ Create a Node.  The node can be within a dag or independent (and added to dags later). """

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
    if ctx.obj.output_format == "tree": ctx.obj.output_format == "yaml"
    result = newapi(ctx.obj, f"/v1/nodes", payload, "POST")
    present(ctx, result["node"])
