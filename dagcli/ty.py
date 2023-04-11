import typer
import requests
from pprint import pprint
from typing import List

app = typer.Typer(pretty_exceptions_show_locals=False)

@app.callback()
def common_params(ctx: typer.Context,
                  apigw_host: str = typer.Option("http://localhost:8080/api", envvar='DagKnowsApiGatewayHost', help='API endpoint for our CLI to reach'),
                  reqrouter_host : str = typer.Option("https://demo.dagknows.com:8443", envvar='DagKnowsReqRouterHost', help='Environment for our API GW to hit'),
                  log_request: str = typer.Option(False, help='Enables logging of requests'),
                  log_response: str = typer.Option(False, help='Enables logging of responses'),
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
    if ctx.obj["log_request"]:
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
    if ctx.obj["log_response"]:
        print("API Response: ", pprint(result))
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
            newapi(ctx, f"/v1/dags/{dagid}", "DELETE")

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

    return app

def nodes():
    app = typer.Typer()
    return app

def sessions():
    app = typer.Typer()
    return app

def execs():
    app = typer.Typer()
    return app

app.add_typer(dags(), name="dags")
app.add_typer(sessions(), name="sessions")
app.add_typer(nodes(), name="nodes")
app.add_typer(execs(), name="execs")

if __name__ == "__main__":
    app(obj={})
