import typer

def process(swagger_path_or_dict: Union[Dict, str]):
    leafs, ast = to_rich_trie(swagger_path_or_dict)
    root = leafs[0].root
    realroot = root
    while len(realroot.children) == 1:
        realroot = realroot.children[list(realroot.children.keys())[0]]
    rootapp = typer.Typer()
    for leaf in leafs:
        ensure_command_at_leaf(ast, leaf, realroot, rootapp)
    return app

def create_function(func_name, func_args, func_body, func_params=None):
    func_str = f"def {func_name}({func_args}): \n {func_body}"
    exec(func_str)
    new_func = locals()[func_name]
    if func_params is not None:
        for param, (default, annotation) in func_params.items():
            new_func.__annotations__[param] = annotation
            new_func.__defaults__ += (default,)
    return new_func

def ensure_app_at_node(node: TrieNode, realroot: TrieNode, rootapp: typer.Typer): 
    if "app" not in node.data:
        parentapp = rootapp
        if node.parent != None and node != realroot:    # we are at the root
            parentapp = ensure_app_at_node(node.parent, realroot, rootapp)
        node.data["app"] = currapp = typer.Typer()
        parentapp.add_typer(currapp, name=node.value)
    return node.data["app"]

def eval_type_of(field_path: List[str], bodyparams):
    return str, "str"

def make_request(ctx, path, method):
    # Construct the http request and call it here based on all args passed
    ast = ctx.obj["swaggerast"]
    set_trace()

def nested_schema_field_paths(ast, schemaref, childkey):
    modelname = schemaref.split("/")[-1]
    schema = ast.specification["definitions"][modelname]
    if "properties" in schema:
        props = schema["properties"]
        yield from nested_field_paths(ast, props, childkey)
    elif schema.get("type", None) == "object":
        yield childkey, object, "object", None, schema.get("description", "")
    else:
        set_trace()
        pass

def nested_field_paths(ast, obj, keysofar=""):
    for key, value in obj.items():
        if value.get("in", None) == "path": continue

        childkey = key
        if keysofar and value.get("in", None) != "body":
            childkey = keysofar + "." + childkey

        # Path params dont need to be passed in flags
        if "schema" in value:
            schemaref = value["schema"]["$ref"]
            yield from nested_schema_field_paths(ast, schemaref, childkey)
            # have a nested object
        elif "type" in value:
            if value["type"] == "string":
                yield childkey, str, "str", None, value.get("description", "")
            elif value["type"] == "array":
                yield childkey, List[str], "List[str]", [], value.get("description", "")
            else:
                set_trace()
        elif "$ref" in value:
            yield from nested_schema_field_paths(ast, value["$ref"], childkey)
        else:
            set_trace()
            print("No Type")

def ensure_command_at_leaf(ast, leaf: TrieNode, realroot: TrieNode, rootapp):
    if leaf.data.get("appcmd", None):
        set_trace()
        print("This is being called twice.  Is this right?")
    parent_app = ensure_app_at_node(leaf, realroot, rootapp)

    # use the leaf params etc to create our "request" caller
    bodyparams = leaf.data["bodyparams"]

    httpverb = leaf.data["verb"].upper()
    httppath = leaf.data["path"]

    func_name = leaf.path_to_ancestor(realroot, lambda a,b: a + "_" + b)
    func_args = "ctx: typer.Context"
    arg_names = ["ctx"]
    arg_types = [typer.Context]
    arg_defaults = []
    for argname in leaf.data["path_params"]:
        # add the type
        argname = argname.replace(".", "_")
        argtype, argtypestr = eval_type_of(argname, bodyparams)
        arg_names.append(argname)
        arg_types.append(argtype)
        # arg_defaults.append()
        func_args += f", {argname}: {argtypestr}"

    arg_names.append("file")
    arg_types.append(typer.FileText)
    arg_defaults.append(typer.Option(..., help="File containing the entire body of the request"))
    func_args += ", file: typer.FileText"

    arg_names.append("json")
    arg_types.append(str)
    arg_defaults.append(typer.Option(..., help="A JSON string containing the entire body of the request"))
    func_args += ", json: str"

    # Do the same for all nested field paths
    for field_path, fptype, fptypestr, fpdefault, fphelp  in nested_field_paths(ast, bodyparams):
        argname = field_path.replace(".", "_")
        arg_names.append(argname)
        arg_types.append(fptype)
        arg_defaults.append(typer.Option(fpdefault, field_path, help=fphelp))
        func_args += f", {argname}: {fptypestr}"

    pprinted = pprint(bodyparams)
    func_body = f"make_request(ctx, httppath, httpverb, {pprinted})"
    func_template = f"def {func_name}({func_args}): \n {func_body}"
    exec(func_template)
    new_func = locals()[func_name]
    new_func.__defaults__ = tuple(arg_defaults)
    # new_func.__annotations__[param] = annotation

    # now add file and json types

    # register it!
    leaf.data["appcmd"] = parent_app.command(leaf.value)(new_func)
    return leaf.data["appcmd"]
