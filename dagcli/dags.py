
import typer
from dagcli.client import newapi
from dagcli.utils import present
from dagcli.transformers import *
from typing import List

app = typer.Typer()

@app.command()
def create(ctx: typer.Context,
           title: str = typer.Option(..., help = "Title of the new Dag"),
           description: str = typer.Option("", help = "Description string for your Dag")):
    """ Creates a new dag with the given title and description. """
    ctx.obj.tree_transformer = lambda obj: dag_info_with_exec(obj["dag"])
    present(ctx, newapi(ctx.obj, "/v1/dags", {
        "title": title,
        "description": description,
    }, "POST"))

@app.command()
def delete(ctx: typer.Context, dag_ids: List[str] = typer.Argument(..., help = "List of ID of the Dags to be deleted")):
    """ Delete all dags with the given IDs. """
    for dagid in dag_ids:
        present(ctx, newapi(ctx.obj, f"/v1/dags/{dagid}", None, "DELETE"))

@app.command()
def get(ctx: typer.Context,
        dag_ids: List[str] = typer.Argument(None, help = "IDs of the Dags to be fetched")):
    """ Gets one or more dags given IDs.  If no IDs are specified then a list of all dags is done.  Otherwise for each Dag ID provided its info is fetched. """
    if not dag_ids:
        ctx.obj.tree_transformer = lambda obj: dag_list_transformer(obj["dags"])
        present(ctx, newapi(ctx.obj, "/v1/dags", { }, "GET"))
    elif len(dag_ids) == 1:
        ctx.obj.tree_transformer = lambda obj: rich_dag_info_with_exec(obj["dag"])
        present(ctx, newapi(ctx.obj, f"/v1/dags/{dag_ids[0]}", { }, "GET"))
    else:
        ctx.obj.tree_transformer = lambda obj: dag_list_transformer(obj["dags"].values())
        present(ctx, newapi(ctx.obj, "/v1/dags:batchGet", { "ids": dag_ids }, "GET"))

@app.command()
def search(ctx: typer.Context, title: str = typer.Option("", help = "Title to search for Dags by")):
    """ Searches for dags by a given title. """
    ctx.obj.tree_transformer = lambda obj: dag_list_transformer(obj["dags"])
    present(ctx, newapi(ctx.obj, "/v1/dags", {
        "title": title,
    }, "GET"))

@app.command()
def modify(ctx: typer.Context, dag_id: str = typer.Argument(..., help = "ID of the dag to be updated"),
           title: str = typer.Option(None, help="New title to be set for the Dag"),
           description: str = typer.Option(None, help="New description to be set for the Dag")):
    """ Modifies the title or description of a Dag. """
    update_mask = []
    params = {}
    if title: 
        update_mask.append("title")
        params["title"] = title
    if description: 
        update_mask.append("description")
        params["description"] = description
    present(ctx, newapi(ctx.obj, f"/v1/dags/{dag_id}", {
        "dag": params,
        "update_mask": ",".join(update_mask),
    }, "PATCH"))

@app.command()
def add_nodes(ctx: typer.Context, 
              dag_id: str = typer.Option(..., help = "Dag ID to remove nodes from"),
              node_ids: List[str] = typer.Option(..., help = "First NodeID to add to the Dag"),
              nodeids: List[str] = typer.Argument(None, help = "List of more Node IDs to add to the Dag")):
    """ Adds nodes (by node IDs) to a Dag.  If a node already exists it is ignored. """
    all_node_ids = node_ids + nodeids
    if all_node_ids:
        result = newapi(ctx.obj, f"/v1/dags/{dag_id}", {
            "add_nodes": all_node_ids,
        }, "PATCH")
        dag = newapi(ctx.obj, f"/v1/dags/{dag_id}")
        ctx.obj.tree_transformer = lambda obj: dag_info_with_exec(obj["dag"])
        present(ctx, dag)

@app.command()
def remove_nodes(ctx: typer.Context, 
                 dag_id: str = typer.Option(..., help = "Dag ID to remove nodes from"),
                 node_ids: List[str] = typer.Option(..., help = "First NodeID to remove from the Dag"),
                 nodeids: List[str] = typer.Argument(..., help = "List of more Node IDs to remove from the Dag")):
    """ Removes nodes from a Dag.  When a node is removed, its child nodes are also removed. """
    nodeids = [n for n in nodeids if n.strip()]
    all_node_ids = node_ids + nodeids
    if all_node_ids:
        newapi(ctx.obj, f"/v1/dags/{dag_id}", {
            "remove_nodes": all_node_ids,
        }, "PATCH")
        dag = newapi(ctx.obj, f"/v1/dags/{dag_id}")
        ctx.obj.tree_transformer = lambda obj: dag_info_with_exec(obj["dag"])
        present(ctx, dag)

@app.command()
def connect(ctx: typer.Context,
            dag_id: str = typer.Option(..., help = "Dag ID to add a new edge in"),
            src_node_id: str = typer.Option(..., help = "Source node ID to start connection from"),
            dest_node_id: str = typer.Option(..., help = "Destination node ID to add connection to")):
    """ Connect src_node_id to dest_node_id creating an edge between them in the given Dag.  If adding an edge results in cycles, the request will fail. """
    result = newapi(ctx.obj, f"/v1/nodes/{src_node_id}", {
        "node": {
            "dag_id": dag_id,
        },
        "add_nodes": [ dest_node_id ]
    }, "PATCH")
    dag = newapi(ctx.obj, f"/v1/dags/{dag_id}")
    ctx.obj.tree_transformer = lambda obj: dag_info_with_exec(obj["dag"])
    present(ctx, dag)

@app.command()
def disconnect(ctx: typer.Context,
            dag_id: str = typer.Option(..., help = "Dag ID to remove an new edge from"),
            src_node_id: str = typer.Option(..., help = "Source node ID to remove connection from"),
            dest_node_id: str = typer.Option(..., help = "Destination node ID to remove connection in")):
    """ Removes the edge between src_node_id and dest_node_id in the given Dag """
    newapi(ctx.obj, f"/v1/nodes/{src_node_id}", {
        "node": {
            "dag_id": dag_id,
        },
        "remove_nodes": [ dest_node_id ]
    }, "PATCH")
    dag = newapi(ctx.obj, f"/v1/dags/{dag_id}")
    ctx.obj.tree_transformer = lambda obj: dag_info_with_exec(obj["dag"])
    present(ctx, dag)
