from ipdb import set_trace

def dag_info_transformer(dag):
    out = {"title": f"{dag['id']} - {dag['title']}"}
    nodes = dag.get("nodes", {})
    for nodeid, edgelist in nodes.items():
        if "children" not in out: out["children"] = []
        child = {"title": "Node " + nodeid}
        edges = edgelist.get("edges", [])
        for edge in edges:
            if "children" not in child: child["children"] = []
            child["children"].append({"title": edge["destNode"]})
        out["children"].append(child)
    return out

def dag_list_transformer(dags):
    return {"title": "dags",
            "children": map(dag_info_transformer, dags)}

def node_info_transformer(dagnode):
    node = dagnode["node"]
    edges = dagnode.get("outEdges", {}).get("edges", [])
    out = {"title": f"{node['id']}  :   {node['title']}"}
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
