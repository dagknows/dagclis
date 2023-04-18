
import typer
from typing import List
from dagcli.client import newapi
app = typer.Typer()


def list(ctx: typer.Context,
         session_id: str = typer.Option(..., help = "ID of session in which to get messages"),
         query: str = typer.Option("", help = "Search messages by text/subject")):
    newapi(ctx, f"/v1/sessions/{session_id}/messages", { }, "GET")

@app.command()
def get(ctx: typer.Context,
        msg_ids: List[str] = typer.Argument(None, help = "IDs of the messages to be fetched in a session")):
    if len(message_ids) == 1:
        newapi(ctx, f"/v1/messages/{message_ids[0]}", { }, "GET")
    else:
        newapi(ctx, "/v1/messages:batchGet", { "ids": message_ids }, "GET")

@app.command()
def send(ctx: typer.Context, 
         session_id: str = typer.Option(..., help = "ID of session in which to get messages"),
         message: List[str] = typer.Argument(None, help = "Message to send to the group")):
    if message:
        return newapi(ctx, f"/v1/sessions/{session_id}/messages", {
            "msg": " ".join(message)
        }, "POST")
