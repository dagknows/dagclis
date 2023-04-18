
from ipdb import set_trace
import typer
import requests
import json
import re
import os
import pickle
from pprint import pprint
from typing import List

def make_url(host, path):
    url = host
    if path.startswith("/"):
        path = path[1:]
    if host.endswith("/"):
        host = host[:-1]
    return f"{url}/{path}"

class SessionClient:
    def __init__(self, host, session_file):
        self.host = host
        self.session_file = session_file
        self.load_session()

    def reset(self):
        self.session = requests.Session()
        self.session.verify = False
        self.savecookies()

    def load_session(self, verbose=True):
        self.session = requests.Session()
        self.session.verify = False
        from urllib3.exceptions import InsecureRequestWarning
        from urllib3 import disable_warnings
        disable_warnings(InsecureRequestWarning)

        # This is for verbose debugging
        if verbose:
            import logging
            from http.client import HTTPConnection  # py3
            log = logging.getLogger('urllib3')
            log.setLevel(logging.DEBUG)

            # logging from urllib3 to console
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            log.addHandler(ch)

            # print statements from `http.client.HTTPConnection` to console/stdout
            HTTPConnection.debuglevel = 1

    def savecookies(self):
        with open(self.session_file, 'wb') as f:
            pickle.dump(self.session.cookies, f)

    def loadcookies(self):
        if os.path.isfile(self.session_file):
            with open(self.session_file, 'rb') as f:
                self.session.cookies.update(pickle.load(f))

    def login_with_email(self, email, password, org):
        url = make_url(self.host, f"/user/sign-in?org={org}")
        """
        resp = self.session.get(url)
        content = resp.content
        contentstr = str(content)
        m = re.search(r"(\<input[^>]*name=\"csrf_token\"[^>]*)value=\"([^\"]*)\"", contentstr)
        if not m or len(m.groups()) != 2:
            raise Exception(f"Invalid sign-in URL: f{url}")
        csrf_token = m.groups()[1]
        """
        payload = {
            # "req_next": "/",
            # "csrf_token": csrf_token,
            "email": email,
            "password": password,
            "org": org,
        }
        resp = self.session.post(url, data=payload)
        self.savecookies()

    def list_tokens(self):
        url = make_url(self.host, "/getSettings?org=dagknows")
        set_trace()
        resp = self.session.post(url, json={})
        resp = resp.json()
        if resp.get("responsecode", False) in (False, "false", "False"):
            print(resp["msg"])
            return
        admin_settings = resp["admin_settings"]
        set_trace()
        return ""

    def add_proxy(self, label):
        url = make_url(self.host, "/addAProxy")
        payload = { "alias": label, }
        resp = self.session.post(url, json=payload)
        return resp.json()

    def list_proxies(self):
        url = make_url(self.host, "/getSettings")
        resp = self.session.post(url, json={}).json()
        if resp.get("responsecode", False) in (False, "false", "False"):
            print(resp["msg"])
            return
        admin_settings = resp["admin_settings"]
        proxy_table = admin_settings["proxy_table"]
        return proxy_table.keys()

    def download_proxy(self, label):
        url = make_url(self.host, "/getSettings")
        resp = self.session.post(url, json={})
        resp = resp.json()
        if resp.get("responsecode", False) in (False, "false", "False"):
            print(resp["msg"])
            return
        admin_settings = resp["admin_settings"]
        proxy_table = admin_settings["proxy_table"]
        if label not in proxy_table:
            return None
        proxy_info = proxy_table[label]
        import base64
        proxy_bytes = base64.b64decode(proxy_info["proxy_code"])
        return proxy_bytes

    def delete_proxy(self, label):
        url = make_url(self.host, "/deleteAProxy")
        payload = { "alias": label, }
        resp = self.session.post(url, json=payload)
        return resp.json()
        
    def generate_access_token(self, label, expires_in=30*86400):
        url = make_url(self.host, "/generateAccessToken")
        payload = {
            "label": label,
            "exp": expires_in
        }
        set_trace()
        resp = self.session.post(url, json=payload)
        return resp.json()

    def revoke_access_token(self, token):
        url = make_url(self.host, "/revokeToken")
        payload = { "token": token }
        resp = self.session.post(url, json=payload)
        return resp.json()

def oldapi(cmd, payload=None, url="https://localhost:443", access_token=""):
    fullurl = f"{url}/{cmd}"
    headers = {"Authorization": f"Bearer {access_token}"}
    set_trace()
    resp = requests.post(fullurl, json=payload or {}, headers=headers, verify=False)
    print(json.dumps(resp.json(), indent=4))
    return resp

def newapi(ctx: typer.Context, path, payload=None, method = ""):
    url = make_url(ctx.obj.data["api_host"], path)
    method = method.lower()
    headers = ctx.obj.data["headers"]
    if not method.strip():
        if payload: method = "post"
        else: method = "get"
    methfunc = getattr(requests, method)
    if ctx.obj.data["log_request"] == True:
        print(f"API Request: {method.upper()} {url}: ", payload)
    if payload:
        if method == "get":
            resp = methfunc(url, params=payload, headers=headers)
        else:
            resp = methfunc(url, json=payload, headers=headers)
    else:
        resp = methfunc(url, headers=headers)
    # print(json.dumps(resp.json(), indent=4))
    result = resp.json()
    pprint(result)
    return result