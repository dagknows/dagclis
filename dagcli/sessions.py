import typer
from typing import List
from dagcli.client import newapi
from dagcli.utils import present
from dagcli.transformers import *
import subprocess, os, base64
import requests

app = typer.Typer()

@app.command()
def create(ctx: typer.Context,
           subject: str = typer.Option(..., help = "Subject of the new session")):
    """ Create a new session. """
    present(ctx, newapi(ctx.obj, "/v1/sessions", {
        "subject": subject,
    }, "POST"))

@app.command()
def get(ctx: typer.Context, session_ids: List[str] = typer.Argument(None, help = "IDs of the Sessions to be fetched")):
    """ Get details about one or more sessions. """
    if ctx.obj.output_format == "tree": 
        ctx.obj.data["output_format"] = "yaml"
    if not session_ids:
        present(ctx, newapi(ctx.obj, "/v1/sessions", { }, "GET"))
    elif len(session_ids) == 1:
        present(ctx, newapi(ctx.obj, f"/v1/sessions/{session_ids[0]}", { }, "GET"))
    else:
        present(ctx, newapi(ctx.obj, "/v1/sessions:batchGet", { "ids": session_ids }, "GET"))

@app.command()
def delete(ctx: typer.Context, session_ids: List[str] = typer.Argument(..., help = "List of ID of the Sessions to be deleted")):
    """ Delete a session. """
    if ctx.obj.output_format == "tree": 
        ctx.obj.data["output_format"] = "yaml"
    for sessionid in session_ids:
        present(ctx, newapi(ctx.obj, f"/v1/sessions/{sessionid}", None, "DELETE"), notree=True)

@app.command()
def search(ctx: typer.Context, subject: str = typer.Option("", help = "Subject to search for Sessions by")):
    """ Search for sessions by subject. """
    if ctx.obj.output_format == "tree": 
        ctx.obj.data["output_format"] = "yaml"
    return present(ctx, newapi(ctx.obj, "/v1/sessions", {
        "title": subject,
    }, "GET"))

@app.command()
def add_user(ctx: typer.Context, session_id: str, user_ids: List[str] = typer.Argument(..., help = "List of user IDs to add to the session")):
    """ Add a user to a session. """
    if not user_ids: return
    if ctx.obj.output_format == "tree": 
        ctx.obj.data["output_format"] = "yaml"
    present(ctx, newapi(ctx.obj, f"/v1/sessions/{session_id}", {
        "session": {},
        "add_users": user_ids,
    }, "PATCH"))

@app.command()
def remove_user(ctx: typer.Context, session_id: str, user_ids: List[str] = typer.Argument(..., help = "List of user IDs to remove from the session")):
    """ Remove a user from a session. """
    if not user_ids: return
    if ctx.obj.output_format == "tree": 
        ctx.obj.data["output_format"] = "yaml"
    present(ctx, newapi(ctx.obj, f"/v1/sessions/{session_id}", {
        "session": {},
        "remove_users": user_ids,
    }, "PATCH"))

@app.command()
def join(ctx: typer.Context,
         session_id: str = typer.Argument(..., help="Session ID to join and start recording.")):
    """ Join's an existing sessions.  Any previous sessions are flushed out and exported. """
    join_session(ctx, session_id)

@app.command()
def record(ctx: typer.Context,
           subject: str = typer.Option("", help="Create a new session with this subject and start recording")):
    """ Create a new session with the given subject and start recording and exporting commands to it. Any previous sessions are flushed out and exported."""
    if not subject:
        subject = typer.prompt("Enter the subject of the new session to record")
        print("Subject: ", subject)
        if not subject.strip():
            ctx.fail("Please enter a valid subject.")

    # Todo - create
    session = newapi(ctx.obj, "/v1/sessions", { "subject": subject, }, "POST")
    session_id = session["session"]["id"]
    join_session(ctx, session_id)


@app.command()
def flush(ctx: typer.Context,
          session_id: str = typer.Argument(..., help="Session ID to flush and export.")):
    """ Flush all accumulated commands to the server. """
    # Get hostname
    p = subprocess.run("hostname", shell=True, stdout=subprocess.PIPE)
    hostname =  p.stdout.decode('utf-8').strip()

    # Read the typescript file
    blobfile = ctx.obj.getpath(f"sessions/{session_id}/cliblob", is_dir=False)
    if not os.path.isfile(blobfile): return
    cliblobs = open(blobfile).read()
    cliblobb64 = base64.b64encode(cliblobs.encode()).decode().strip("\n")
    if not cliblobb64: return

    # Do same with commands
    cmdfile = ctx.obj.getpath(f"sessions/{session_id}/commands", is_dir=False)
    if not os.path.isfile(cmdfile):
        return
    cmdblobs = open(cmdfile).read()
    cmdblobb64 = base64.b64encode(cmdblobs.encode()).decode().strip("\n")
    if not cmdblobb64: return

    """
    subprocess.run(f"cat {cliblob_file_path} | base64 > {cliblob_file_path_base64}", shell=True)
    cliblob_file_fh = open(cliblob_file_path_base64, "r")
    cliblob = cliblob_file_fh.read()
    cliblob = cliblob.strip('\n')
    #print("Here's base64ed cliblob: ", cliblob)
    cliblob_file_fh.close()
    #print("Done with base64-ing cliblob")
 
    #Read the commands file
    subprocess.run(f"cat {cmd_file_path} | base64 > {cmd_file_path_base64}", shell=True)
    cmd_file_fh = open(cmd_file_path_base64, "r")
    cmd = cmd_file_fh.read()
    cmd = cmd.strip('\n')
    cmd_file_fh.close()
    #print("Done with base64-ing cmds")
    """
 
    # Construct the request
    reqObj = {}
    reqObj['cliblob'] = cliblobb64
    reqObj['cmd'] = cmdblobb64
    reqObj['subject'] = "Done Recording"
    reqObj['hostname'] = hostname
    #print("Constructed request: ", json.dumps(reqObj))
    if session_id:
        reqObj['session_id'] = session_id
    headers = {"Authorization" : f"Bearer {ctx.obj.access_token}"}

    # Hack - need to either move to using the api gateway or prompt
    # for reqrouter host
    apihost =  ctx.obj.resolve("api_host")
    if apihost.startswith("http://localhost"):
        rrhost = "https://localhost"
    elif apihost.endswith("/api"):
        rrhost = apihost[:-len("/api")]
    else:
        raise Exception(f"Invalid RRHost: {apihost}")
    # import ipdb ; ipdb.set_trace()
    respObj = requests.post(f"{rrhost}/processCliBlob", json=reqObj, headers=headers, verify=False)

    # Now truncate both the files so we can restart
    open(blobfile, "a").truncate(0)
    open(cmdfile, "a").truncate(0)


def join_session(ctx: typer.Context, session_id: str):
    ctx.obj.getpath(f"sessions/{session_id}", is_dir=True, ensure=True)
    # ctx.obj.getpath("enable_recording", ensure=True)
    with open(ctx.obj.getpath("current_session", profile_relative=False), "w") as currsessfile:
        currsessfile.write(session_id)
    with open(ctx.obj.getpath("current_profile", profile_relative=False), "w") as currproffile:
        currproffile.write(ctx.obj.curr_profile)
    typer.echo(f"Congratulations.  You are now recording sessions {session_id}")

@app.command()
def stop(ctx: typer.Context):
    """ Exports a session currently being recorded. """
    enable_file = ctx.obj.getpath("enable_recording")
    if os.path.isfile(enable_file):
        os.remove(enable_file)
    typer.echo("Congratulations.  You have stopped recording")
    sessfile = ctx.obj.getpath("current_session", profile_relative=False)
    proffile = ctx.obj.getpath("current_profile", profile_relative=False)
    if os.path.isfile(sessfile): os.remove(sessfile)
    if os.path.isfile(proffile): os.remove(proffile)
