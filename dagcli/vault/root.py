import typer
import json, os, sys
from dagcli.vault.lib import dagknows_proxy_vault

app = typer.Typer(pretty_exceptions_show_locals=False)

@app.callback()
def common_params(ctx: typer.Context,
                  vault_url: str = typer.Option("https://localhost:8200", envvar="DagKnowsVaultUrl", help="URL where the vault is operating"),
                  vault_keys_folder: str = typer.Option("src/keys", envvar="DagKnowsVaultKeysFolder", help="Folder where keys used by credentials are stored"),
                  vault_unseal_tokens_file: typer.FileText= typer.Option(None, envvar='DagKnowsVaultUnsealKeysFile', help='File contain tokens to unseal vault')):
    class MyCtx: pass
    ctx.obj = MyCtx()
    ctx.obj.vault_url = vault_url.strip()
    ctx.obj.vault_keys_folder = vault_keys_folder.strip()
    ctx.obj.vault_unseal_tokens = "INVALID"
    if vault_unseal_tokens_file:
        data = json.loads(vault_unseal_tokens_file.read())
        ctx.obj.vault_unseal_tokens = data["root_token"]
    ctx.obj.vault_api = dagknows_proxy_vault(vault_url, ctx.obj.vault_unseal_tokens)

def ensure_mandatory(ctx: typer.Context):
    if not ctx.obj.vault_url or \
       not ctx.obj.vault_keys_folder or \
       not ctx.obj.vault_unseal_tokens:
        print("Command: ", ctx.command_path)
        ctx.fail(f"Vault command params missing")


@app.command()
def reloadpkey(ctx: typer.Context,
               pkeypath: typer.FileText= typer.Option("src/keys/public_key.pem", help = "Path of the public_key.pem to configure vault with")):
    vapi = ctx.obj.vault_api
    pkey = pkeypath.read()
    vapi.set_jwt_auth_key(pkey)
