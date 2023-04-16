
import typer
from dagcli.client import newapi
from typing import List

app = typer.Typer()

@app.command()
def create(ctx: typer.Context,
           title: str = typer.Option(..., help = "Title of the new Dag"),
           description: str = typer.Option("", help = "Description string for your Dag")):
    newapi(ctx, "/v1/dags", {
        "title": title,
        "description": description,
    }, "POST")

@app.command()
def delete(ctx: typer.Context, dag_ids: List[str] = typer.Argument(..., help = "List of ID of the Dags to be deleted")):
    for dagid in dag_ids:
        newapi(ctx, f"/v1/dags/{dagid}", None, "DELETE")

@app.command()
def get(ctx: typer.Context, dag_ids: List[str] = typer.Argument(None, help = "IDs of the Dags to be fetched")):
    if not dag_ids:
        newapi(ctx, "/v1/dags", { }, "GET")
    elif len(dag_ids) == 1:
        newapi(ctx, f"/v1/dags/{dag_ids[0]}", { }, "GET")
    else:
        newapi(ctx, "/v1/dags:batchGet", { "ids": dag_ids }, "GET")

@app.command()
def search(ctx: typer.Context, title: str = typer.Option("", help = "Title to search for Dags by")):
    return newapi(ctx, "/v1/dags", {
        "title": title,
    }, "GET")

@app.command()
def modify(ctx: typer.Context, dag_id: str = typer.Argument(..., help = "ID of the dag to be updated"),
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
    newapi(ctx, f"/v1/dags/{dag_id}", {
        "dag": params,
        "update_mask": ",".join(update_mask),
    }, "PATCH")

"""
@app.command()
def add_nodes(ctx: typer.Context, dag_id: str, node_ids: List[str] = typer.Argument(..., help = "List of Node IDs to add to the Dag")):
    # dagcli nodes create title --dag_id = this
    if not node_ids: return
    for node_id in node_ids:
        node = newapi(ctx, f"/v1/nodes/{node_id}")
        title =  node["node"]["node"]["title"]
        payload = {
            "node": {
                "dag_id": dag_id,
                "node": {
                    "id": node_id,
                    "title": title,
                }
            }
        }
        newapi(ctx, f"/v1/nodes", payload, "POST")
"""

@app.command()
def remove_nodes(ctx: typer.Context, 
                 dag_id: str = typer.Option(..., help = "Dag ID to add a new edge in"),
                 node_ids: List[str] = typer.Argument(..., help = "List of Node IDs to remove from the Dag")):
    if not node_ids: return
    newapi(ctx, f"/v1/dags/{dag_id}", {
        "remove_nodes": node_ids,
    }, "PATCH")

@app.command()
def connect(ctx: typer.Context,
            dag_id: str = typer.Option(..., help = "Dag ID to add a new edge in"),
            src_node_id: str = typer.Option(..., help = "Source node ID to start connection from"),
            dest_node_id: str = typer.Option(..., help = "Destination node ID to add connection to")):
    newapi(ctx, f"/v1/nodes/{src_node_id}", {
        "node": {
            "dag_id": dag_id,
        },
        "add_nodes": [ dest_node_id ]
    }, "PATCH")

@app.command()
def disconnect(ctx: typer.Context,
            dag_id: str = typer.Option(..., help = "Dag ID to remove an new edge from"),
            src_node_id: str = typer.Option(..., help = "Source node ID to remove connection from"),
            dest_node_id: str = typer.Option(..., help = "Destination node ID to remove connection in")):
    newapi(ctx, f"/v1/nodes/{src_node_id}", {
        "node": {
            "dag_id": dag_id,
        },
        "remove_nodes": [ dest_node_id ]
    }, "PATCH")
