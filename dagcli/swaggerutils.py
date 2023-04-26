
from typing import List, Union, Dict
from swagger_parser import SwaggerParser
import json, os
from pprint import pprint
from dagcli.tries import TrieNode
from dagcli.cmd import CLI, HttpCommand, FlagDef

def jp(obj):
    print(json.dumps(obj, indent=2))

def make_cli(swagger_path_or_dict: Union[Dict, str]):
    root, leafs = to_trie(swagger_path_or_dict)
    cli = CLI(root)
    return cli

def to_trie(swagger_path_or_dict: Union[Dict, str]):
    """ Processes the parsed swagger AST and builds a Trie of commands we will use to convert to Typer declarations. """
    import warnings
    from swagger_spec_validator.common import SwaggerValidationWarning
    warnings.simplefilter("ignore", SwaggerValidationWarning)
    if type(swagger_path_or_dict) is str:
        ast = SwaggerParser(swagger_path = swagger_path_or_dict)
    else:
        ast = SwaggerParser(swagger_dict = swagger_path_or_dict)

    root = TrieNode("")
    leafs = []
    for path, pathspec in ast.paths.items():
        for mindex, (method, methodinfo) in enumerate(pathspec.items()):
            leaf_meth_node = default_command_strategy(ast, root, path, pathspec, method)
            leafs.append(leaf_meth_node)
    return root, leafs

def path_to_trie_path(path, pathspec, method):
    parts = [x.strip() for x in path.split("/") if x.strip()]
    custaction = ""
    is_action = False
    trieparts = []
    param_mappings = {}

    # Treat parts based on whether it is a "plain" word or surrounded by "{}"
    # denoting a parameter (also affects how it sets req params)
    # Param names we are extracting out
    def is_param(word): return word[0] == "{" and word[-1] == "}"
    for index,p in enumerate(parts):
        if is_param(p):
            trieparts.append((p[1:-1], True))
            param_mappings[p[1:-1]] = index
        elif index < len(parts) - 1:
            trieparts.append((p.lower(), False))
        else:
            # Allow custom actions in the end only - respecting AIP dev
            # here we can have a hook to do custom names
            subparts = p.split(":")
            custaction = "_".join(subparts[1:])
            is_action = len(subparts) > 1
            for part2 in subparts:
                trieparts.append((part2.lower(), False))

    # See if node ends with an action, ie: dags:batchCreate
    # here "batchCreate" is the action
    # now look at the "method" name

    # which "method" should we use?
    # use the get/post/patch etc to use as is
    methname = method
    method_name_used = True
    if is_action:
        # ie use the last part of the "a:b:c:d" as our method name
        # Only append the method if last part already exists
        # add the method as a node only if we have "multiple" VERBs on the exact
        # same pathspec so if a/b:crates has GET and POST then we will do a 
        # a b crates get and
        # a b crates post
        if len(pathspec.keys()) > 1:
            trieparts.append((methname, False))
        else:
            method_name_used = False
    else:
        trieparts.append((methname, False))
    return trieparts, method_name_used, param_mappings

def default_command_strategy(ast, root, path, pathspec, method):
    """ Command strategies are used to convert a request path spec into a command node. """
    trieparts, method_name_used, param_mappings = path_to_trie_path(path, pathspec, method)
    # print("Processing: ", parts)
    # Start from the root and add parts of the path spec into the trie
    methnode = root
    for part, as_param in trieparts:
        methnode = methnode.add(part, as_param)
    return populate_method_data(methnode, method, path, pathspec, ast, param_mappings)

def populate_method_data(methnode, method, path, pathspec, ast, param_mappings, runner="HttpCommand"):
    # Given a method node already created at a certain trie path, 
    # populates its data with the path/method parameters

    if methnode.data.get("type"):
        set_trace()
        assert False, "Type should *not* be set here?"
    methnode.data["ast"] = ast
    methnode.data["type"] = "method"
    methnode.terminal = True

    # The http VERB to be used for this method
    methnode.data["verb"] = method

    # Full path for this method as is
    methnode.data["path"] = path
    methnode.data["pathspec"] = pathspec 

    # Params extracted from the "path" - will be used to contruct
    # the path to hit our endpoint with
    methnode.data["param_mappings"] = param_mappings

    # Body params can be sent as http body or as query parameters
    # based on whether the verb allows http body or not
    methodinfo = pathspec[method]
    methnode.data["bodyparams"] = methodinfo["parameters"]
    methnode.data["runner"] = runner
    return methnode
