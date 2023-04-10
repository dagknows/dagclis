
import sys
import itertools
from collections import deque
import requests
from ipdb import set_trace
from typing import List, Union, Dict
import json, os
from pprint import pprint

class CommandActivation(object):
    def __init__(self, name, node, flags=None):
        # All the cli parts that have come so far
        # eg in a cmd cat a b c d --a --b --c 2 e f
        # Name here would indicate each "activation" on the command path
        self.name = name

        # Nodes that were visited along with their specific flags (so we can record
        # node specific flags too) as each part was encountered and we stepped into
        # a child node.
        self.node = node
        self.flags = flags or {}

class CommandContext(object):
    def __init__(self, cli, data=None):
        # The CLI object on which we are operating
        self.cli = cli

        # [0] is always the realroot
        self.cmd_stack = []

        # Again for above example, args would contain all args
        # if "b" was the leaf cmd part then our args would be "c" "d" "e" "f"
        self.args = []

        # Flags are unordered and here would contain a={default_val} b={default_val c=2
        # default value would be chosen based on the type of value found in the swagger spec
        self.flags = {}

        # custom data passed by the user
        self.data = data or {}

    @property
    def cmd_so_far(self):
        return " ".join(c.name for c in self.cmd_stack)

    def get_flag_values(self, flag):
        """ Gets the value of a flag by either getting its explicitly set value
        or the default value from where ever it is specified (eg file, env var etc).
        """
        if flag in self.flags:
            return self.flags[flag]

        for activ in self.cmd_stack:
            node = activ.node
            for fd in node.data.get("flagdefs", []):
                if fd.name == flag:
                    vals = fd.load()
                    if vals:
                        return vals

        # And go through global values
        for fd in self.cli.global_flag_defs:
            if fd.name == flag:
                vals = fd.load()
                if vals:
                    return vals

        return None

    def add_flag_value(self, flag, value):
        """ Adds an extra value for a flag.  No validation is done to see if it is valid or not. """
        if flag not in self.flags:
            self.flags[flag] = []
        self.flags[flag].append(value)
        return self.flags[flag]

    @property
    def last_node(self):
        return self.cmd_stack[-1].node

class FlagDef:
    def __init__(self, name, help_text="", valtype=str, default_value=None, envvars=None, srcfiles=None, required=False):
        self.name = name
        self.required=required
        self.help_text = help_text
        self.valtype = valtype
        self.default_value = default_value
        self.envvars = envvars or []
        self.srcfiles = srcfiles or []

    def load(self, firstval=False):
        """ Load from a bunch of places first. """
        # print("Loading default value for: ", self.name)
        values = []

        # First read env vars
        for envvar in self.envvars:
            val = os.environ.get(envvar)
            if val is not None:
                values.append(val)
                if firstval: return values

        # Then read files
        for srcfile in self.srcfiles:
            if os.path.exists(srcfile):
                contents = open(srcfile).read()
                values.append(contents)
                if firstval: return values

        # Finally add default value
        if self.default_value is not None:
            values.append(self.default_value)
        return values

class Command:
    """ Generic command interface. """
    def __call__(self, node, ctx: CommandContext):
        pass

class HttpCommand:
    def __call__(self, node, ctx: CommandContext):
        data = node.data
        path = data["path"]
        bodyparams = node.data.get("bodyparams", {})
        ast = node.data.get("ast", {})

        param_mappings = data["param_mappings"]
        if param_mappings:
            parts = path.split("/")
            if path[0] == "/":
                parts = parts[1:]
            for pp, val in param_mappings.items():
                parts[val] = ctx.cmd_stack[val].name
            path = "/".join(parts)

        method = data["verb"].lower()
        needs_body = method not in ("get", "delete")
        auth_token = ctx.get_flag_values("AuthToken")[0]
        apigw_host = ctx.get_flag_values("ApiGatewayHost")[0]
        dk_host = ctx.get_flag_values("ReqRouterHost")[0]
        headers = {
            "Authorization" : f"Bearer {auth_token}",
            "DagKnowsReqRouterHost": dk_host,
        }
        if apigw_host.endswith("/"): apigw_host = apigw_host[:-1]
        if path.startswith("/"): path = path[1:]
        url = f"{apigw_host}/{path}"

        payload = {}
        # Read payload from input file or json
        infile = ctx.get_flag_values("file")
        if infile:
            payload = json.loads(open(infile).read())

        injson = ctx.get_flag_values("json")
        if injson:
            payload = json.loads(injson[0])

        read_stdin = ctx.get_flag_values("stdin")
        if read_stdin:
            lines = list(itertools.takewhile(lambda x: True, sys.stdin))
            payload = json.loads("\n".join(lines))

        set_trace()
        if needs_body and not payload:
            schemaref = bodyparams.get("body", {}).get("schema", {}).get("$ref", "")
            schemaname = schemaref.split("/")
            if schemaname:
                defs = ast.specification["definitions"]
                print(f"API Request: {method} {url} needs a body of type: ", defs[schemaname[-1]].get("title", schemaname))
                return -1
            else:
                print(f"API Request: {method} {url} needs a body")

        set_trace()
        methfunc = getattr(requests, method)
        if ctx.get_flag_values("log_request"):
            print(f"API Request: {method} {url} ", headers, payload)
        if needs_body:
            resp = methfunc(url, json=payload, headers=headers)
        else:
            resp = methfunc(url, params=payload, headers=headers)
        out = resp.json()
        if ctx.get_flag_values("log_response"):
            print("API Response: ")
            pprint(out)
        return out

class CLI(object):
    """ Represents the CLI object managing a trie of commands as well as an activation context on each run. """
    def __init__(self, root):
        self.root = root

    def get_runner(self, runner_name):
        return HttpCommand()

    def add_flag(self, flag):
        self.global_flag_defs.append(flag)

    def show_usage(self, ctx: CommandContext):
        """ Show help usage at the given context point. """
        print(f"Usage: {ctx.cmd_so_far} OPTIONS ARGS...")
        print("Available Commands: ")
        for key in ctx.last_node.children.keys():
            print(f"    - {key}")
        if ctx.last_node.param_trie:
            print("    - <PARAM>")

    def show_help(self):
        pass

    def invalid_command(self, ctx: CommandContext):
        raise Exception("Invalid/Incomplete command: " + ctx.cmd_so_far)

    def no_method_found(self, ctx: CommandContext, currarg: str=None):
        node = ctx.last_node
        print("Available commands: ", list(node.children.keys()))
        raise Exception("Incomplete command: " + ctx.cmd_so_far)

    def check_flag(self, val):
        isflag = val.startswith("-")
        if isflag:
            while val[0] == "-":
                val = val[1:]
        return isflag, val, None

    def read_flag_value(self, argvals: deque, flagkey, flagdef) -> str:
        if not argvals: return None

        if argvals[0].startswith("-"):
            # have a flag so stop
            return None

        # TODO - convert to right type as well as see if we can do tuples here
        return argvals.popleft()

    def __call__(self, data: any=None, args=None):
        ctx = CommandContext(self, data)
        if args is None:
            import sys
            self.cmd_name = sys
            args = sys.argv[1:]
            ctx.cmd_name = sys.argv[0]
        ctx.args = args

        # see where the real root is
        root = self.root
        while len(root.children) == 1:
            root = root.children[list(root.children.keys())[0]]

        allargs = deque(args)
        node = root
        ctx.cmd_stack.append(CommandActivation("", node))
        while allargs:
            currarg = allargs.popleft()
            # is curr a "flag"
            isflag, flagkey, flagdef = self.check_flag(currarg)

            if isflag:
                flagvalue = self.read_flag_value(allargs, flagkey, flagdef)
                # for now we only read one value for a flag
                # but our node can have a "flagdef" that may see how many
                # values can be part of this flag (eg tuples)
                ctx.add_flag_value(flagkey, flagvalue)
            else:
                # we have a subcommand  see if realroot has it
                if currarg in node.children:
                    node = node.children[currarg]
                    ctx.cmd_stack.append(CommandActivation(currarg, node))
                elif node.param_trie:
                    node = node.param_trie
                    ctx.cmd_stack.append(CommandActivation(currarg, node))
                else:
                    self.no_method_found(ctx, currarg)

        lastnode = ctx.last_node
        if ctx.get_flag_values("help"):
            self.show_usage(ctx)
        else:
            runner = lastnode.data.get("runner", None)
            if runner and type(runner) is str:
                runner = self.get_runner(runner)

            if not runner:
                self.show_usage(ctx)
                self.invalid_command(ctx)
                return -1

            result = runner(lastnode, ctx)
            return 0# result
