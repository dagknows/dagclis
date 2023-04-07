
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

def swaggertotrie(swagger_path_or_dict: Union[Dict, str]):
    if type(swagger_path_or_dict) is str:
        parser = SwaggerParser(swagger_path = swagger_path_or_dict)
    else:
        parser = SwaggerParser(swagger_dict = swagger_path_or_dict)

    root = TrieNode("")
    for path, pathspec in parser.paths.items():
        parts = [x.strip() for x in path.split("/") if x.strip()]
        print("Processing: ", path, parts)

        # Treat parts based on whether it is a "plain" word or surrounded by "{}"
        # denoting a parameter (also affects how it sets req params)
        node = root
        for p in parts:
            node = node.add(p)
            node.data["type"] = "static"
            if is_param(p):
                # Mark this node as a required parameter
                node.data["type"] = "reqparam"
                node.data["param_name"] = p[1:-1]

        # Now all the "prefix parameters" have been matched, 

        # now look at the "method" name
        for method, methodinfo in pathspec.items():
            methnode = node.add(method)
            methnode.data["type"] = "method"
            methnode.data["paraminfo"] = methodinfo["parameters"]

            # Here we can have "flags" if this request has a body object (method name doesnt matter).
            # If our body is say {a: A, b: B, c: C} then we can have 3 flags
            # --a, --b and --c
            # and we could use them as: --a=3, --a=$ENV_VAR, --b=file://contents_of_file or --c="string"
            # In the case of "c" we will treat the param type of c be a string or a json string depending on the
            # type of param in the actual spec!
            #
            # Here is also a good opportunity to let these have "default" values
            # We could probably do this via callbacks into the convert method
    return root

def trietotyper(root: TrieNode):
    set_trace(context=20)
    pass
