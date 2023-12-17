import typer, yaml, json, os, logging
from pprint import pprint
from boltons.iterutils import remap
from rich import print as rprint
from rich.tree import Tree
import psutil

ALLOWED_SHELLS = ["bash", "zsh"]

def disable_urllib_warnings():
    from urllib3 import disable_warnings
    from urllib3.exceptions import NotOpenSSLWarning
    disable_warnings(NotOpenSSLWarning)
    from urllib3.exceptions import InsecureRequestWarning
    disable_warnings(InsecureRequestWarning)
    from urllib3.exceptions import InsecurePlatformWarning
    disable_warnings(InsecurePlatformWarning)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('requests').setLevel(logging.CRITICAL)

def get_curr_shell():
    currproc = psutil.Process(os.getppid())
    while currproc:
        if currproc.name() in ALLOWED_SHELLS:
            return currproc.name()
        currproc = currproc.parent()
    return None

def print_reco(reco):
    class bcolors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    cmd = reco['cmd']
    title = reco['title']
    dag_title = reco['dag_title']
    dag_id = reco['dag_id']
    print(bcolors.OKGREEN + bcolors.BOLD + "next: " + bcolors.ENDC + bcolors.ENDC + ' ' + title)
    print(bcolors.OKGREEN + bcolors.BOLD + "command: " + bcolors.ENDC + bcolors.ENDC)
    print(" ", bcolors.OKBLUE + bcolors.BOLD + cmd + bcolors.ENDC + bcolors.ENDC)
    print(bcolors.OKGREEN + bcolors.BOLD + "runbook: " + bcolors.ENDC + bcolors.ENDC + ' ' + dag_title)
    print(bcolors.OKGREEN + bcolors.BOLD + "runbook id: " + bcolors.ENDC + bcolors.ENDC + ' ' + dag_id)
    print("----------------------------------------------------")

def ensure_shellconfigs(ctx: typer.Context, shell_type=None):
    for f in ["bashrc", "zshrc", "dag.commonrc", "bash-preexec.sh"]:
        from pkg_resources import resource_string
        respath = ctx.obj.getpath(f, profile_relative=False)
        resdata = resource_string("dagcli", f"scripts/{f}")
        with open(respath, "w") as resfile:
            resfile.write(resdata.decode())

    shell_type = shell_type = get_curr_shell()
    if not shell_type:
        raise "Could not detect shell type"

    from rich.prompt import Prompt, Confirm
    if shell_type == "zsh":
        dkzshrc = ctx.obj.getpath("zshrc", profile_relative=False)
        usr_shell_rc = os.path.expanduser("~/.zshrc")
        dk_shell_rc = dkzshrc
    else:
        dkbashrc= ctx.obj.getpath("bashrc", profile_relative=False)
        usr_shell_rc = os.path.expanduser("~/.bashrc")
        dk_shell_rc = dkbashrc

    added_line = f"source {dk_shell_rc}"
    line_found = (os.path.isfile(usr_shell_rc) and added_line in open(usr_shell_rc).read().split("\n"))
    if not line_found:
        if Confirm.ask("Would you like to source dagknows shell confings in your {usr_shell_rc} file?", default=True):
            with open(usr_shell_rc, "a") as usr_shell_rc_file:
                usr_shell_rc_file.write(f"\n{added_line}")
                line_found = True
    return line_found

def present(ctx: typer.Context, results, notree=False):
    def unnecessary_fields(p, k, v):
        if v in (None, "", {}, []) or k == "requesting_user" or k == "proxy":
            return False
        if type(v) is str and not v.strip(): return False
        if k in ["createdAt", "updatedAt"]: return False
        return True

    output_format = ctx.obj.output_format
    if output_format == "tree" and notree:
        output_format = "yaml"

    filtered_results = remap(results, unnecessary_fields)
    if output_format == "json":
        print(json.dumps(filtered_results, indent=4))
    elif output_format == "yaml":
        print(yaml.dump(filtered_results, indent=4, sort_keys=False))
    elif output_format == "pprint":
        pprint(filtered_results)
    elif output_format == "tree":
        # Then our results are actually a tree where each node has only 2 keys - a "title" and a "children"
        # we can render this in tree format with "|" etc
        if results:
            tree = {}
            if type(results) in (bool, str, int, float):
                pprint(results)
            elif not ctx.obj.tree_transformer:
                print(yaml.dump(filtered_results, indent=4, sort_keys=False))
                # assert False, "'tree' output format needs a tree transformer to convert results into a tree structure where each node only has either 'title' or 'children'"
            else:
                tree = ctx.obj.tree_transformer(results)
                if type(tree) is Tree:
                    rprint(tree)
                else:
                    lines = render_tree(tree)
                    print("\n".join(lines))
    else:
        # Apply a result type specific transformer here
        print("Invalid output format: ", output_format)

def make_tree(prefix, num_levels, num_children_per_level):
    root = {"title": prefix, "children": []}
    if num_levels > 0:
        for i in range(num_children_per_level):
            root["children"].append(make_tree(f"{prefix}.{i}", num_levels - 1, num_children_per_level))
    return root

t1 = make_tree("Root", 0, 0)
t2 = make_tree("Node", 3, 3)

def render_tree(root, indent=4):
    output = render_node(root, [], 0, indent=indent)
    lines = [((level - 1) * " ") + sp + lp + (" ") + title if lp else title for (sp, lp, title,level) in output]
    # lines = [sp + lp + (" ") + title if lp else title for (sp, lp, title,level) in output]
    def pipeindex(level, indent=4):
        """ Given an indent size and "level" returns the index of where the starting "|" would occur """

    def setchar(s, index, ch):
         return s[:index] + ch + s[index+1:]

    for index, (sp, lp, title, level) in enumerate(output):
        if level > 0:
            pi = len(sp) + level - 1
            lines[index] = setchar(lines[index], pi, "\u2517")
            for nextind in range(index - 1, 0, -1):
                _,_,_,nextlevel = output[nextind]
                if nextlevel > level:
                    lines[nextind] = setchar(lines[nextind], pi, "\u2503")
                elif nextlevel == level:
                    lines[nextind] = setchar(lines[nextind], pi, "\u2523")
                else:
                    break
    return lines

def render_node(root, lines=None, level=0, indent=4):
    indentstr = " " * indent
    if lines is None: lines = []
    if root:
        space_prefix = ""
        line_prefix = ""
        if level > 0:
            space_prefix = (level - 1) * indentstr
            line_prefix = "|" + (indent - 1) * "\u2501"
        title = root if type(root) is str else root["title"]
        lines.append((space_prefix, line_prefix, title, level))

        if type(root) is not str:
            for child in root.get("children", []):
                lines = render_node(child, lines, level + 1, indent)
    return lines
