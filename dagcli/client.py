
import typer
import requests
import json
import os, sys
from typing import List

from dagcli.utils import disable_urllib_warnings
disable_urllib_warnings()

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

    def load_session(self, verbose=False):
        self.session = requests.Session()
        self.session.verify = False

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
        import pickle
        with open(self.session_file, 'wb') as f:
            pickle.dump(self.session.cookies, f)

    def loadcookies(self):
        import pickle
        if os.path.isfile(self.session_file):
            with open(self.session_file, 'rb') as f:
                self.session.cookies.update(pickle.load(f))

    def login_with_email(self, email, password, org):
        url = make_url(self.host, f"/user/sign-in?org={org}")
        """
        resp = self.session.get(url)
        content = resp.content
        contentstr = str(content)
        import re
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
        resp = self.session.post(url, json={})
        resp = resp.json()
        if resp.get("responsecode", False) in (False, "false", "False"):
            print(resp["msg"])
            return
        admin_settings = resp["admin_settings"]
        return ""

    def add_proxy(self, label, dagknows_url=None):
        dagknows_url = dagknows_url or None
        url = make_url(self.host, "/addAProxy")
        payload = { "alias": label, "dagknows_url": dagknows_url}
        resp = self.session.post(url, json=payload)
        return resp.json()

    def list_proxies(self, access_token):
        url = make_url(self.host, "/getSettings")
        resp = self.session.post(url, json={}, headers={"Authorization": f"Bearer {access_token}"}).json()
        if resp.get("responsecode", False) in (False, "false", "False"):
            print(resp["msg"])
            return
        admin_settings = resp["admin_settings"]
        proxy_table = admin_settings.get("proxy_table", {})
        return proxy_table

    def download_proxy(self, label, access_token):
        url = make_url(self.host, "/getSettings")
        resp = self.session.post(url, json={}, headers={"Authorization": f"Bearer {access_token}"})
        resp = resp.json()
        if resp.get("responsecode", False) in (False, "false", "False"):
            print(resp)
            return
        admin_settings = resp["admin_settings"]
        proxy_table = admin_settings["proxy_table"]
        if label not in proxy_table:
            return None
        proxy_info = proxy_table[label]
        import base64
        proxy_bytes = base64.b64decode(proxy_info["proxy_code"])
        return proxy_bytes

    def delete_proxy(self, label, access_token):
        url = make_url(self.host, "/deleteAProxy")
        payload = { "alias": label, }
        resp = self.session.post(url, json=payload, headers={"Authorization": f"Bearer {access_token}"})
        return resp.json()
        
    def generate_access_token(self, label, expires_in=30*86400):
        url = make_url(self.host, "/generateAccessToken")
        payload = {
            "label": label,
            "exp": expires_in
        }
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
    resp = requests.post(fullurl, json=payload or {}, headers=headers, verify=False)
    return resp.json()

def newapi(dkconfig: "DagKnowsConfig", path, payload=None, method = "", apihost=None):
    apihost = apihost or dkconfig.resolve("api_host")
    url = make_url(apihost, path)
    method = method.lower()
    headers = dkconfig.headers
    if not method.strip():
        if payload: method = "post"
        else: method = "get"
    methfunc = getattr(requests, method)
    if dkconfig.resolve("log_requests") == True:
        print(f"API Request: {method.upper()} {url}: ", payload)
    if payload:
        if method == "get":
            resp = methfunc(url, params=payload, headers=headers, verify=False)
        else:
            resp = methfunc(url, json=payload, headers=headers, verify=False)
    else:
        resp = methfunc(url, headers=headers, verify=False)
    # print(json.dumps(resp.json(), indent=4))
    if resp.status_code != 200:
        print("Request Failed: ", resp.content)
        """
        if "message" in result:
            print(result["message"])
        else:
            print("Request failed: ", result)
        """
        sys.exit(1)
    result = resp.json()
    return result
