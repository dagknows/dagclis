import sys, json
from dagcli import swaggerutils

from pkg_resources import resource_stream
resstream = resource_stream("dagcli", "schemas/swagger.json")
cli = swaggerutils.make_cli(json.load(resstream))

if __name__ == "__main__":
    cli()
