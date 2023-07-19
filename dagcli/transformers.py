import json
from collections import defaultdict
from rich.tree import Tree

problem_color = "red"
not_problem_color = "green"
normal_color = "#white"

def node_info_transformer(dagnode):
    node = dagnode["node"]
    edges = (dagnode.get("outEdges", {}) or {}).get("edges", []) or []
    nodeid = node['id']
    title = f"[bold]{node['title']}[/bold]  -  ({nodeid})"
    root = Tree(title)
    for edge in edges:
        root.add(edge["destNode"])
    return root

def node_list_transformer(nodes):
    root = Tree("nodes")
    for n in nodes:
        ninfo = node_info_transformer(n)
        root.add(ninfo)
    return root

def task_list_transformer(tasks):
    root = Tree("tasks")
    for d in tasks:
        dinfo = rich_task_info_with_exec(d)
        root.add(dinfo)
    return root

def dag_list_transformer(dags):
    root = Tree("dags")
    for d in dags:
        dinfo = rich_dag_info_with_exec(d)
        root.add(dinfo)
    return root
    # return {"title": "dags", "children": map(dag_info_with_exec, dags)}

"""
dagcli nodes get R7YGKMUGWMDlP1HkWg68H9m8m8aejTy6 --dag-id Mu3CFBZvlwNjYoZVA13SC8Gpm4D16Fdi
"""

def rich_dag_info_with_exec(dag, problem_info=None):
    problem_info = problem_info or defaultdict(str)
    nodesbyid = {}
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", {})
    incount = defaultdict(int)
    for node in nodes:
        nodeid = node["id"]
        title = f"[bold]{node['title']}[/bold]  -  ({nodeid})"
        if problem_info[nodeid] == "yes":
            title = f"[{problem_color}][Problem]  -  {title}"
        elif problem_info[nodeid] == "no":
            title = f"[{not_problem_color}]{title}"
        else:
            title = f"[{normal_color}]{title}"
        treenode = Tree(title)
        nodesbyid[nodeid] = treenode

    for srcnode, edgelist in edges.items():
        children = edgelist.get("edges", [])
        for next in children:
            destnodeid = next["destNode"]
            incount[destnodeid] += 1
            destnode = nodesbyid[destnodeid]
            nodesbyid[srcnode].add(destnode)

    dag_title = f"[bold]{dag['title']}[/bold]  -  ({dag['id']})"
    if any([v == "yes" for v in problem_info.values()]):
        dag_title = f"[{problem_color}]{dag_title}"
    else:
        dag_title = f"[{normal_color}]{dag_title}"
    root = Tree(dag_title)
    for nodeid, node in nodesbyid.items():
        if incount[nodeid] == 0:
            root.add(node)
    return root

def dag_info_with_exec(dag, problem_info=None):
    problem_info = problem_info or defaultdict(str)
    out = {"title": f"{dag['title']} ({dag['id']})", "children": []}
    nodesbyid = {}
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", {})
    incount = defaultdict(int)
    for node in nodes:
        nodeid = node["id"]
        title = node["title"] + f"  ({nodeid})"
        if problem_info[nodeid] == "yes":
            title = f"[Problem] - {title}"
        elif problem_info[nodeid] == "no":
            title = f"[Not Problem] - {title}"
        nodesbyid[nodeid] = {"title": title, "children": []}

    for srcnode, edgelist in edges.items():
        children = edgelist.get("edges", [])
        for next in children:
            destnodeid = next["destNode"]
            incount[destnodeid] += 1
            destnode = nodesbyid[destnodeid]
            nodesbyid[srcnode]["children"].append(destnode)

    for nodeid, node in nodesbyid.items():
        if incount[nodeid] == 0:
            out["children"].append(node)
    return out
