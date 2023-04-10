
import requests
from collections import deque
from ipdb import set_trace
from typing import List, Union, Dict
from swagger_parser import SwaggerParser
import json, os
from pprint import pprint
from dagcli.tries import TrieNode

def jp(obj):
    print(json.dumps(obj, indent=2))

def make_cli(swagger_path_or_dict: Union[Dict, str]):
    leafs = to_trie(swagger_path_or_dict)
    cli = CLI(leafs)
    return cli

def to_trie(swagger_path_or_dict: Union[Dict, str]):
    """ Processes the parsed swagger AST and builds a Trie of commands we will use to convert to Typer declarations. """
    if type(swagger_path_or_dict) is str:
        ast = SwaggerParser(swagger_path = swagger_path_or_dict)
    else:
        ast = SwaggerParser(swagger_dict = swagger_path_or_dict)

    def is_param(word): return word[0] == "{" and word[-1] == "}"

    root = TrieNode("")
    leafs = []
    for path, pathspec in ast.paths.items():
        parts = [x.strip() for x in path.split("/") if x.strip()]
        print("Processing: ", path, parts)

        # Start from the root and add parts of the path spec into the trie
        node=root

        # Treat parts based on whether it is a "plain" word or surrounded by "{}"
        # denoting a parameter (also affects how it sets req params)
        # Param names we are extracting out
        params = {}
        custaction = ""
        is_action = False
        num_path_parts = len(parts)
        for index,p in enumerate(parts):
            if is_param(p):
                node = node.add(p[1:-1].lower(), True)
                params[p[1:-1]] = index
            elif index < len(parts) - 1:
                node = node.add(p.lower())
            else:
                # Allow custom actions in the end only - respecting AIP dev
                # here we can have a hook to do custom names
                nodeparts = p.split(":")
                custaction = "_".join(nodeparts[1:])
                is_action = len(nodeparts) > 1
                for part2 in nodeparts:
                    node = node.add(part2.lower())

        # See if node ends with an action, ie: dags:batchCreate
        # here "batchCreate" is the action
        # now look at the "method" name
        for mindex, (method, methodinfo) in enumerate(pathspec.items()):
            # which "method" should we use?
            # use the get/post/patch etc to use as is
            methname = method
            has_method_suffix = True
            if is_action:
                # ie use the last part of the "a:b:c:d" as our method name
                # Only append the method if last part already exists
                methnode = node
                # add the method as a node only if we have "multiple" VERBs on the exact
                # same pathspec so if a/b:crates has GET and POST then we will do a 
                # a b crates get and
                # a b crates post
                if len(pathspec.keys()) > 1:
                    methnode = methnode.add(methnam)
                else:
                    has_method_suffix = False
                # if custaction in node.children: methnode = methnode.add(methname)
            else:
                methnode = node.add(methname)

            # We are a method node
            assert methnode.data.get("type", None) is None, "Type should *not* be set here?"
            methnode.data["ast"] = ast
            methnode.data["type"] = "method"
            methnode.terminal = True
            methnode.data["num_path_parts"] = num_path_parts
            methnode.data["has_method_suffix"] = has_method_suffix

            # The http VERB to be used for this method
            methnode.data["verb"] = method

            # Full path for this method as is
            methnode.data["path"] = path
            methnode.data["pathspec"] = pathspec 

            # Params extracted from the "path" - will be used to contruct
            # the path to hit our endpoint with
            methnode.data["path_param_indices"] = params

            # Body params can be sent as http body or as query parameters
            # based on whether the verb allows http body or not
            methnode.data["bodyparams"] = methodinfo["parameters"]

            methnode.data["cmd"] = HttpCommand(methnode)
            methnode.data["flagdefs"] = [
                FlagDef("json", help_text="JSON file containing the entire request body", valtype="json"),
                FlagDef("file", help_text="Input file containing a JSON of the entire request body", valtype="file"),
            ]
            leafs.append(methnode)
    return leafs

class CommandContext(object):
    def __init__(self, cli, data=None):
        # The CLI object on which we are operating
        self.cli = cli

        # All the cli parts that have come so far
        # eg in a cmd cat a b c d --a --b --c 2 e f
        # path parts would contain cat a b c d
        self.cmd_parts = []

        # Nodes that were visited along with their specific flags (so we can record node specific flags too)
        # as each part was encountered and we stepped into a child node.
        # [0] is always the realroot
        self.cmd_nodes = []

        # Again for above example, args would contain all args
        # if "b" was the leaf cmd part then our args would be "c" "d" "e" "f"
        self.args = []

        # Flags are unordered and here would contain a={default_val} b={default_val c=2
        # default value would be chosen based on the type of value found in the swagger spec
        self.flags = {}

        # custom data passed by the user
        self.data = data or {}

    def get_flag_values(self, flag):
        """ Gets the value of a flag by either getting its explicitly set value
        or the default value from where ever it is specified (eg file, env var etc).
        """
        if flag in self.flags:
            return self.flags[flag], True

        for node,_ in self.cmd_nodes:
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
        return self.cmd_nodes[-1][0]

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
        print("Loading default value for: ", self.name)
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
    def __init__(self, node):
        self.node = node

    def __call__(self, ctx: CommandContext):
        pass

class HttpCommand(Command):
    def __call__(self, ctx: CommandContext):
        node = self.node
        data = node.data
        path = data["path"]
        path_param_indices = data["path_param_indices"]
        if data["path_param_indices"]:
            parts = path.split("/")
            if path[0] == "/":
                parts = parts[1:]
            for pp, val in path_param_indices.items():
                parts[val] = ctx.cmd_parts[val]
            path = "/".join(parts)

        method = data["verb"].lower()
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
        methfunc = getattr(requests, method)
        if method == "get" or method == "delete":
            resp = methfunc(url, params=payload, headers=headers)
        else:
            resp = methfunc(url, json=payload, headers=headers)
        return resp.json()

class CLI(object):
    """ Represents the CLI object that is based off a swagger spec. """
    def __init__(self, leafs):
        self.leafs = leafs
        self.root = self.leafs[0].root

        # Flag definitions application for all commands
        self.global_flag_defs = [
            FlagDef("AuthToken",
                    help_text="Auth token for accessing the API gateway",
                    valtype=str,
                    required=True,
                    envvars=["DagKnowsAuthToken"]),
            FlagDef("ReqRouterHost",
                    help_text="Request router host",
                    valtype=str,
                    default_value="https://demo.dagknows.com:8443",
                    envvars=["DagKnowsReqRouterHost"]),
            FlagDef("ApiGatewayHost",
                    help_text="API Gatway host fronting the new API",
                    valtype=str,
                    default_value="http://localhost:8080/api",
                    envvars=["DagKnowsApiGatewayHost"]),
        ]

    def add_flag(self, flag):
        self.global_flag_defs.append(flag)

    def show_usage(self, ctx: CommandContext):
        """ Show help usage at the given context point. """
        print(f"Usage: {' '.join(ctx.cmd_parts)} OPTIONS ARGS...")
        print("Available Commands: ")
        for key in ctx.last_node.children.keys():
            print(key)

    def show_help(self):
        pass

    def invalid_command(self, ctx: CommandContext):
        raise Exception("Invalid/Incomplete command: " + " ".join(ctx.cmd_parts))

    def no_method_found(self, ctx: CommandContext, currarg: str=None):
        node = ctx.cmd_nodes[-1]
        print("Available commands: ", list(node.children.keys()))
        raise Exception("Incomplete command: " + " ".join(ctx.cmd_parts))

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
        ctx.cmd_parts.append("")
        ctx.cmd_nodes.append((node, {}))
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
                ctx.cmd_parts.append(currarg)
                # we have a subcommand  see if realroot has it
                if currarg in node.children:
                    node = node.children[currarg]
                    ctx.cmd_nodes.append((node, {}))
                elif node.param_trie:
                    node = node.param_trie
                    ctx.args.append(currarg)
                    ctx.cmd_nodes.append((node, {}))
                else:
                    self.no_method_found(ctx, currarg)

        lastnode = ctx.last_node
        if ctx.get_flag_values("help"):
            self.show_usage(ctx)
        else:
            cmd = lastnode.data.get("cmd", None)
            if not cmd:
                self.show_usage(ctx)
                self.invalid_command(ctx)
            else:
                return cmd(ctx)
