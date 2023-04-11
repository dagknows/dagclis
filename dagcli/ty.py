import typer
from ipdb import set_trace
import requests
from pprint import pprint
from typing import List

app = typer.Typer(pretty_exceptions_show_locals=False)

@app.callback()
def common_params(ctx: typer.Context,
                  apigw_host: str = typer.Option("http://localhost:8080/api", envvar='DagKnowsApiGatewayHost', help='API endpoint for our CLI to reach'),
                  reqrouter_host : str = typer.Option("https://demo.dagknows.com:8443", envvar='DagKnowsReqRouterHost', help='Environment for our API GW to hit'),
                  log_request: bool = typer.Option(False, help='Enables logging of requests'),
                  log_response: bool = typer.Option(False, help='Enables logging of responses'),
                  auth_token: str = typer.Option(..., envvar='DagKnowsAuthToken', help='AuthToken for accessing DagKnows')):
    ctx.obj = {
        "apigw_host": apigw_host,
        "reqrouter_host": reqrouter_host,
        "auth_token": auth_token,
        "log_request": log_request,
        "log_response": log_response,
        "headers": {
            "Authorization": f"Bearer {auth_token}",
            "DagKnowsReqRouterHost": reqrouter_host,
        }
    }

def newapi(ctx: typer.Context, path, payload=None, method = ""):
    url = ctx.obj["apigw_host"]
    method = method.lower()
    headers = ctx.obj["headers"]
    if not method.strip():
        if payload: method = "post"
        else: method = "get"
    if path.startswith("/"):
        path = path[1:]
    url = f"{url}/{path}"
    methfunc = getattr(requests, method)
    if ctx.obj["log_request"] == True:
        print(f"API Request: {method.upper()} {url}: ", payload)
    if payload:
        if method == "get":
            resp = methfunc(url, params=payload, headers=headers)
        else:
            resp = methfunc(url, json=payload, headers=headers)
    else:
        resp = methfunc(url, headers=headers)
    # print(json.dumps(resp.json(), indent=4))
    result = resp.json()
    pprint(result)
    return result

def dags():
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
    def remove_nodes(ctx: typer.Context, dag_id: str, node_ids: List[str] = typer.Argument(..., help = "List of Node IDs to remove from the Dag")):
        if not node_ids: return
        newapi(ctx, f"/v1/dags/{dag_id}", {
            "remove_nodes": node_ids,
        }, "PATCH")

    @app.command()
    def connect(ctx: typer.Context,
                dag_id: str,
                src_node_id: str = typer.Option(..., help = "Source node ID to start connection from"),
                dest_node_id: str = typer.Option(..., help = "Destination node ID to add connection to")):
        # src_node = newapi(ctx, f"/v1/nodes/{src_node_id}", {}, "GET")
        newapi(ctx, f"/v1/nodes/{src_node_id}", {
            "node": {
                "dag_id": dag_id,
            },
            "add_nodes": [ dest_node_id ]
        }, "PATCH")

    @app.command()
    def disconnect(ctx: typer.Context,
                dag_id: str,
                src_node_id: str = typer.Argument(..., help = "Source node ID to remove connection from"),
                dest_node_id: str = typer.Argument(..., help = "Destination node ID to remove connection in")):
        src_node = newapi(ctx, f"/v1/nodes/{src_node_id}", {}, "GET")
        newapi(ctx, f"/v1/nodes/{node_id}", {
            "node": {
                "dag_id": dag_id,
            },
            "remove_nodes": [ dest_node_id ]
        }, "PATCH")

    return app

def execs():
    app = typer.Typer()

    @app.command()
    def new(ctx: typer.Context,
            dag_id: str = typer.Option(..., help = "ID of Dag to create an execution for"),
            session_id: str = typer.Option(..., help = "ID of Session to publish results in"),
            proxy: str= typer.Option(..., help="Address of the proxy to send execution to"),
            node_id: str = typer.Option(None, help = "ID of node to start from.  Will default to Dag root node"),
            params: str = typer.Option(None, help = "Json dictionary of parameters"),
            file: typer.FileText = typer.Option(None, help = "File containing a json of the parametres"),
            schedule: str = typer.Option(None, help = "Json dictionary of execution schedule")):

        payload = {
            "session_id": session_id,
            "proxy_address": proxy,
            "stop_on_problem": False,
            "full_sub_dag": True,
            "params": {}
        }
        dag = newapi(ctx, f"/v1/dags/{dag_id}")
        if node_id:
            payload["node_id"] = node_id
        else:
            payload["node_handle"] = dag["dag"]["title"]

        if schedule: payload["schedule"] = json.loads(schedule)
        if params: payload["params"] = json.loads(params)
        if file: payload["params"] = json.load(file)
        newapi(ctx, f"/v1/dags/{dag_id}/executions", payload, "POST")

    return app

def sessions():
    app = typer.Typer()

    @app.command()
    def create(ctx: typer.Context,
               subject: str = typer.Option(..., help = "Subject of the new session")):
        newapi(ctx, "/v1/sessions", {
            "subject": subject,
        }, "POST")

    @app.command()
    def get(ctx: typer.Context, session_ids: List[str] = typer.Argument(None, help = "IDs of the Sessions to be fetched")):
        if not session_ids:
            newapi(ctx, "/v1/sessions", { }, "GET")
        elif len(session_ids) == 1:
            newapi(ctx, f"/v1/sessions/{session_ids[0]}", { }, "GET")
        else:
            newapi(ctx, "/v1/sessions:batchGet", { "ids": session_ids }, "GET")

    @app.command()
    def delete(ctx: typer.Context, session_ids: List[str] = typer.Argument(..., help = "List of ID of the Sessions to be deleted")):
        for sessionid in session_ids:
            newapi(ctx, f"/v1/sessions/{sessionid}", None, "DELETE")

    @app.command()
    def search(ctx: typer.Context, subject: str = typer.Option("", help = "Subject to search for Sessions by")):
        return newapi(ctx, "/v1/sessions", {
            "title": subject,
        }, "GET")

    @app.command()
    def add_user(ctx: typer.Context, session_id: str, user_ids: List[str] = typer.Argument(..., help = "List of user IDs to add to the session")):
        if not user_ids: return
        newapi(ctx, f"/v1/sessions/{session_id}", {
            "session": {},
            "add_users": user_ids,
        }, "PATCH")

    @app.command()
    def remove_user(ctx: typer.Context, session_id: str, user_ids: List[str] = typer.Argument(..., help = "List of user IDs to remove from the session")):
        if not user_ids: return
        newapi(ctx, f"/v1/sessions/{session_id}", {
            "session": {},
            "remove_users": user_ids,
        }, "PATCH")

    return app

def nodes():
    app = typer.Typer()

    @app.command()
    def get(ctx: typer.Context,
            dag_id: str = typer.Option(None, help="Dag ID in the context of which to get the Node - only for single gets"),
            node_ids: List[str] = typer.Argument(None, help = "IDs of the Nodes to be fetched")):
        if not node_ids:
            newapi(ctx, "/v1/nodes", { }, "GET")
        elif len(node_ids) == 1:
            payload = {}
            if dag_id:
                payload["dag_id"] = dag_id
            newapi(ctx, f"/v1/nodes/{node_ids[0]}", payload, "GET")
        else:
            newapi(ctx, "/v1/nodes:batchGet", { "ids": node_ids }, "GET")

    @app.command()
    def search(ctx: typer.Context, title: str = typer.Option("", help = "Title to search for Nodes by")):
        return newapi(ctx, "/v1/nodes", {
            "title": title,
        }, "GET")

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

        newapi(ctx, f"/v1/nodes/{node_id}", {
            "node": {
                "node": params,
            },
            "update_mask": ",".join(update_mask),
        }, "PATCH")

    @app.command()
    def delete(ctx: typer.Context, node_ids: List[str] = typer.Argument(..., help = "List of ID of the Nodes to be deleted")):
        for nodeid in node_ids:
            newapi(ctx, f"/v1/nodes/{nodeid}", None, "DELETE")

    @app.command()
    def create(ctx: typer.Context,
            dag_id: str = typer.Option(None, help = "ID of Dag to create a node in"),
            title: str = typer.Option(..., help = "Title of the new Node"),
            description: str = typer.Option("", help = "Description string for your Node"),
            detection_script: typer.FileText = typer.Option(None, help = "File containing the detection script for this Node"),
            remediation_script: typer.FileText = typer.Option(None, help = "File containing the remediation script for this Node")):

        payload = {
            "node": {
                "node": {
                    "title": title,
                    "description": description,
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
        newapi(ctx, f"/v1/nodes", payload, "POST")

    return app

app.add_typer(dags(), name="dags")
app.add_typer(sessions(), name="sessions")
app.add_typer(nodes(), name="nodes")
app.add_typer(execs(), name="execs")

if __name__ == "__main__":
    app(obj={})
