import hvac
import argparse
import sys
import json
import requests
import base64
import re
from os import listdir
from os.path import isfile, join

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class dagknows_proxy_vault():
    def __init__(self, vault_url, token):
        self.vault_url = vault_url
        self.cl = hvac.Client(self.vault_url, verify=False)
        self.cl.token = token

    def set_jwt_auth_key(self, public_key):
        """ Replacfes the public_key in our vault.  This is usually the entire contents of a 
        public key pem file you are using. """
        result = self.cl.auth.jwt.configure(jwt_validation_pubkeys=public_key)
        print("Configured jwt validation public key", result, file=sys.stdout)

    def list_roles(self):
        try:
           list_resp = self.cl.auth.jwt.list_roles()
   
           if 'data' in list_resp:
               return list_resp['data']['keys']
           return []
        except:
           return []

    def add_role(self, role):
        #Add the role
        self.cl.auth.jwt.create_role(
            name=role,
            role_type='jwt',
            allowed_redirect_uris=[self.vault_url],
            user_claim='sub',
            bound_claims={
                # 'roles/proxy' : role,
                'proxyrole' : role
            },
            bound_audiences=['dagknows'],
            token_policies=role+'_policy'
        )
        #Create a secrets engine for this role
        self.cl.sys.enable_secrets_engine(
            backend_type='kv',
            path=role+'_secrets'
        )
        
        #add a policy so only read access is allowed
        if role == 'admin':
            policy_str='path \"' + role +  '_secrets/*\" {capabilities = [\"read\", \"list\", \"delete\", \"sudo\"]}'
        else:
            policy_str='path \"' + role +  '_secrets/*\" {capabilities = [\"read\", \"list\"]}'

        self.cl.sys.create_or_update_policy(
            name=role+'_policy',
            policy=policy_str,
        )


    def get_token(self, role, jwt):
        response = self.cl.auth.jwt.jwt_login(role=role, jwt=jwt)
        if 'auth' in response and 'client_token' in response['auth']:
           return response['auth']['client_token']
        return None

    def list_url_labels(self):
        headers = {"X-Vault-Token" : self.cl.token}
        vlturl = self.vault_url + '/v1/allusers_secrets/data/url_label?list=true'
        resp = requests.get(url=vlturl, verify=False, headers=headers)
        if 'data' in resp.json():
            labels = resp.json()['data']['keys']
            return labels
        return []    

    def add_credentials(self, role, label, username, typ, ssh_key_file_name=None, password=None, conn_type='ssh'):
        if typ == "ssh_key_file" or typ.lower() == 's':
            
            fh = open(ssh_key_file_name, "r")
            ssh_key = fh.read()
            self.cl.secrets.kv.v2.create_or_update_secret(
                path=label,
                mount_point=role + '_secrets',
                secret=dict(username=username, ssh_key=ssh_key, conn_type=conn_type)
            )
            return True
        elif typ == "password" or typ.lower() == 'p':

            self.cl.secrets.kv.v2.create_or_update_secret(
                path=label,
                mount_point=role + '_secrets',
                secret=dict(username=username, password=password, conn_type=conn_type)
            )
            return True
            
    def delete_credentials(self, role, label):
        self.cl.secrets.kv.v2.delete_latest_version_of_secret(
            path = label,
            mount_point = role+'_secrets'
        )
        return True

    def list_credentials(self, role):
        headers = {"X-Vault-Token" : self.cl.token}
        url = self.vault_url + '/v1/' + role + '_secrets/data?list=true'
        resp = requests.get(url=url, verify=False, headers=headers)
        if 'data' in resp.json():
            creds = resp.json()['data']['keys']
            return creds
        return []

    def get_credentials(self, role, cred_label):
        try:
           credentials = self.cl.secrets.kv.v2.read_secret_version(
               path=cred_label,
               mount_point=role + '_secrets'
           ) 
           if 'data' in credentials and 'data' in credentials['data']:
              return credentials['data']['data']
           return {}
        except:
           return {}

    def add_ip_addr(self, ip_addresses, cred_label):
    
        #TODO: check sanity of the cred_label, ensure it is valid
        for ip_addr in ip_addresses:
            if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_addr):
                print("ERROR: Skipping bad IP address: ", ip_addr, file=sys.stderr)
                sys.stderr.flush()
                continue
            lbl = self.get_ip_addr(ip_addr)
            if not lbl:
                enc_ip_addr = base64.b64encode(ip_addr.encode())
                self.cl.secrets.kv.v2.create_or_update_secret(
                   path='ip_group/' + enc_ip_addr.decode(),
                   mount_point = 'allusers_secrets',
                   secret = dict(group=[cred_label])
                )
            else:
               #The IP address already exists. Let's append the new cred_label to it
               lbl.append(cred_label)
               enc_ip_addr = base64.b64encode(ip_addr.encode())
               self.cl.secrets.kv.v2.create_or_update_secret(
                   path='ip_group/' + enc_ip_addr.decode(),
                   mount_point = 'allusers_secrets',
                   secret = dict(group=lbl)
               )

    def delete_ip_addr(self, ip_addresses):
        for ip_addr in ip_addresses:
            if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_addr):
                print("ERROR: Skipping bad IP address: ", ip_addr, file=sys.stderr)
                sys.stderr.flush()
                continue

            enc_ip_addr = base64.b64encode(ip_addr.encode())
            self.cl.secrets.kv.v2.delete_latest_version_of_secret(
                path='ip_group/' + enc_ip_addr.decode(),
                mount_point = 'allusers_secrets'
            )

    def list_ip_addrs(self):
        headers = {"X-Vault-Token" : self.cl.token}
        url = self.vault_url + '/v1/allusers_secrets/data/ip_group?list=true'
        resp = requests.get(url=url, verify=False, headers=headers)
        if 'data' in resp.json():
            enc_ip_addrs = resp.json()['data']['keys']
            ip_addrs = [base64.b64decode(x).decode() for x in enc_ip_addrs]
            return ip_addrs
        else:
            return []

    def add_inventory(self, filename):
        fh = open(filename, "r")
        inventory = fh.read()
        items = inventory.split('\n')

        host_groups = self.list_host_groups()

        for line in items:
            if not line:
                continue
            parts = line.split(',')
            hostname = ""
            ip_addr = ""
            cred_label = ""
            group_label = ""
            if len(parts) == 4:
                #Expect: hostname, IP_addr, credential_label
                hostname = parts[0].strip()
                ip_addr = parts[1].strip()
                cred_label = parts[2].strip()
                group_label = parts[3].strip()
            elif len(parts) == 3:
                #Expect: hostname, IP_addr, credential_label
                hostname = parts[0].strip()
                ip_addr = parts[1].strip()
                cred_label = parts[2].strip()
            elif len(parts) == 2:
                #Expect IP_addr, credential_label
                ip_addr = parts[0].strip()
                cred_label = parts[1].strip()

            self.add_ip_addr([ip_addr], cred_label)
            self.add_ip_label(ip_addr, hostname)
            if group_label:
                if group_label not in host_groups:
                    #This group doesn't exist yet. Create one
                    self.create_host_group(group_label, [hostname])
                else:
                    #Group already exists, just add the host to it
                    self.add_hosts_to_group(group_label, hostname)

    def get_ip_addr(self, ip_addr):        
        enc_ip_addr = base64.b64encode(ip_addr.encode())
        try:
           resp = self.cl.secrets.kv.v2.read_secret_version(path='ip_group/'+enc_ip_addr.decode(), mount_point='allusers_secrets')
           if 'data' in resp and 'data' in resp['data'] and 'group' in resp['data']['data']:
              return resp['data']['data']['group']
        except:
           return None
        return None

    def list_host_groups(self):
        headers = {"X-Vault-Token" : self.cl.token}
        url = self.vault_url + '/v1/allusers_secrets/data/group_to_hosts?list=true'
        resp = requests.get(url=url, verify=False, headers=headers)
        if 'data' in resp.json():
            group_labels = resp.json()['data']['keys']
            return group_labels
        return []    

    def add_hosts_to_group(self, group_label, hosts):
            resp = self.cl.secrets.kv.v2.read_secret_version(
                path='group_to_hosts/' + group_label,
                mount_point='allusers_secrets'
            )
            cur_hosts = resp['data']['data']
            host_list_tmp = hosts
            if type(hosts) is str:
                if "," in hosts:
                    host_list_tmp = hosts.split(',')
                else:
                    host_list_tmp = hosts.split(r'\s')

            host_list = [x.strip() for x in host_list_tmp]
        
            cur_hosts.extend(host_list)
    
            new_host_list = list(set(cur_hosts))
            self.cl.secrets.kv.v2.create_or_update_secret(
                path='group_to_hosts/' + group_label,
                mount_point='allusers_secrets',
                secret=new_host_list
            )
            return new_host_list

    def create_host_group(self, group_label, host_list):
        self.cl.secrets.kv.v2.create_or_update_secret(
            path='group_to_hosts/' + group_label,
            mount_point='allusers_secrets',
            secret=host_list
        )
        #TODO: Error check
        return True

    def delete_host_group(self, group_label):        
        self.cl.secrets.kv.v2.delete_latest_version_of_secret(
            path='group_to_hosts/' + group_label,
            mount_point='allusers_secrets'
        )
        #TODO: Error check
        return True
            
    def get_host_group(self, group_label):
        resp = self.cl.secrets.kv.v2.read_secret_version(
            path='group_to_hosts/' + group_label,
            mount_point='allusers_secrets'
        )
        if 'data' in resp and 'data' in resp['data']:
           return resp['data']['data']
        return []

    def delete_hosts_from_group(self, group_label, host_list):
        resp = self.cl.secrets.kv.v2.read_secret_version(
            path='group_to_hosts/' + group_label,
            mount_point='allusers_secrets'
        )
        cur_hosts = set(resp['data']['data'])


        host_list_set = set(host_list)
        new_host_list_tmp = cur_hosts - host_list_set
        new_host_list = list(new_host_list_tmp)
        self.cl.secrets.kv.v2.create_or_update_secret(
            path='group_to_hosts/' + group_label,
            mount_point='allusers_secrets',
            secret=new_host_list
        )
        return True


    def list_ip_labels(self):
        headers = {"X-Vault-Token" : self.cl.token}
        url = self.vault_url + '/v1/allusers_secrets/data/ip_alias?list=true'
        resp = requests.get(url=url, verify=False, headers=headers)
        if 'data' in resp.json():
            labels = resp.json()['data']['keys']
            return labels
        return []    

    def add_ip_label(self, ip_addr, label):
        self.cl.secrets.kv.v2.create_or_update_secret(
            path='ip_alias/' + label,
            mount_point='allusers_secrets',
            secret=dict(encoded=True, ip=ip_addr)
        )
        return True

    def delete_ip_label(self, label):
        resp = self.cl.secrets.kv.v2.read_secret_version(
            path='ip_alias/'+label,
            mount_point='allusers_secrets'
        )
        ip_addr = resp['data']['data']['ip']
        self.cl.secrets.kv.v2.delete_latest_version_of_secret(
            path='ip_alias/' + label,
            mount_point='allusers_secrets'
        )
        return True

    def get_ip_label(self, label):
        try:
           resp = self.cl.secrets.kv.v2.read_secret_version(
               path='ip_alias/'+label,
               mount_point='allusers_secrets'
           )
           ip_addr = resp['data']['data']['ip']
           return ip_addr
        except:
           return None

    def list_ip_label_regex(self):
        try:
           resp = self.cl.secrets.kv.v2.read_secret_version(
               path='ip_alias_regex',
               mount_point='allusers_secrets'
           )
           regex_list = resp['data']['data']
           return regex_list
        except Exception as e:
           print("Got exception: ", str(e), file=sys.stderr)
           sys.stderr.flush()
           return []


    def add_ip_label_regex(self, ip_addr, regex):
        regex_list = self.list_ip_label_regex()
        regex_list.append({"encoded" : True, "ip" : ip_addr, "regex" : regex})
        self.cl.secrets.kv.v2.create_or_update_secret(
            path='ip_alias_regex',
            mount_point='allusers_secrets',
            secret=regex_list
        )
        return True

    def delete_ip_label_regex(self, regex):
        regex_list = self.list_ip_label_regex()
        new_regex_list = [x for x in regex_list if x['regex'] != regex]
        self.cl.secrets.kv.v2.create_or_update_secret(
            path='ip_alias_regex',
            mount_point='allusers_secrets',
            secret=new_regex_list
        )
        return True


    def add_url_label(self, url, label):
        if not (url.startswith('http://') or url.startswith('https://')):
            return False
        else:
            self.cl.secrets.kv.v2.create_or_update_secret(
                path='url_label/' + label,
                mount_point='allusers_secrets',
                secret=dict(url=url)
            )
            return True

    def delete_url_label(self, label):
        resp = self.cl.secrets.kv.v2.read_secret_version(
            path='url_label/'+label,
            mount_point='allusers_secrets'
        )
        url = resp['data']['data']['url']
        self.cl.secrets.kv.v2.delete_latest_version_of_secret(
            path='url_label/' + label,
            mount_point='allusers_secrets'
        )
        #TODO error checks
        return True

    def get_url_label(self, label):
        resp = self.cl.secrets.kv.v2.read_secret_version(
            path='url_label/'+label,
            mount_point='allusers_secrets'
        )
        if 'data' in resp and 'data' in resp['data'] and 'url' in resp['data']['data']:
           return resp['data']['data']['url']
        return None

    def add_user(self, uname, role):
        resp = self.cl.secrets.kv.v2.create_or_update_secret(
            path='user_roles/' + uname,
            mount_point = 'allusers_secrets',
            secret=dict(role=role)
        )
        return True

    def delete_user(self, uname):
        resp = self.cl.secrets.kv.v2.delete_latest_version_of_secret(
            path='user_roles/' + uname,
            mount_point = 'allusers_secrets'
        )
        return True

    def list_users(self):
        headers = {"X-Vault-Token" : self.cl.token}
        url = self.vault_url + '/v1/allusers_secrets/data/user_roles?list=true'
        resp = requests.get(url=url, verify=False, headers=headers)
        if 'data' in resp.json():
            users = resp.json()['data']['keys']
            return users
        return []

    def get_user(self, uname):
        try:
           resp = self.cl.secrets.kv.v2.read_secret_version(
               path='user_roles/' + uname,
               mount_point = 'allusers_secrets'
           )
           if 'data' in resp and 'data' in resp['data']:
              return resp['data']['data']
           return {}
        except:
           return {}
