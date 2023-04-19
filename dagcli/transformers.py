
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

def dag_map_transformer(dags):
    return {"title": "dags",
            "children": map(dag_info_transformer, dags["dags"])}

def dag_list_transformer(node):
    return {"title": "dags",
            "children": map(dag_info_transformer, node["dags"])}
