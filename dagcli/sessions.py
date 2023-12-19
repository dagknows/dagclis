import typer
from typing import List
from dagcli.client import newapi
from dagcli.utils import present, ensure_shellconfigs, print_reco, get_curr_shell
from dagcli.transformers import *
from dagcli import forwarder
import subprocess, os, base64, platform
import requests
import traceback
import psutil
import time
import threading

from dagcli.utils import disable_urllib_warnings
disable_urllib_warnings()

PLATFORM = platform.uname()
SYSTEM_NAME = PLATFORM.system.lower()

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
def add_users(ctx: typer.Context, session_id: str,
             user_ids: List[str] = typer.Option(..., help = "First user id to add to the session"),
             userids: List[str] = typer.Argument(None, help = "List of more user IDs to add to the session"),
             ):
    """ Add users to a session. """
    all_user_ids = user_ids + userids
    if not all_user_ids: return
    if ctx.obj.output_format == "tree": 
        ctx.obj.data["output_format"] = "yaml"
    result = newapi(ctx.obj, f"/v1/sessions/{session_id}", {
        "session": {},
        "add_users": all_user_ids,
    }, "PATCH")
    present(ctx, result)

@app.command()
def remove_users(ctx: typer.Context, session_id: str,
                user_ids: List[str] = typer.Option(..., help = "First user IDs to remove from the session"),
                userids: List[str] = typer.Argument(None, help = "List of more user IDs to remove from the session")):
    """ Remove users from a session. """
    all_user_ids = user_ids + userids
    if not all_user_ids: return
    if ctx.obj.output_format == "tree": 
        ctx.obj.data["output_format"] = "yaml"
    result = newapi(ctx.obj, f"/v1/sessions/{session_id}", {
        "session": {},
        "remove_users": all_user_ids,
    }, "PATCH")
    present(ctx, result)

@app.command()
def join(ctx: typer.Context,
         session_id: str = typer.Argument(..., help="Session ID to join and start recording.")):
    """ Join's an existing sessions.  Any previous sessions are flushed out and exported. """
    start_shell(ctx, session_id)

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
    start_shell(ctx, session_id)


@app.command()
def flush(ctx: typer.Context,
          session_id: str = typer.Argument(..., help="Session ID to flush and export."),
          sync: bool = typer.Option(True, help="Whether to flush synchronously or asynchronolusly.")):
    """ Flush all accumulated commands to the server. """
    # Get hostname
    p = subprocess.run("hostname", shell=True, stdout=subprocess.PIPE)
    hostname =  p.stdout.decode('utf-8').strip()

    # Read the typescript file
    blobfile = ctx.obj.getpath(f"sessions/{session_id}/cliblob", is_dir=False)
    if not os.path.isfile(blobfile): return
    cliblobs = open(blobfile, "rb").read()
    # cliblobb64 = base64.b64encode(cliblobs.encode()).decode().strip("\n")
    cliblobb64 = base64.b64encode(cliblobs).decode().strip("\n")
    if not cliblobb64: return

    # Do same with commands
    cmdfile = ctx.obj.getpath(f"sessions/{session_id}/commands", is_dir=False)
    if not os.path.isfile(cmdfile):
        return
    cmdblobs = open(cmdfile, "rb").read()
    # cmdblobb64 = base64.b64encode(cmdblobs.encode()).decode().strip("\n")
    cmdblobb64 = base64.b64encode(cmdblobs).decode().strip("\n")
    if not cmdblobb64: return
 
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
    if apihost.endswith("/api"):
        rrhost = apihost[:-len("/api")]
    else:
        raise Exception(f"Invalid RRHost: {apihost}")

    write_backup = True
    errmsg = ""
    try:
        forwarder.submit(ctx, rrhost, headers, reqObj, sync=sync)
    except Exception as error:
        # back it up if there is a failure
        write_backup = True
        print("Err: ", traceback.format_exc())
        errmsg = f"{time.time()} Server error accepting CLI command and outputs.  Backing up locally"
        print(errmsg)

    if write_backup:
        blobfilebak = ctx.obj.getpath(f"sessions/{session_id}/cliblob.bak", is_dir=False, ensure=True)
        with open(blobfilebak, "a") as bf:
            if errmsg: bf.write(errmsg + "\n")
            bf.write(open(blobfile).read())

        cmdfilebak = ctx.obj.getpath(f"sessions/{session_id}/commands.bak", is_dir=False, ensure=True)
        with open(cmdfilebak, "a") as cf:
            if errmsg: cf.write(errmsg + "\n")
            cf.write(open(cmdfile).read())

    # Now truncate both the files so we can restart
    open(blobfile, "a").truncate(0)
    open(cmdfile, "a").truncate(0)

def script_already_started(ctx, session_id):
    sessionspath = ctx.obj.getpath(f"sessions", is_dir=True, ensure=True)
    ctx.obj.getpath(f"sessions/{session_id}", is_dir=True, ensure=True)
    blobfile = ctx.obj.getpath(f"sessions/{session_id}/cliblob")
    currpid = os.getpid()
    currproc = psutil.Process(currpid)
    while currproc:
        if currproc.name() == "script" and currproc.cmdline()[-1] == blobfile:
            print("You have already joined this session.")
            return True
        currproc = currproc.parent()

    # see if *any* session has been started for another sesion_id (except this)
    for proc in psutil.process_iter():
        if proc.name() == "script":
            cmdline = proc.cmdline()[-1]
            if cmdline != blobfile and cmdline.startswith(sessionspath):
                parent, basename = os.path.split(cmdline)
                _, another_session_id = os.path.split(parent)
                print(f"Another session is currently joined: {another_session_id}")
                return True
    return False

def start_shell(ctx: typer.Context, session_id: str):
    ctx.obj.getpath(f"sessions/{session_id}", is_dir=True, ensure=True)

    # Before doing so ensure we have our forwarder running
    # threading.Thread(target=forwarder.ensure, args=(ctx, 12000)).start()

    if script_already_started(ctx, session_id):
        return

    if not ensure_shellconfigs(ctx):
        typer.echo("Cannot start shell without updating shell configs")
        return

    # ctx.obj.getpath("enable_recording", ensure=True)
    with open(ctx.obj.getpath("current_profile", profile_relative=False), "w") as currproffile:
        currproffile.write(ctx.obj.curr_profile)
    with open(ctx.obj.getpath("current_session"), "w") as currsessfile:
        currsessfile.write(session_id)

    blobfile = ctx.obj.getpath(f"sessions/{session_id}/cliblob")
    # session_url = ctx.obj.profile_data["api_host"].replace("/api", f"/member?convId={session_id}")
    session_url = ctx.obj.profile_data["api_host"].replace("/api", f"/cli-sessions/{session_id}")
    print("-" * 80)
    print("")
    print(f"DagKnows session recording started")
    print("")
    print(f"id: {session_id}")
    print(f"url: {session_url}")
    print("")
    print(f"To join this session from another terminal, run: 'dk session join {session_id}'")
    print("")
    print("-" * 80)
    shell_type = get_curr_shell()
    if SYSTEM_NAME == "darwin": ## shell_type == "bash":
        subprocess.run(f"script -a -q -F {blobfile}", shell=True)
    else:
        subprocess.run(f"script -a -q -f {blobfile}", shell=True)
    subprocess.run(f"reset")
    print(f"DagKnows Shell Recording Turned Off")

@app.command()
def start(ctx: typer.Context):
    """ Global starting of a script to capture all commands.  All user provided profile and session IDs will be overridden and the current_session/current_profile in ~/.dagknows folder will be taken. """
    proffile = ctx.obj.getpath("current_profile", profile_relative=False)
    sessfile = ctx.obj.getpath("current_session")
    session_id = profile = ""
    if os.path.isfile(sessfile):
        session_id = open(sessfile).read().strip()
    if os.path.isfile(proffile):
        profile = open(proffile).read().strip()
    if session_id and profile:
        # Use the profile in the stop command instead of what ever the user provided
        ctx.obj.curr_profile = profile
        blobfile = ctx.obj.getpath(f"sessions/{session_id}/cliblob")
        start_shell(ctx, session_id)

@app.command()
def stop(ctx: typer.Context):
    """ Exports a session currently being recorded. """

    # Stop the forwarder first
    forwarder.stop(ctx)
    proffile = ctx.obj.getpath("current_profile", profile_relative=False)
    sessfile = ctx.obj.getpath("current_session")
    session_id = profile = ""
    if os.path.isfile(sessfile):
        session_id = open(sessfile).read().strip()
    if os.path.isfile(proffile):
        profile = open(proffile).read().strip()
    if session_id and profile:
        # Use the profile in the stop command instead of what ever the user provided
        ctx.obj.curr_profile = profile
        blobfile = ctx.obj.getpath(f"sessions/{session_id}/cliblob")
        currproc = psutil.Process(os.getpid())
        kill_later = []
        for proc in psutil.process_iter():
            if proc.name() == "script" and proc.cmdline()[-1] == blobfile:
                print("Script session terminating: ", proc)
                if proc in currproc.parents():
                    kill_later.append(proc)
                else:
                    parent = proc.parent()
                    proc.kill()

        os.remove(sessfile)
        # os.remove(proffile)
        assert len(kill_later) <= 1, "Cannot be part of too many parent processes??"
        if kill_later:
            kill_later[0].kill()
