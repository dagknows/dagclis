import typer
import json
from typing import List
from dagcli.client import newapi, oldapi
from dagcli.utils import present
from dagcli.transformers import *
app = typer.Typer()

@app.command()
def new(ctx: typer.Context,
        dag_id: str = typer.Option(..., help = "ID of Dag to create an execution for"),
        node_id: str = typer.Option(..., help = "ID of node to start from.  Will default to Dag root node"),
        session_id: str = typer.Option(..., help = "ID of Session to publish results in"),
        proxy: str= typer.Option(..., help="Address of the proxy to send execution to"),
        params: str = typer.Option(None, help = "Json dictionary of parameters"),
        file: typer.FileText = typer.Option(None, help = "File containing a json of the parametres"),
        schedule: str = typer.Option(None, help = "Json dictionary of execution schedule")):
    """ Create a new execution on dag. """

    payload = {
        "session_id": session_id,
        "proxy_address": proxy,
        "stop_on_problem": False,
        "full_sub_dag": True,
        "params": {},
        "node_id": node_id,
    }
    try:
        if schedule: payload["schedule"] = json.loads(schedule)
        if params: payload["params"] = json.loads(params)
        if file: payload["params"] = json.load(file)
    except:
        ctx.fail("Error parsing json")
    ctx.obj.tree_transformer = lambda obj: f"Created Job: {obj['jobId']}"
    present(ctx, newapi(ctx.obj, f"/v1/dags/{dag_id}/executions", payload, "POST"))

@app.command()
def get(ctx: typer.Context,
        exec_id: str = typer.Argument(None, help = "ID of execution to get")):
    """ Get status of an execution. """
    execution = newapi(ctx.obj, f"/v1/executions/{exec_id}")["execution"]
    problem_info = defaultdict(str)
    if not execution: return
    if "results" in execution and execution["results"]:
        last_info = execution["results"][-1]["info"]
        for node in last_info["confirm_problem"]:
            problem_info[node["node_id"]] = "yes"
        for node in last_info["confirm_not_problem"]:
            problem_info[node["node_id"]] = "no"
    dagid = execution["dagId"]
    dag = newapi(ctx.obj, f"/v1/dags/{dagid}")
    if ctx.obj.output_format == "tree": 
        from rich import print
        print("Execution results from nodes: ")
        for result in execution.get("results", []):
            tshootinfo = result["info"]["tshoot_info"]
            for nodeid, nodeinfo in tshootinfo.items():
                if nodeinfo.get("_to_session", {}):
                    print(nodeid, json.dumps(nodeinfo["_to_session"], indent=4))

        richtree = rich_dag_info_with_exec(dag["dag"], problem_info)
        print("Execution Summary: ")
        print(richtree)
    else:
        present(ctx, execution)
    # ctx.obj.tree_transformer = lambda obj: dag_info_with_exec(obj["dag"], problem_nodes)
    # oldapi("getJob", {"job_id": exec_id}, access_token=ctx.obj.access_token)
