import json
from collections import defaultdict

def dag_list_transformer(dags):
    return {"title": "dags",
            "children": map(dag_info_with_exec, dags)}

problem_color = "red"
not_problem_color = "green"
normal_color = "#5ebbff"

def node_info_transformer(dagnode):
    node = dagnode["node"]
    edges = (dagnode.get("outEdges", {}) or {}).get("edges", []) or []
    out = {"title": f"{node['title']} ({node['id']})"}
    for edge in edges:
        if "children" not in out: out["children"] = []
        out["children"].append({"title": edge["destNode"]})
    return out

def node_list_transformer(nodes):
    return {"title": "nodes",
            "children": map(node_info_transformer, nodes)}

"""
dagcli nodes get R7YGKMUGWMDlP1HkWg68H9m8m8aejTy6 --dag-id Mu3CFBZvlwNjYoZVA13SC8Gpm4D16Fdi
"""

def rich_dag_info_with_exec(dag, problem_info=None):
    from rich.tree import Tree

    nodesbyid = {}
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", {})
    incount = defaultdict(int)
    for node in nodes:
        nodeid = node["id"]
        title = node["title"] + f"  ({nodeid})"
        if problem_info[nodeid] == "yes":
            title = f"[{problem_color}][Problem] - {title}"
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

    dag_title = f"{dag['title']} ({dag['id']})"
    if len([v == "yes" for v in problem_info.values()]) > 0:
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
