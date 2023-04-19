import typer, yaml, json
from pprint import pprint
from ipdb import set_trace
from boltons.iterutils import remap
from rich import print

def present(ctx: typer.Context, results):
    results = remap(results, lambda p, k, v: v is not None)
    if ctx.obj.output_format == "json":
        print(json.dumps(results, indent=4))
    elif ctx.obj.output_format == "yaml":
        print(yaml.dump(results, indent=4, sort_keys=False))
    elif ctx.obj.output_format == "pprint":
        pprint(results)
    elif ctx.obj.output_format == "tree":
        # Then our results are actually a tree where each node has only 2 keys - a "title" and a "children"
        # we can render this in tree format with "|" etc
        if results:
            tree = {}
            if not ctx.obj.tree_transformer:
                pprint(results)
                set_trace()
                assert False, "'tree' output format needs a tree transformer to convert results into a tree structure where each node only has either 'title' or 'children'"
            else:
                tree = ctx.obj.tree_transformer(results)
                output = render(tree)
                lines = [(level * " ") + p + (" ") + title if p else title for (p,title,level) in output]
                print("\n".join(lines))
    else:
        # Apply a result type specific transformer here
        print("Invalid output format: ", ctx.obj.output_format)

def render(root, lines=None, level=0, indent=4):
    indentstr = " " * indent
    if lines is None: lines = []
    if root:
        prefix = ""
        if level > 0:
            prefix += (level - 1) * indentstr
            prefix += "  |" + (indent - 1) * "-"
        lines.append((prefix, root["title"], level))
        for child in root.get("children", []):
            lines = render(child, lines, level + 1, indent)
    return lines
