
from ipdb import set_trace
from typing import List
import typer

app = typer.Typer()

# Here we can define top level flags etc - ie check for dk host, auth token, verbosity etc
@app.callback()
def toplevelcback(ctx: typer.Context):
    print("Running Top level callback")

@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def main(ctx: typer.Context):
    print("Hello World")
    for extra_arg in ctx.args:
        print(f"Got extra arg: {extra_arg}")

def dags():
    """ This should be all commands under "dag" """
    app = typer.Typer()
    @app.command()
    def get(ctx: typer.Context, dagid: str):
        print("Getting a dag listing - dags get")

    @app.command()
    def post(ctx: typer.Context):
        print("Crreating a new dag - dags post")

    @app.command("execs2")
    def exec(ctx: typer.Context):
        print("Just an execs listing command")

    app.add_typer(execs(), name="execs")
    return app

def execs():
    app = typer.Typer()
    @app.command()
    def get(ctx: typer.Context, kvpairs: List[str],
                flag1: str=typer.Option(3), flag2: str=typer.Option(4)):
        # This should be interesting - as we can call this from dags or at top level
        print("Getting an exec listing - execs get")
        set_trace()
        pass

    @app.command()
    def post(ctx: typer.Context):
        # This should be interesting - as we can call this from dags or at top level
        print("Creating a new exec - execs post")
    return app

"""
Say e have the "final" trie path of
a b c d e

(we are saying final becuase we want to pass "custom" functions that take a path + method and returns a command hierarchy)

METHOD /v1/myapp/<id1>/myrestype1/<id2/myrestype2 

could result in:

    describe-myrestype2 id1 id2

    or 

    describe-myrestype2-of-myrestyp1 - 

    idea is we are transform the http or grpc method + service path into a command path

NOTE - this is only if user wants an "auto" command to be formed instead manually specifying say via grpc/swagger annotations

So given a command path of "cmd subcmd2 subsubcmd3"
/v1/a/b/c/d/e

cmdfunc := name + child funcs
"""

app.add_typer(dags(), name="dags")
app.add_typer(execs(), name="execs")
if __name__ == "__main__":
    import sys
    set_trace()
    app(obj={})

"""
app2 = typer.Typer()
@app2.command()
def batchget(ctx: typer.Context, ids: List[str], json: str = typer.Option(None), file: typer.FileText = typer.Option(None)):
    # read request params in ctx
    print("Context: ", ctx)
    ctx.ensure_object(dict)
    print("IDs: ", ids, json, file)

@app2.command()
def get(ctx: typer.Context, id: str, json: str = typer.Option(None), file: typer.FileText = typer.Option(None)):
    print("Context: ", ctx)
    ctx.ensure_object(dict)
    print("IDs: ", ids, json, file)
"""
