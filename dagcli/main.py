import sys, json
from dagcli import swaggerutils

from pkg_resources import resource_stream
resstream = resource_stream("dagcli", "schemas/swagger.json")


cli = swaggerutils.make_cli(json.load(resstream))

# Global flag definitions for our specific CLI
cli.global_flag_defs = [
    swaggerutils.FlagDef("AuthToken",
            help_text="Auth token for accessing the API gateway",
            valtype=str,
            required=True,
            envvars=["DagKnowsAuthToken"]),
    swaggerutils.FlagDef("ReqRouterHost",
            help_text="Request router host",
            valtype=str,
            default_value="https://demo.dagknows.com:8443",
            envvars=["DagKnowsReqRouterHost"]),
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
]

if __name__ == "__main__":
    cli()
