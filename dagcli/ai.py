
import typer
from enum import Enum
from dagcli.root import app, ensure_access_token
from dagcli import config

app = typer.Typer()

class LLMChoices(str, Enum):
    MISTRAL = "mistral"
    OPENAI = "openai"
    CLAUDE = "claude"
    LLAMA3 = "llama3"

@app.command()
def ai(ctx: typer.Context,
       session_id: str = typer.Argument(None, help = "IDs of the session to push messages to"),
       llm: LLMChoices = typer.Option(LLMChoices.OPENAI, help = "The LLM to be used remotely")):
    """ Start an AI session or connect to one. """
    print("Hello World")

if __name__ == "__main__":
    app()
