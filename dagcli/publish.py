
from dagcli.client import newapi
import subprocess
import typer
import os, sys
from typing import List
from pprint import pprint
import requests
import marko

from pkg_resources import resource_string
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
disable_warnings(InsecureRequestWarning)

app = typer.Typer()

from ipdb import set_trace as debug

def render_node(node):
    nt = node.get_type().lower()
    if nt == "paragraph":
        return "".join(map(render_node, node.children))
    elif nt == "rawtext":
        return node.children
    elif nt == "codespan":
        return "`" + node.children + "`"
    elif nt == "blankline":
        return "\n"
    elif nt == "list":
        return "\n".join([node.bullet + render_node(ch) for ch in node.children])
    elif nt == "linebreak":
        return "" if node.soft else "\n"
    elif nt == "listitem":
        return "\n".join(map(render_node, node.children))
    elif nt == "link":
        return f"[{node.children[0].children}]"
    elif nt == "emphasis":
        border = "*" * node.priority
        return f"{border}{node.children[0].children}{border}"
    elif nt == "thematicbreak":
        return ""
    else:
        debug(context=21)
        assert False

class TaskNode:
    def __init__(self, parent=None):
        self.level = 0
        self.parent = parent
        if parent:
            self.level = parent.level + 1
        self.mdnode = None
        self.node_type = ""
        self.content = ""
        self.children = []

    @property
    def last_child(self):
        if self.children: return self.children[-1]
        return None

    @property
    def root(self):
        if self.parent is None: return self
        return self.parent.root

    def print(self):
        print(f"{' ' * self.level}: {self.node_type}: {self.content}")
        for ch in self.children: ch.print()

    def printed(self):
        out = {
            "type": self.node_type,
            "level": self.level,
            "content": self.content,
        }
        if self.children:
            out["children"]= [ch.printed() for ch in self.children]
        return out

    def process_mdnode(self, node):
        nt = node.get_type().lower()
        print("Processing node: ", node)
        # debug(context=21)
        if nt  in ("paragraph", "list", "listitem"):
            # Start a new node - but dont change "level"
            if node.children:
                """
                t = TaskNode(self)
                t.level = self.level + 1
                t.node_type = nt
                t.content = ""
                self.children.append(t)
                """
                for ch in node.children:
                    self.process_mdnode(ch)
        elif nt in ("blankline", "linebreak", "codespan", "thematicbreak", "rawtext", "link", "emphasis"):
            # Always ensure a parent exists
            # We can turn this off with a flag?
            # Append as is
            if self.last_child and self.last_child.node_type == "text":
                self.last_child.content += render_node(node)
            elif nt != "blankline":
                t = TaskNode(self)
                t.node_type = "text"
                t.content = render_node(node)
                self.children.append(t)
        elif nt in ("fencedcode", "codeblock"):
            if node.children and node.children[0].children:
                code = node.children[0].children
                if self.last_child and self.last_child.node_type == "code":
                    self.last_child.content += "\n" + code
                else:
                    t = TaskNode(self)
                    t.node_type = "code"
                    t.content = code
                    self.children.append(t)
        elif nt in ("heading", "setextheading"):
            if node.children and node.children[0].children:
                if type(node.children[0].children) is not str:
                    debug(context=21)
                    assert False
                else:
                    # We have a proper title
                    title = node.children[0].children
                    # Make sure we go up/down the levels
                    pnode = self
                    while pnode and node.level <= pnode.level:
                        pnode = pnode.parent

                    if not pnode:
                        pnode = self.root

                    t = TaskNode(pnode)
                    t.node_type = "heading"
                    t.content = title
                    t.level = node.level
                    pnode.children.append(t)
                    return t
        else:
            import ipdb ; ipdb.set_trace()
            assert False, ("Invalid type: ", node)

@app.command()
def mdfile(ctx: typer.Context,
           md_file: typer.FileText = typer.Argument(..., help = "Markdown to publish as a task"),
           taskid: str = typer.Argument(..., help = "Task to replace/update or create as.  Note that if you do not have update the taskid or its children, this will fail.")):
    mdcontents = md_file.read()
    mdast = marko.parse(mdcontents)

    currnode = None
    for node in mdast.children:
        nt = node.get_type().lower()
        if not currnode:
            currnode = TaskNode()
            currnode.node_type = "heading"
            currnode.level = 1
            currnode.content = "Unnamed Node" # or get it from flag
            if nt == "heading" and node.level == 1:
                # We can create a root node with this
                currnode.content = node.children[0].children
                continue
        currnode = currnode.process_mdnode(node) or currnode

    # Step 1 - Delete this taskid and all its children recursively
    newapi(ctx.obj, f"/tasks/{taskid}?recurse=true", None, "DELETE")

    root = currnode.root
    roottask = node2task(ctx, root, taskid)
    root.print()

# Step 2 - Create this now
def node2task(ctx, node, taskid=None):
    print("Creating Task for Node: ", node.node_type, node.content)
    assert node.node_type == "heading", "Node type here *must* be a heading"
    # debug()
    task_params = {"title": node.content}
    if taskid: task_params["id"] = taskid
    nodetask = newapi(ctx.obj, "/tasks/", { "task": task_params }, "POST")["task"]
    taskid = nodetask["id"]

    childids = []
    i = 0
    while i < len(node.children):
        chnode = node.children[i]
        task_params = {}
        if chnode.node_type == "text":
            # good we can get this and the code after this (if it exists)
            if len(chnode.content) < 80:
                task_params["title"] = chnode.content
            else:
                task_params["title"] = f"Step {len(childids) + 1}"
                task_params["description"] = chnode.content
            if i + 1 < len(node.children) and node.children[i + 1].node_type == "code":
                task_params["commands"] = [node.children[i + 1].content]
                task_params["script_type"] = "command"
                i += 1
            chtask = newapi(ctx.obj, "/tasks/", { "task": task_params }, "POST")
            childids.append(chtask["task"]["id"])
        elif chnode.node_type == "code":
            # This was *not* preceeded by a text so create a "step" node
            task_params["title"] = "Run the following: "
            task_params["commands"] = [chnode.content]
            task_params["script_type"] = "command"
            chtask = newapi(ctx.obj, "/tasks/", { "task": task_params }, "POST")
            childids.append(chtask["task"]["id"])
        else: # heading
            chtask = node2task(ctx, chnode)
            childids.append(chtask["id"])
        i += 1

    # Now save subtaskids
    if childids:
        nodetask["sub_tasks"] = [{"taskid": id} for id in childids]
        resp = newapi(ctx.obj, f"/tasks/{taskid}", {
            "task": nodetask,
            "update_mask": ["sub_tasks"]
        }, "PATCH")
    return nodetask

"""
[<marko.block.Paragraph object at 0x1027da810>, <marko.block.BlankLine object at 0x1027dae90>, <marko.block.Heading object at 0x1027db750>, <marko.block.BlankLine object at 0x1027db310>, <marko.block.Paragraph object at 0x1027db890>, <marko.block.BlankLine object at 0x1027db650>, <marko.block.Heading object at 0x1027db4d0>, <marko.block.BlankLine object at 0x1027dbad0>, <marko.block.Heading object at 0x1027dba10>, <marko.block.BlankLine object at 0x1027db950>, <marko.block.Heading object at 0x1027dbc50>, <marko.block.BlankLine object at 0x1027dbe50>, <marko.block.FencedCode object at 0x1027db510>, <marko.block.BlankLine object at 0x1027db2d0>, <marko.block.Heading object at 0x1027db810>, <marko.block.BlankLine object at 0x1027db550>, <marko.block.Paragraph object at 0x1027db710>, <marko.block.BlankLine object at 0x1027db5d0>, <marko.block.FencedCode object at 0x1027e9090>, <marko.block.BlankLine object at 0x1027e8e50>, <marko.block.Heading object at 0x1027e9050>, <marko.block.BlankLine object at 0x1027e8f90>, <marko.block.FencedCode object at 0x1027e8410>, <marko.block.BlankLine object at 0x1027e9350>, <marko.block.Paragraph object at 0x1027e9410>, <marko.block.BlankLine object at 0x1027e9490>, <marko.block.Paragraph object at 0x1027e9550>, <marko.block.BlankLine object at 0x1027e9510>, <marko.block.FencedCode object at 0x1027e9750>, <marko.block.BlankLine object at 0x1027e9910>, <marko.block.Paragraph object at 0x1027ea790>, <marko.block.BlankLine object at 0x1027ea890>, <marko.block.Heading object at 0x1027ea710>, <marko.block.BlankLine object at 0x1027ea950>, <marko.block.Paragraph object at 0x1027eaa50>, <marko.block.BlankLine object at 0x1027eaa10>, <marko.block.FencedCode object at 0x1027ea690>, <marko.block.BlankLine object at 0x1027ea810>, <marko.block.Paragraph object at 0x1027ea7d0>, <marko.block.BlankLine object at 0x1027eab50>, <marko.block.FencedCode object at 0x1027eabd0>, <marko.block.BlankLine object at 0x1027eacd0>, <marko.block.List object at 0x1027ead50>, <marko.block.BlankLine object at 0x101b0c1d0>, <marko.block.Paragraph object at 0x1027eadd0>, <marko.block.BlankLine object at 0x1027eaf90>, <marko.block.List object at 0x1027eb3d0>, <marko.block.BlankLine object at 0x1027eb190>, <marko.block.Paragraph object at 0x1027eb2d0>, <marko.block.BlankLine object at 0x1027eb450>, <marko.block.List object at 0x1027eb310>, <marko.block.BlankLine object at 0x1027eb6d0>, <marko.block.FencedCode object at 0x1027eb810>, <marko.block.BlankLine object at 0x1027eba90>]
"""
