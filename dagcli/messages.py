
import typer
from typing import List
from dagcli.client import newapi, oldapi
from dagcli.utils import present
from dagcli.transformers import *
app = typer.Typer()


@app.command()
def list(ctx: typer.Context,
         session_id: str = typer.Option(..., help = "ID of session in which to get messages"),
         query: str = typer.Option("", help = "Search messages by text/subject")):
    if ctx.obj.output_format == "tree": 
        ctx.obj.data["output_format"] = "yaml"
    present(ctx, oldapi("getConvOrCreate", {"id": session_id}, access_token=ctx.obj.access_token))

@app.command()
def get(ctx: typer.Context,
        msg_ids: List[str] = typer.Argument(None, help = "IDs of the messages to be fetched in a session")):
    if ctx.obj.output_format == "tree": 
        ctx.obj.data["output_format"] = "yaml"
    if len(message_ids) == 1:
        present(ctx, newapi(ctx.obj, f"/v1/messages/{message_ids[0]}", { }, "GET"))
    else:
        present(ctx, newapi(ctx.obj, "/v1/messages:batchGet", { "ids": message_ids }, "GET"))

@app.command()
def send(ctx: typer.Context, 
         session_id: str = typer.Option(..., help = "ID of session in which to get messages"),
         message: List[str] = typer.Argument(None, help = "Message to send to the group")):
    if message:
        oldapi("message", {
                    "msg": " ".join(message),
                    "conv_id": session_id,
                    "search_chat_mode": "chat",
                    "nobroadcast": False,
                    "nostore": False,
                }, access_token=ctx.obj.access_token)


@app.command()
def cmd(ctx: typer.Context, 
         session_id: str = typer.Option(..., help = "ID of session in which to get messages"),
         proxy: str = typer.Option(..., help = "Proxy needed to send command to"),
         cmd: List[str] = typer.Argument(None, help = "Message to send to the group")):
    if cmd:
        fullcmd = " ".join(cmd)
        oldapi("message", {
                    "msg": f"@{proxy}.{fullcmd}",
                    "conv_id": session_id,
                    "proxy": {"alias": proxy},
                    "search_chat_mode": "chat",
                    "nobroadcast": False,
                    "nostore": False,
                }, access_token=ctx.obj.access_token)
