
import typer
from dagcli.vault.root import app, ensure_mandatory
from dagcli.vault import roles
from dagcli.vault import credentials

app.add_typer(roles.app, name="roles", callback=ensure_mandatory)
app.add_typer(credentials.app, name="credentials", callback=ensure_mandatory)
# from dagcli import ipaddrs
# app.add_typer(ipaddrs.app, name="ipaddrs", callback=ensure_access_token)
# from dagcli import iplabels
# app.add_typer(iplabels.app, name="iplabels", callback=ensure_access_token)
# from dagcli import hostgroups
# app.add_typer(hostgroups.app, name="hostgroups", callback=ensure_access_token)
# from dagcli import urllabels
# app.add_typer(urllabels.app, name="urllabels", callback=ensure_access_token)

if __name__ == "__main__":
    app()
