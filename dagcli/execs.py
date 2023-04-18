import typer
from typing import List
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

    payload = {
        "session_id": session_id,
        "proxy_address": proxy,
        "stop_on_problem": False,
        "full_sub_dag": True,
        "params": {},
        "node_id": node_id,
    }
    if schedule: payload["schedule"] = json.loads(schedule)
    if params: payload["params"] = json.loads(params)
    if file: payload["params"] = json.load(file)
    newapi(ctx, f"/v1/dags/{dag_id}/executions", payload, "POST")