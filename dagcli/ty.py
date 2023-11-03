import typer
from dagcli.root import app, ensure_access_token
from dagcli import tasks
from dagcli import jobs
from dagcli import sessions
from dagcli import messages
from dagcli import tokens
from dagcli import proxy
from dagcli import config
from dagcli import forwarder

app.add_typer(sessions.app, name="sessions", callback=ensure_access_token)
app.add_typer(messages.app, name="messages", callback=ensure_access_token)
app.add_typer(tasks.app, name="tasks", callback=ensure_access_token)
app.add_typer(jobs.app, name="jobs", callback=ensure_access_token)
app.add_typer(tokens.app, name="tokens", callback=ensure_access_token)
app.add_typer(proxy.app, name="proxy", callback=ensure_access_token)
app.add_typer(config.app, name="config", callback=ensure_access_token)
app.add_typer(forwarder.app, name="forwarder")

if __name__ == "__main__":
    app()
