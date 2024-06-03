import urllib
import datetime
import subprocess
import time
import json
import os
import sys
import requests
from enum import Enum
from dagcli import config
from dagcli.root import common_params, ensure_access_token
from dagcli.utils import read_envfile
import random
import string
import traceback
import typer

app = typer.Typer()

class LLMChoices(str, Enum):
    MISTRAL = "mistral"
    OPENAI = "openai"
    CLAUDE = "claude"
    LLAMA3 = "llama3"

CONFIGURABLE_TOOLS = {
    "slack": {
        "params": [ "SLACK_API_TOKEN" ]
    },
    "jira": {
        "params": [ "JIRA_USER_NAME", "JIRA_API_KEY", "JIRA_BASE_URL" ]
    },
    "github": {
        "params": [ "GITHUB_API_TOKEN", "GITHUB_LOCAL_REPOS", "GITHUB_REPOS_OWNER" ]
    },
    "rundeck": {
        "params": ["RUNDECK_URL", "RUNDECK_API_TOKEN"]
    },
    "elk": {
        "params": ["ELASTIC_URL", "ELASTIC_USER_NAME", "ELASTIC_PASSWORD"]
    },
    "servicenow": {
        "params": ["SNOW_USER_NAME", "SNOW_PASSWORD", "SNOW_URL"]
    },
}

@app.command()
def config(ctx: typer.Context,
           tool: str = typer.Argument(..., help = f"Name of the tool to configure.  Options: {list(CONFIGURABLE_TOOLS.keys())}"),
           dagknows_home: str = typer.Option("~/.dagknows", envvar="DagKnowsHomeDir", help="Dir for DagKnows configs"),
           profile: str = typer.Option(None, envvar="DagKnowsProfile", help="DagKnows profile to use.  To set a default run `dk profiles set-default`"),
           access_token: str = typer.Option(None, envvar='DagKnowsAccessToken', help='Access token for accessing DagKnows APIs')):
    if tool not in CONFIGURABLE_TOOLS:
        print("Invalid tool: ", tool)
        return

    common_params(ctx, dagknows_home, profile, access_token)

    tools_envfilepath = ctx.obj.getpath("tools_env_vars", profile_relative=False)
    tools_env = read_envfile(tools_envfilepath)

    from prompt_toolkit import PromptSession
    prompt_session = PromptSession()
    
    for param in CONFIGURABLE_TOOLS.get(tool,{}).get("params", []):
        user_input = prompt_session.prompt(f"Enter value for {param}: ").strip()
        tools_env[param] = user_input

    # write back now
    envvals = [f"{k}={v}" for k,v in tools_env.items()]
    with open(tools_envfilepath, "w") as tools_envfile:
        tools_envfile.write("\n".join(envvals))


@app.command()
def ai(ctx: typer.Context,
       dagknows_home: str = typer.Option("~/.dagknows", envvar="DagKnowsHomeDir", help="Dir for DagKnows configs"),
       profile: str = typer.Option(None, envvar="DagKnowsProfile", help="DagKnows profile to use.  To set a default run `dk profiles set-default`"),
       access_token: str = typer.Option(None, envvar='DagKnowsAccessToken', help='Access token for accessing DagKnows APIs'),
       session_id: str = typer.Argument(None, help = "IDs of the session to push messages to"),
       llm_type: LLMChoices = typer.Option(LLMChoices.OPENAI, help = "The LLM to be used remotely"),
       show_messages: bool = typer.Option(True, envvar="SHOW_DK_MESSAGES", help = "Whether to show messages from AI or not"),
       auto_exec: bool = typer.Option(True, help = "Whether to automatically execute commands or prompt first before executing")):
    """ Start an AI session or connect to one. """
    common_params(ctx, dagknows_home, profile, access_token)
    ensure_access_token(ctx)
    print("Hello World")
    dk_token = ctx.obj.access_token
    dk_host_url = ctx.obj.profile_data["api_host"]
    if dk_host_url.endswith("/api"):
        dk_host_url = dk_host_url[:-4]
    client = Client(session_id, dk_host_url, dk_token, llm_type)
    client.in_dkcli = True
    client.auto_exec = auto_exec
    client.llm.show_dk_messages = show_messages
    client.run()

class bcolor:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

ask = "ASK" # bcolor.OKBLUE + "ASK: " + bcolor.ENDC
exe = bcolor.WARNING + "EXEC:" + bcolor.ENDC + "\n"
dk = bcolor.OKGREEN + "DK: " + bcolor.ENDC + "\n"

class Client:
    def __init__(self, session_id, dk_host_url, dk_token, llm_type):
        self.in_dkcli = False
        self.auto_exec = True
        self.dk_host_url = dk_host_url
        from prompt_toolkit import PromptSession
        self.dk_token = dk_token
        # from prompt_toolkit import print_formatted_text, HTML
        self.prompt_session = PromptSession()
        llm = RemoteLLM(llm_type.value, session_id, None, dk_host_url, dk_token)
        self.llm = llm
        print(f"AI Session URL: {self.dk_host_url}/cli-sessions/{llm.session_id}")

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.dk_token}"}

    def run(self):
        llm = self.llm
        llm.interact("")
        i = 0
        while True:
            i += 1
            if False and i == 1:
                user_input = "list latest 10 jira tickets in project DD"
            else:
                user_input = self.prompt_session.prompt(llm.ask_prompt)
            if user_input == "/exit":
                break
            elif user_input.strip().startswith("/"):
                self.handle_user_command(user_input.strip())
            else:
                self.handle_input(user_input)

    def search_tasks(self, query):
        q = {urllib.parse.quote(query)}
        search_path = f"api/tasks/?with_pending_perms=false&page_key=0&page_size=5&q={q}&knn.k=3&knn.nc=10&order_by=elastic"
        resp = requests.get(f"{self.dk_host_url}/{search_path}",
                            headers=self.auth_headers,
                            verify=True)
        if resp.status_code != 200:
            print("Error: ", resp.content)
            return []
        return resp.json()["tasks"]


    def handle_user_command(self, user_input):
        if user_input == "/reset":
            self.llm.reset()
            print(f"AI Session URL: {self.dk_host_url}/cli-sessions/{self.llm.session_id}")
        elif user_input.strip().startswith("/exec"):
            query = user_input.strip()[5:].strip()
            tasks = self.search_tasks(query)
            for i, t in enumerate(tasks): print(f"{i + 1} ({t['id']}) - {t['title']}")
            if not tasks:
                print("No tasks found")
                return

            try:
                ui2 = int(self.prompt_session.prompt("Which task would you like to run? ").strip())
            except:
                print("Invalid selection")
                return

            try:
                seltask = tasks[ui2 - 1]
                print("Executing Task: ", seltask["title"], seltask["id"])
                input_params = {}
                for inp in seltask.get("input_params", []):
                    iname = inp["name"]
                    itype = inp["param_type"]
                    val = self.prompt_session.prompt(f"Enter value for '{iname} (type: {itype})': ").strip()
                    if val:
                        if val[0] in ("[", "{"): val = json.loads(val)
                        if itype.lower().startswith("int"): val = int(val)
                        if itype.lower().startswith("float"): val = float(val)
                        input_params[iname] = val

                self.execute_task(seltask, input_params)
            except:
                print("Error: ", traceback.format_exc())

    def handle_input(self, user_input):
        ai_resp = self.llm.handle_user_input(user_input)

        assert "type" in ai_resp, "No type in AI response"
        assert "message" in ai_resp, "No message in AI response"

        # This is now that we have the response from the remote agent
        if ai_resp["type"] == "command":
            if self.llm.show_dk_messages: print(dk, ai_resp["message"])
            permission = "y"
            if not self.auto_exec:
                print("Executing command: ", ai_resp["message"])
                permission = input("Should I execute? (y/N): ") or ("n")

            # Ask for execution of a command and execute it
            if permission in ["Y", "y", "Yes", "YES"]:
                p = subprocess.run(
                    ai_resp["message"], 
                    stdin=subprocess.PIPE, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    shell=True
                )
                stdout_contents = p.stdout.decode('utf-8')
                stderr_contents = p.stderr.decode('utf-8')
                if stdout_contents: print(exe, stdout_contents)
                if stderr_contents: print(exe, stderr_contents)

                # Append to messages if executed
                exec_output = "type : command\n"
                exec_output += f"code : {ai_resp['message']}\n"
                exec_output += f"stdout : {stdout_contents}\n"
                exec_output += f"stderr : {stderr_contents}"
                exec_message = {
                    "role" : "user",
                    "content" : exec_output 
                 }
                self.llm.add_message(exec_message, {
                     "type": "command",
                     "code": ai_resp['message'],
                     "stdout": stdout_contents,
                     "stderr": stderr_contents,
                 })

        elif ai_resp["type"] == "python":
            # Ask for execution of a script and execute it
            if self.llm.show_dk_messages: print(dk, ai_resp["message"])
            permission = "y"
            if not self.auto_exec:
                print("Executing script: \n", ai_resp["message"])
                permission = input("Should I execute? (y/N): ") or ("n")

            # Ask for execution of a command and execute it
            # permission = input(exe + "Should I execute? (Y/n): ") or ("n")
            if permission in ["Y", "y", "Yes", "YES"]:
                # Let's write this to a file and then execute
                filename = ''.join(random.choices(string.ascii_uppercase, k=16))
                filename = filename + ".py"
                fh = open(filename, "w")
                fh.write("import os\n")
                fh.write(ai_resp["message"])
                fh.close()
                #print(f"Stored the code in {filename} and executing now")
                p = subprocess.run(
                        f"python3 ./{filename}", 
                        stdin=subprocess.PIPE, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        shell=True
                    )
                stdout_contents = p.stdout.decode('utf-8')
                stderr_contents = p.stderr.decode('utf-8')
                if stdout_contents: print(exe, stdout_contents)
                if stderr_contents: print(exe, "STDERR: " + stderr_contents)

                # Append to messages
                exec_output = "type : python\n"
                exec_output += f"code : same as what assistant provided\n"
                exec_output += f"stdout : {stdout_contents}\n"
                exec_output += f"stderr : {stderr_contents}"
                exec_message = {
                    "role" : "user",
                    "content" : exec_output 
                }
                self.llm.add_message(exec_message, {
                    "type": "python",
                    "code": ai_resp['message'],
                    "stdout": stdout_contents,
                    "stderr": stderr_contents,
                })
        else:
            # Just text message. Print it
            print(dk, ai_resp["message"])

    def execute_task(self, task, params=None):
        resp = requests.get(f"{self.dk_host_url}/api/tasks/{task['id']}/compile?nomain=true",
                            headers=self.auth_headers,
                            verify=True)
        if resp.status_code != 200:
            print("Compile Error: ", resp.content)
            return

        code = resp.json()
        filename = ''.join(random.choices(string.ascii_uppercase, k=16))
        filename = filename + ".py"
        fh = open(filename, "w")
        for k,v in (params or {}).items():
            if type(v) is str:
                fh.write(f"{k} = '{v}'\n")
            else:
                fh.write(f"{k} = {v}\n")
        fh.write("\n".join(code["code_lines"]))
        print(f"Stored the code in {filename} and executing now")

        if self.in_dkcli:
            from pkg_resources import resource_string
            resdata = resource_string("dagcli", f"scripts/daglib.py")
            with open("daglib.py", "w") as dlb:
                dlb.write(resdata.decode())

        # Also download daglib if we are cli mode

        params = params or {}
        fh.write(f"""
def echo_resp_sender(self, resp):
    print(f"[{{resp['req']}}]: ", resp['msg'])

job_class= eval(f\"job_{{JOB_ID}}\")
from daglib import daglib
user_info = {{'uid': 666, "first_name": "User", "last_name": "None"}}
token = \"{self.dk_token}\"
dlb = daglib(None, user=None, jwt=token)
dlb.command_caller = subprocess_caller
j = job_class(dlb, None)
j.starting_task_param_values = {params}
j.msgsender = MSGEcho(j)
j.command_caller = subprocess_caller
j.resp_sender = echo_resp_sender
j.run(JOB_ID, conv_id="", user_info=user_info, iter_id=0)
""")
        fh.close()

        p = subprocess.run(
        f"python3 ./{filename}", 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            shell=True
        )
        stdout_contents = p.stdout.decode('utf-8')
        stderr_contents = p.stderr.decode('utf-8')
        if stdout_contents: print(exe, stdout_contents)
        if stderr_contents: print(exe, "STDERR: " + stderr_contents)

        # Append to messages
        exec_output = "type : python\n"
        exec_output += f"code : user selected task\n"
        exec_output += f"stdout : {stdout_contents}\n"
        exec_output += f"stderr : {stderr_contents}"
        exec_message = {
                        "role" : "user",
                        "content" : exec_output 
                    }
        self.llm.add_message(exec_message, {
            "type": "python",
            "code": f"Task ID: {task['id']}",
            "stdout": stdout_contents,
            "stderr": stderr_contents,
        })
        return exec_output

# =======================================================================================


def get_available_tools():
    return ["jira", "servicenow", "elk", "slack", "github", "rundeck"]

class LLM:
    def __init__(self, session_id=None, tools_enabled=None, dk_host_url=None, dk_token=None, user_info=None, admin_settings=None):
        self.user_info=user_info
        self.admin_settings=admin_settings
        self.dk_token = dk_token
        self.dk_host_url = dk_host_url
        self.tools_enabled = tools_enabled or get_available_tools()
        self.messages = []
        self.num_input_bytes = 0
        self.num_output_bytes = 0
        self.num_input_tokens = 0
        self.num_output_tokens = 0
        self.num_llm_calls_made = 0
        self.total_latency = 0
        self.exception_count = 0
        self.show_dk_messages = True
        self.session_id = self.ensure_session(session_id)
        print("Using Model: ", self.model_name)

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.dk_token}"}

    def ensure_session(self, session_id=None):
        if session_id:
            resp = self.get_session(session_id)
            msgs = resp.get("conv", {})
            for idx,msg in sorted([(k,v) for k,v in msgs.items()]):
                if msg.get("full_message"):
                    self.messages.append(msg["full_message"])
        else:
            resp = requests.post(self.create_session_url,
                                 headers=self.auth_headers,
                                 json={
                                     "subject": f"AI session at {datetime.datetime.utcnow().isoformat()}",
                                     "conv_type": "aiagent"
                                 }, verify=True)
            rj = resp.json()
            session_id = rj["conv_context"]["id"]
        return session_id

    def get_session(self, session_id):
        print(f"Fetching session: {session_id}...")
        if self.dk_host_url == "<local>":
            resp = requests.post(f"http://conv-mgr:2224/getConv",
                                 headers=self.auth_headers,
                                 json={"conv_id": session_id,
                                       "user_info": self.user_info,
                                       "admin_settings": self.admin_settings },
                                 verify=True)
            rj = resp.json()
            if rj.get("responsecode").lower().strip() != "true":
                print("Error getting session: ", rj)
                sys.exit(1)
            print("Using existing conv session: ", rj["conv_context"]["id"])
        else:
            resp = requests.get(f"{self.dk_host_url}/api/v1/sessions/{session_id}",
                                headers=self.auth_headers, verify=True)
            rj = resp.json()
            if resp.status_code != 200:
                print("Error getting session: ", resp.content)
                sys.exit(1)
            print("Using existing conv session: ", rj["session"]["subject"])

        # now also list the messages
        resp = requests.post(f"{self.conv_mgr_url}/getConvOrCreate",
                             headers=self.auth_headers,
                             json={"conv_id": session_id,
                                   "user_info": self.user_info,
                                   "admin_settings": self.admin_settings },
                             verify=True)

        return resp.json()

    @property
    def conv_mgr_url(self):
        if self.dk_host_url == "<local>":
            return "http://conv-mgr:2224"
        else:
            return self.dk_host_url

    @property
    def create_session_url(self):
        if self.dk_host_url == "<local>":
            return f"http://conv-mgr:2224/createConv"
        else:
            return f"{self.dk_host_url}/createConv"

    @property
    def model_name(self):
        assert False, "set this"

    @property
    def prompt_model_name(self):
        return self.model_name

    @property
    def first_prompt(self):
        dirname = os.path.dirname(__file__)
        prompt_files = [
            f"prompts/{self.prompt_model_name}.first_prompt.txt",
            f"prompts/first_prompt.txt"
        ]
        for prompt_file in prompt_files:
            prompt_file = os.path.join(dirname, prompt_file)
            if os.path.isfile(prompt_file):
                return open(prompt_file).read()
        assert "Implement this method or create one of these prompt files: {prompt_files}"

    def get_tool_prompt(self, tool):
        tool = tool.lower().strip()
        dirname = os.path.dirname(__file__)
        prompt_files = [
            f"prompts/{self.model_name}.tools.{tool}.txt",
            f"prompts/tools.{tool}.txt"
        ]
        for prompt_file in prompt_files:
            prompt_file = os.path.join(dirname, prompt_file)
            if os.path.isfile(prompt_file):
                return open(prompt_file).read()
        assert "Implement this method or create one of these prompt tool files: {prompt_files}"

    @property
    def first_message(self):
        content = self.first_prompt
        for tool in self.tools_enabled:
            content += "\n" + self.get_tool_prompt(tool)
        return  {
            "role": "system",
            "content": content
        }

    def do_call_llm(self, trimmed_messages):
        self.num_llm_calls_made += 1
        start_time = time.time()
        out = self.call_llm(trimmed_messages)
        self.total_latency += (time.time() - start_time)
        return out

    def add_message(self, msg, extras=None):
        assert "role" in msg
        fm = { "msg": msg }
        for k,v in (extras or {}).items(): fm[k] = v

        if self.dk_host_url == "<local>":
            resp = requests.post("http://conv-mgr:2224/plainMessage",
                                 headers=self.auth_headers,
                                 json={
                                     "msg": msg["content"],
                                     "full_message": fm,
                                     "conv_id": self.session_id,
                                     "nostore": False,
                                     "user_info": self.user_info,
                                     "admin_settings": self.admin_settings,
                                 }, verify=True)
        else:
            resp = requests.post(f"{self.dk_host_url}/message",
                                 headers=self.auth_headers,
                                 json={
                                     "msg": msg["content"],
                                     "full_message": fm,
                                     "conv_id": self.session_id,
                                     "nostore": False,
                                 }, verify=True)
        rj = resp.json()
        self.messages.append(msg)

    @property
    def set_trace(self):
        import ipdb
        return ipdb.set_trace
    
    def trimmed_messages(self):
        trimmed_messages = self.messages
        if len(self.messages) >= 10:
            trimmed_messages = self.messages[len(self.messages) - 10:]
        return trimmed_messages

    def add_user_message(self, msg):
        self.add_message({ "role" : "user", "content" : msg }, { "type": "usermsg", })

    def handle_user_input(self, user_input):
        ai_resp = self.interact(user_input)
        empty_resp_iter_count = 0
        while (not ai_resp and empty_resp_iter_count < 3):
            print("ERROR: Empty AI response! Trying again")
            feedback = "Your output was either malformed or empty. Please try again"
            ai_resp = self.interact(feedback)
            empty_resp_iter_count = empty_resp_iter_count + 1
        assert ai_resp, "AI response is empty"
        missing_fields_iter_count = 0
        while ("type" not in ai_resp or "message" not in ai_resp) and missing_fields_iter_count < 3:
            print("ERROR: Missing fields in AI response! Trying again: ", ai_resp.keys())
            feedback = "Your output is malformed. As mentioned before, your output must be a parseable JSON dictionary and nothing else.  Ensure that the JSON output starts with { and ends with }.  The JSON dictionary must have two keys: message and type. The meaning of these fields has been specified before. Please try again."
            ai_resp = self.interact(feedback)
            missing_fields_iter_count = missing_fields_iter_count + 1
        return ai_resp

    def interact(self, user_message):
        try:
            if user_message:
                self.add_user_message(user_message)
         
                content = self.do_call_llm(self.trimmed_messages())
                assistant_response = {
                    "role" : "assistant",
                    "content" : content
                }
                self.add_message(assistant_response, { "type": "assistantmsg", })
                try:
                    ai_resp = json.loads(content)
                    self.exception_count = 0
                    return ai_resp
                except Exception as e:
                    self.exception_count += 1
                    if (self.exception_count < 4):
                        error_msg = f"Your output is not JSON parseable. Remember, your output must be a JSON dict with keys called type and message. The meaning of these keys has been specified earlier. Please try again."
                        print(f"ERROR: exception count = {self.exception_count} Exception: JSON parsing problem -- {traceback.format_exc()} \n Trying again")
                        self.interact(error_msg)
                    else:
                        print("ERROR: Got so many exceptions. Giving up. Here's the message context so far: ", json.dumps(self.messages, indent=4))
                        return {"type" : "text", "message" : "ERROR. I am unable to fulfill your request. Sorry, try asking the question a different way."}
        except Exception as e:
            self.exception_count += 1
            if (self.exception_count < 4):
                error_msg = f"I got the following exception when I tried to interact with you: {traceback.format_exc()}. \n Please try again."
                print(f"ERROR: exception count = {self.exception_count} Exception: {traceback.format_exc()} \n Trying again")
                self.interact(error_msg)
            else:
                print("ERROR: Got so many exceptions. Giving up. Here's the message context so far: ", json.dumps(self.messages, indent=4))
                return {"type" : "text", "message" : "ERROR. I am unable to fulfill your request. Sorry, try asking the question a different way."}

    def reset(self):
        del self.messages[1:]
        self.num_input_bytes = 0
        self.num_output_bytes = 0
        self.num_input_tokens = 0
        self.num_output_tokens = 0
        self.num_llm_calls_made = 0
        self.total_latency = 0

    @property
    def ask_prompt(self):
        return f"{ask}: "
        # return f"[C: {self.num_llm_calls_made}, I: {self.num_input_tokens}, O: {self.num_output_tokens}, L: {int(self.total_latency * 1000)}ms] {ask}: "

    def msghandler(request):
        session_id = request.session_id
        llm_type = request.llm_type

class RemoteLLM(LLM):
    def __init__(self, llm_type, session_id=None, tools_enabled=None, dk_host_url=None, dk_token=None, user_info=None, admin_settings=None):
        self.llm_type = llm_type
        super().__init__(session_id, tools_enabled, dk_host_url, dk_token, user_info, admin_settings)

    def reset(self):
        super().reset()
        # Create a new session
        self.session_id = self.ensure_session(None)

    @property
    def model_name(self):
        return f"remote_model_{self.llm_type}"

    def handle_user_input(self, user_input):
        # Call the remote endpoint
        payload = {"session_id": self.session_id,
                   "llm_type": self.llm_type,
                   "user_input": user_input,
                   "dk_token": self.dk_token}
        resp = requests.post(f"{self.dk_host_url}/call_llm",
                             headers=self.auth_headers, verify=True,
                             json=payload)
        rj = resp.json()
        print("Remote Resp: ", rj)
        return rj.get("msg", {})

# =======================================================================================

if __name__ == "__main__":
    app()
