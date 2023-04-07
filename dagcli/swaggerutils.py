
from ipdb import set_trace
from typing import List, Union, Dict
from swagger_parser import SwaggerParser
import typer
import json
from pprint import pprint
from dagcli.tries import TrieNode

def jp(obj):
    print(json.dumps(obj, indent=2))

def is_param(word):
    return word[0] == "{" and word[-1] == "}"

def to_trie(swagger_path_or_dict: Union[Dict, str]):
    """ Processes the parsed swagger AST and builds a Trie of commands we will use to convert to Typer declarations. """
    if type(swagger_path_or_dict) is str:
        ast = SwaggerParser(swagger_path = swagger_path_or_dict)
    else:
        ast = SwaggerParser(swagger_dict = swagger_path_or_dict)

    root = TrieNode("")
    leafs = []
    for path, pathspec in ast.paths.items():
        parts = [x.strip() for x in path.split("/") if x.strip()]
        print("Processing: ", path, parts)

        # Treat parts based on whether it is a "plain" word or surrounded by "{}"
        # denoting a parameter (also affects how it sets req params)
        node = root
        # Param names we are extracting out
        params = []
        for p in parts:
            if is_param(p):
                params.append(p[1:-1])
                # Mark this node as a required parameter
                # node.data["type"] = "reqparam"
                # node.data["param_name"] = p[1:-1]
            else:
                node = node.add(p)
                node.data["type"] = "static"

        # Now all the "prefix parameters" have been matched, 

        # See if node ends with an action, ie: dags:batchCreate
        # here "batchCreate" is the action
        nodeparts = node.value.split(":")
        custaction = "_".join(nodeparts[1:])
        is_action = len(nodeparts) > 1

        # now look at the "method" name
        for method, methodinfo in pathspec.items():
            # which "method" should we use?
            # use the get/post/patch etc to use as is
            methname = method

            if is_action:
                methname = custaction
                if custaction in node.children:
                    # we already have a custom action so prefix with method
                    methname = method + "_" + methname

            methnode = node.add(methname)
            methnode.terminal = True

            # We are a method node
            methnode.data["type"] = "method"

            # The http VERB to be used for this method
            methnode.data["verb"] = method

            # Full path for this method as is
            methnode.data["path"] = path

            # Params extracted from the "path" - will be used to contruct
            # the path to hit our endpoint with
            methnode.data["path_params"] = params

            # Body params can be sent as http body or as query parameters
            # based on whether the verb allows http body or not
            methnode.data["bodyparams"] = methodinfo["parameters"]
            leafs.append(methnode)
    return leafs, ast

def to_typer(root: TrieNode, ast):
    # go to the first root that has > 1 children
    realroot = root
    while len(realroot.children) == 1:
        realroot = realroot.children[list(realroot.children.keys())[0]]
    set_trace(context=20)
    pass

def process(swagger_path_or_dict: Union[Dict, str]):
    leafs, ast = to_trie(swagger_path_or_dict)
    root = leafs[0].root
    to_typer(root, ast)
