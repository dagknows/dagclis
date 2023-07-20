
import typer
from dagcli.vault.root import app, ensure_mandatory

from dagcli.vault import users
app.add_typer(users.app, name="users", callback=ensure_mandatory)

from dagcli.vault import roles
app.add_typer(roles.app, name="roles", callback=ensure_mandatory)

from dagcli.vault import credentials
app.add_typer(credentials.app, name="credentials", callback=ensure_mandatory)

from dagcli.vault import ips
app.add_typer(ips.app, name="ips", callback=ensure_mandatory)

from dagcli.vault import urls
app.add_typer(urls.app, name="urls", callback=ensure_mandatory)

from dagcli.vault import hostgroups
app.add_typer(hostgroups.app, name="hostgroups", callback=ensure_mandatory)

if __name__ == "__main__":
    app()
