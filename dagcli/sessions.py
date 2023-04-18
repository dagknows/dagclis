import typer
from typing import List
from dagcli.client import newapi
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