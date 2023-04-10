import sys, json
from dagcli import swaggerutils
from typing import List, Tuple

from pkg_resources import resource_stream
resstream = resource_stream("dagcli", "schemas/swagger.json")


cli = swaggerutils.make_cli(json.load(resstream))

def set_http_header(header_name):
    def flag_handler(ctx, flagdef, *values: List[Tuple[int, str]]):
        if "http" not in ctx.data:
            ctx.data["http"] = {}
        if "headers" not in ctx.data["http"]:
            ctx.data["http"]["headers"] = {}
        ctx.data["http"]["headers"][header_name] = values[0][1]
    return flag_handler

# Global flag definitions for our specific CLI
cli.add_flags(
    swaggerutils.FlagDef("AuthToken",
            help_text="Auth token for accessing the API gateway",
            valtype=str,
            required=True,
            envvars=["DagKnowsAuthToken"],
            handler=set_http_header("Authorization")),
    swaggerutils.FlagDef("ReqRouterHost",
            help_text="Request router host",
            valtype=str,
            default_value="https://demo.dagknows.com:8443",
            envvars=["DagKnowsReqRouterHost"],
            handler=set_http_header("DagKnowsReqRouterHost")),
    swaggerutils.FlagDef("ApiGatewayHost",
            help_text="API Gatway host fronting the new API",
            valtype=str,
            default_value="http://localhost:8080/api",
            envvars=["DagKnowsApiGatewayHost"]),
    swaggerutils.FlagDef("log_request",
            help_text="Whether to log API requests globally",
            valtype=str,
            default_value=True),
    swaggerutils.FlagDef("log_response",
            help_text="Whether to log API responses globally",
            valtype=str,
            default_value=True),
    swaggerutils.FlagDef("stdin",
                         help_text="Reads the base input from standard input before applying any field path specific overrides",
                         valtype=bool, required=False,
                         default_value=False,
                         val_on_missing=True),
    swaggerutils.FlagDef("json",
                         help_text="Reads base input from a json string before applying any field path specific overrides",
                         valtype="json", required=False,
                         default_value=None),
    swaggerutils.FlagDef("file",
                         help_text="Reads base input from an input file containing the JSON payload before applying any field path specific overrides",
                         valtype=str, required=False, default_value=None),
)

if __name__ == "__main__":
    cli()
