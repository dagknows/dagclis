
import requests
import json
import re
import os
from dagcli.client import SessionClient

class DagKnowsConfig:
    def __init__(self, homedir, **data):
        self.homedir = homedir
        self.data = data
        self.profile_data = {}
        self._client = None
        self.tree_transformer = None
        self.load()

    def getpath(self, path, is_dir=False, ensure=False):
        """ Gets name of a file within the home dir. """
        out = os.path.expanduser(os.path.join(self.homedir, self.curr_profile, path))
        if ensure:
            if is_dir:
                if not os.path.isdir(out):
                    os.makedirs(out)
            else:
                # a file - so ensure its parent path exists
                parentpath, basepath = os.path.split(out)
                if not os.path.isdir(parentpath):
                    os.makedirs(parentpath)
                if not os.path.isfile(basepath):
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
        if "access_token" in self.data:
            return self.data["access_token"]
        if self.all_access_tokens:
            return self.all_access_tokens[0]
        return None

    @property
    def all_access_tokens(self):
        return self.profile_data.get("access_tokens", [])

    @all_access_tokens.setter
    def all_access_tokens(self, access_tokens):
        values = [atok for atok in access_tokens if not atok["revoked"]]
        for atok in values:
            atok["expires_at"] = time.time() + atok["expiry"]
        self.profile_data["access_tokens"] = values
        self.save()

    @property
    def curr_profile(self):
        return self.data["profile"]

    @curr_profile.setter
    def curr_profile(self, newprofile):
        if newprofile != self.curr_profile:
            self.save()
            self._client = None
            self.data["profile"] = newprofile

    @property
    def client(self):
        if self._client is None:
            host = self.data["reqrouter_host"]
            self._client = SessionClient(host, self.getpath("cookies"))
        return self._client

    @property
    def config_file(self):
        return self.getpath("config", ensure=True)

    def load(self):
        if not os.path.isdir(self.homedir):
            print(f"Ensuring DagKnows home dir: {self.homedir}")
            os.makedirs(self.homedir)
        data = open(self.config_file).read()
        self.profile_data = json.loads(data) if data else {}

    def save(self):
        """ Serializes the configs back (for the current profile) to files. """
        with open(self.config_file, "w") as configfile:
            configfile.write(json.dumps(self.profile_data, indent=4))

    def ensure_host(self, host):
        normalized_host = host.replace("/", "_")
        return self.getpath(normalized_host, is_dir=True, ensure=True)
