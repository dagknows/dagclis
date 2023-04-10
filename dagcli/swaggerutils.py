
from ipdb import set_trace
from typing import List, Union, Dict
from swagger_parser import SwaggerParser
import json, os
from pprint import pprint
from dagcli.tries import TrieNode
from dagcli.cmd import CLI, HttpCommand, FlagDef

def jp(obj):
    print(json.dumps(obj, indent=2))

def default_command_strategy(ast, root, path, pathspec, method, methodinfo):
    """ Command strategies are used to convert a request path spec into a command node. """
    parts = [x.strip() for x in path.split("/") if x.strip()]
    # print("Processing: ", parts)
    # Start from the root and add parts of the path spec into the trie
    node = root

    # Treat parts based on whether it is a "plain" word or surrounded by "{}"
    # denoting a parameter (also affects how it sets req params)
    # Param names we are extracting out
    def is_param(word): return word[0] == "{" and word[-1] == "}"
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
    return methnode

def to_trie(swagger_path_or_dict: Union[Dict, str]):
    """ Processes the parsed swagger AST and builds a Trie of commands we will use to convert to Typer declarations. """
    if type(swagger_path_or_dict) is str:
        ast = SwaggerParser(swagger_path = swagger_path_or_dict)
    else:
        ast = SwaggerParser(swagger_dict = swagger_path_or_dict)

    root = TrieNode("")
    leafs = []
    for path, pathspec in ast.paths.items():
        for mindex, (method, methodinfo) in enumerate(pathspec.items()):
            leaf_meth_node = default_command_strategy(ast, root, path, pathspec, method, methodinfo)
            leafs.append(leaf_meth_node)
    return root, leafs

def make_cli(swagger_path_or_dict: Union[Dict, str]):
    root, leafs = to_trie(swagger_path_or_dict)
    cli = CLI(root)
    return cli
