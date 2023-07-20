import typer
from dagcli.configs import DagKnowsConfig
import json, os, sys
from dagcli.vault.lib import dagknows_proxy_vault

app = typer.Typer(pretty_exceptions_show_locals=False)

@app.callback()
def common_params(ctx: typer.Context,
                  vault_url: str = typer.Option("https://localhost:8200", envvar="DagKnowsVaultUrl", help="URL where the vault is operating"),
                  vault_keys_folder: str = typer.Option("src/keys", envvar="DagKnowsVaultKeysFolder", help="Folder where keys used by credentials are stored"),
                  vault_unseal_tokens_file: typer.FileText= typer.Option(None, envvar='DagKnowsVaultUnsealKeysFile', help='File contain tokens to unseal vault')):
    ctx.obj.data["vault_url"] = vault_url.strip()
    ctx.obj.data["vault_keys_folder"] = vault_keys_folder.strip()
    ctx.obj.data["vault_unseal_tokens"] = json.load(vault_unseal_tokens_file.read())
    ctx.obj.data["vault_api"] = dagknows_proxy_vault(vault_url, ctx.obj.data["vault_unseal_tokens"]["root_token"])

def ensure_mandatory(ctx: typer.Context):
    if not ctx.obj.data.get("vault_url", "") or \
       not ctx.obj.data.get("vault_keys_folder", "") or \
       not ctx.obj.data.get("vault_unseal_tokens", None):
        print("Command: ", ctx.command_path)
        ctx.fail(f"Vault command params missing")

