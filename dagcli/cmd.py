
import sys
import itertools
from collections import deque
import requests
from typing import List, Union, Dict
import json, os

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

        # All flags applied as part of this activation
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
        # When a flag is encountered we keep track of all its values as well as "which" node
        # in the cmd line (ie which part of the full cli) the flag appeared in
        self.flag_values = {}

        # custom data passed by the user
        self.data = data or {}

    def flag_was_set(self, flagname: str) -> bool:
        vals = self.get_flag_values(flagname)
        return True if vals else False

    @property
    def curr_stack_index(self):
        return len(self.cmd_stack)

    @property
    def cmd_so_far(self):
        return " ".join(c.name for c in self.cmd_stack)

    def add_flag_value(self, flagname, value):
        """ Adds a value for a flag.  No validation is done to see if it is valid or not.
        Here the context also evaluates which node/stack index the flag should be
        associated with."""
        flagdef = self.cli.get_flag_def(flagname)
        if flagname not in self.flag_values:
            self.flag_values[flagname] = FlagVals(flagname, flagdef)
        flag = self.flag_values[flagname]
        flag.add(self.curr_stack_index, value)
        return flag

    def get_flag_value(self, flagname, try_external=False, try_default=False):
        """ Gets the first value of a flag.  This also has an option to fall back to external values or even defaults."""
        flagdef = self.cli.get_flag_def(flagname)
        if flagname in self.flag_values:
            flagvals = self.flag_values[flagname]
            if flagvals.values:
                return flagvals.values[0][1]

        if try_external:
            externs = flagdef.external_values()
            if externs:
                return externs[0]

        if try_default:
            if flagdef.default_values:
                return flagdef.default_values[0]

        return None

    def get_flag_values(self, flagname):
        """ Gets the value of a flag that was explicitly set.  """
        flagdef = self.cli.get_flag_def(flagname)
        if flagname in self.flag_values:
            flagvals = self.flag_values[flagname]
            # See if an explicit value was provided, then use it
            return flagvals.values
        return []

    @property
    def last_node(self):
        return self.cmd_stack[-1].node

class FlagVals:
    def __init__(self, name, flagdef=None):
        self.name = name
        self.flagdef = flagdef
        # This is a list of node + val_list pairs
        # So if a flag appears so:
        # a b --val=1 --val 2 c d --val=4
        # our values would be:
        # [
        #   (1, "1")
        #   (1, "2")
        #   (3, "4")
        # ]
        # Here 1 => index of subcommand "b" and 3 => index of subcommand "d"
        self.values = []

    def add(self, cmdindex, value):
        """ Adds a new occurence of a flag value in the context. """
        self.values.append((cmdindex, value))
        self.values.sort()

    @property
    def has_value(self):
        return len(self.values) > 0

class FlagDef:
    def __init__(self, name, help_text="", valtype=str, default_value=None, envvars=None, srcfiles=None, required=False, handler=None, val_on_missing=None):
        self.name = name
        self.required=required
        self.help_text = help_text
        self.valtype = valtype
        self.default_value = default_value
        self.envvars = envvars or []
        self.srcfiles = srcfiles or []
        self.val_on_missing = val_on_missing
        self.handler = handler

    def external_values(self, firstval=False):
        """ Gets 'external' values from non command line locations (eg envvars, config files etc). """
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

        # Dont return default values
        return values

    @property
    def default_values(self):
        values = self.default_value
        if callable(values):
            values = values()
        if not values:
            return []
        if type(values) is list:
            return values
        return [values]

    def apply(self, ctx: CommandContext, values: List["FlagVals"]):
        """ Applies the flag values to a context using our handlers if one exists. """
        if not handler: return

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
        headers = ctx.data["http"]["headers"]

        apigw_host = ctx.get_flag_value("ApiGatewayHost", True, True)
        if apigw_host.endswith("/"): apigw_host = apigw_host[:-1]
        if path.startswith("/"): path = path[1:]
        url = f"{apigw_host}/{path}"

        payload = {}
        # Read payload from input file or json
        infile = ctx.get_flag_value("file")
        if infile:
            payload = json.loads(open(infile).read())

        injson = ctx.get_flag_value("json")
        if injson:
            payload = json.loads(injson)

        read_stdin = ctx.get_flag_value("stdin")
        if read_stdin:
            lines = list(itertools.takewhile(lambda x: True, sys.stdin))
            payload = json.loads("\n".join(lines))

        if needs_body and not payload:
            schemaref = bodyparams.get("body", {}).get("schema", {}).get("$ref", "")
            schemaname = schemaref.split("/")
            if schemaname:
                defs = ast.specification["definitions"]
                print(f"API Request: {method} {url} needs a body of type: ", defs[schemaname[-1]].get("title", schemaname))
                return -1
            else:
                print(f"API Request: {method} {url} needs a body")

        methfunc = getattr(requests, method)
        if ctx.get_flag_value("log_request", False, True):
            print(f"API Request: {method} {url} ", headers, payload)
        if needs_body:
            resp = methfunc(url, json=payload, headers=headers)
        else:
            resp = methfunc(url, params=payload, headers=headers)
        out = resp.json()
        if ctx.get_flag_value("log_response", False, True):
            print("API Response: ")
            from pprint import pprint
            pprint(out)
        return out

class CLI(object):
    """ Represents the CLI object managing a trie of commands as well as an activation context on each run. """
    def __init__(self, root):
        self.root = root
        self.global_flag_defs = []

    def get_runner(self, runner_name):
        # TODO - Replace with a runner
        return HttpCommand()

    def get_flag_def(self, flagname: str) -> FlagDef:
        for fd in self.global_flag_defs:
            if fd.name == flagname:
                return fd
        return None

    def add_flags(self, *flagdefs: List[FlagDef]):
        self.global_flag_defs.extend(flagdefs)

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
        if argvals:
            if not argvals[0].startswith("-"):
                # TODO - convert to right type as well as see if we can
                # do tuples here
                return argvals.popleft()

        # No value was speified - instead of None, use a val_on_missint
        flagdef = self.get_flag_def(flagkey)
        if not flagdef:
            return True
        return flagdef.val_on_missing or ""

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

        if ctx.flag_was_set("help"):
            self.show_usage(ctx)
            return 0

        # We first go through the context and let all flags do their thing to the ctx
        lastnode = ctx.last_node
        self.apply_context_flags(ctx)
        runner = lastnode.data.get("runner", None)
        if runner and type(runner) is str:
            runner = self.get_runner(runner)

        if not runner:
            self.show_usage(ctx)
            self.invalid_command(ctx)
            return -1

        result = runner(lastnode, ctx)
        return 0# result

    def apply_context_flags(self, ctx: CommandContext):
        # First go through all registerd flags and for those that are required
        # and have default or extenral values - and apply them - IF they have
        # not been specified
        for flagdef in self.global_flag_defs:
            if flagdef.handler:
                vals = ctx.get_flag_values(flagdef.name)
                if not vals:
                    externs = flagdef.external_values()
                    if externs:
                        flagdef.handler(ctx, flagdef, (-1, externs[0]))
                    elif flagdef.default_values:
                        flagdef.handler(ctx, flagdef, (-1, flagdef.default_values[0]))

        # Step 2 - Go through flags that were actually specified and apply them
        # In order of their set
        for flagname, flagvals in ctx.flag_values.items():
            flagdef = flagvals.flagdef
            if flagdef and flagdef.handler and flagvals.has_value:
                flagdef.handler(ctx, flagdef, *flagvals.values)
