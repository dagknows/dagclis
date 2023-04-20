from ipdb import set_trace

def dag_info_transformer(dag):
    out = {"title": f"{dag['id']} - {dag['title']}", "children": []}
    nodesbyid = {}
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", {})
    for node in nodes:
        nodeid = node["id"]
        nodesbyid[nodeid] = {"title": nodeid + "  :  " + node["title"]}
        out["children"].append(nodesbyid[nodeid])

    for srcnode, edgelist in edges.items():
        children = edgelist.get("edges", [])
        for next in children:
            destnodeid = next["destNode"]
            destnode = nodesbyid[destnodeid]
            if "children" not in nodesbyid[srcnode]: nodesbyid[srcnode]["children"] = []
            nodesbyid[srcnode]["children"].append({"title": destnode["title"]})
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
