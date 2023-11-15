
import requests
import json
import re
import os
from dagcli.client import SessionClient

class DagKnowsConfig:
    def __init__(self, homedir, curr_profile="default", **data):
        self.homedir = homedir
        self.data = data
        self._curr_profile_data = {}
        self._client = None
        self._curr_profile = curr_profile
        self.tree_transformer = None
        self.load()

    @property
    def headers(self):
        out = {
            "Authorization": f"Bearer {self.access_token}",
        }
        rrhost = self.resolve("reqrouter_host")
        if rrhost: 
            out["DagKnowsReqRouterHost"] = rrhost
        return out

    def get(self, datakey):
        return self.data.get(datakey, None)

    def resolve(self, datakey):
        """ Tries to get pass an explicit value passed in. 
        Otherwise resolves based on the value set in the current profile. """
        out = self.data.get(datakey, None)
        if out != False and not out:
            return self.profile_data.get(datakey, None)
        return out

    def getpath(self, path, is_dir=False, ensure=False, profile_relative=True):
        """ Gets name of a file within the home dir. """
        if profile_relative:
            out = os.path.expanduser(os.path.join(self.homedir, self.curr_profile, path))
        else:
            out = os.path.expanduser(os.path.join(self.homedir, path))
        if ensure:
            if is_dir:
                if not os.path.isdir(out):
                    os.makedirs(out)
            else:
                # a file - so ensure its parent path exists
                parentpath, basepath = os.path.split(out)
                if not os.path.isdir(parentpath):
                    os.makedirs(parentpath)
                if not os.path.isfile(out):
                    # if file doesnt exist then create an empty one
                    open(out, "w").write("")
        return out

    @property
    def output_format(self):
        return self.data["output_format"]

    @property
    def access_token(self):
        # get the auth token from either one explicitly set
        # or form the current profile's list of auth tokens
        out = self.data.get("access_token", None)
        if out:
            return self.data["access_token"]
        if self.all_access_tokens:
            return self.all_access_tokens[0]["value"]
        return None

    @property
    def all_access_tokens(self):
        return self._curr_profile_data.get("access_tokens", [])

    @all_access_tokens.setter
    def all_access_tokens(self, access_tokens):
        values = [atok for atok in access_tokens if not atok["revoked"]]
        for atok in values:
            atok["expires_at"] = time.time() + atok["expiry"]
        self._curr_profile_data["access_tokens"] = values
        self.save()

    @property
    def profile_data(self):
        return self._curr_profile_data

    @property
    def curr_profile(self):
        return self._curr_profile

    @curr_profile.setter
    def curr_profile(self, newprofile):
        if newprofile != self.curr_profile:
            self.save()
            self._client = None
            self._curr_profile = newprofile
            self.load()

    @property
    def client(self):
        if self._client is None:
            host = self.data.get("reqrouter_host", None)
            if not host:
                host = self.profile_data["api_host"]
                if host.endswith("/api"): host = host[:-4]
            self._client = SessionClient(host, self.getpath("cookies"))
        return self._client

    @property
    def config_file(self):
        return self.getpath("config", ensure=True)

    def load(self):
        if not os.path.isdir(self.homedir):
            print(f"Ensuring DagKnows home dir: {self.homedir}")
            os.makedirs(self.homedir)
        data = open(self.config_file).read().strip()
        self._curr_profile_data = json.loads(data) if data else {}

    def save(self):
        """ Serializes the configs back (for the current profile) to files. """
        with open(self.config_file, "w") as configfile:
            configfile.write(json.dumps(self._curr_profile_data, indent=4))

    def ensure_host(self, host):
        normalized_host = host.replace("/", "_")
        return self.getpath(normalized_host, is_dir=True, ensure=True)
