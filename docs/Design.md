
# API2Cli 

## Background

There are plenty of APIs around.   And they come in gRPC and/or REST flavors.   Even better gRPC -> OpenAPI means we have a Rest decorator on top of a gRPC service as well as a swagger spec to boot.

Standard tools exist for interacting with these services - gRPC_cli for gRPC services, curl/httpie/postman for Rest services.

These tools are fantastic and get the job done.  However an application/service specific CLI still has some benefits:

* Focus/Context around the service instead of thinking about generic HTTP (or protocol specific) 
* Integrating general "service access" commands into a larger application specific CLI.
* Grouping different "product" level APIs into a larger tool
* Shell completion - It is quite a burden for generic API tools like Curl/Postman/Httpie on their to use a API spec (eg swagger spec or even HATEOS) to provide suggests in realtime (not withstanding latency constraints of any dynamic fetches).
* Branding!

Given these constraints, a way to convert an API spec into a CLI is beneficial and is provided in this tool.

## Requirements

1. Users provide an API spec (eg gRPC service specs, Swagger Specs etc)
2. Users *may* provide hints on what the command hierarchy would be for each reques in the service spec - eg `DELETE /v1/orders/orderid` => `cli delete orders orderid` or `cli orders orderid delete`
3. In the absence of hints, users should have "templates" to create command hierarchies (eg aws style, k8s style, gcloud style etc).
4. Customization of request bodies from different soruces, eg input files, json strings, field paths or even environment variables.

## Design

Some abstractions that can simplify our thought process:

1. API services expose logical endpoints for operations.

An endpoint is (or can be) a collection of logical services that provides various API methods (or operations) for servicing requests from users.  Each request/operation contains:
    * Request name          - Name of the request (eg GetWidgets, CreateOrder, etc)
    * Request parameters    - All the parameters the request needs.  These could be simple fields like strings, numbers or complex hierarchical items (like JSON objects).
    * Destination           - Where is the server/service running that can serve this request (eg Widget service in the prod EU region, Order service in staging at NA region, etc)
    * Request metadata      - Any other info needed for requests in general (auth information, locale info etc).

Note that request metadata could be part of request parameters too but when the request is agnostic of this, metadata would be the suitable choice for holding this.  Similarly the destination itself could be treated a metadata parameter but it is called out here for generality.

2. API clients are request transformers.

API clients take in requests in one format, transform them and send them to the server in a format the server accepts.  In the case, a CLI:

* Accepts command line arguments
* Builds a command line request hierarchy
* Executes the handler associated with parts of a command
* Command handlers use the arguments and flags passed to build up different parts of the service request (name, parameters, destination, metadata).
* Finally the fully assembled request is sent to/invovked on the service

## Command Line request model

Our command line apps can be represented via a command line model.  Note that there are several models and conventions (Windows convention, POSIX convention etc).

```
record Command {
    // Name of the command
    name: string

    // Sub commands
    subcommands: Map[string, Command]

    // Options accepted by this command
    options: Map[string, Option]

    // args passed to the command
    args: List[Arg]
}

record Option {
    // Name of the option
    // can be "-{name}" or "--{name}"
    name: string

    help_text: string

    default_value = None

    // Minimum number of arguments required
    minargs = 0

    // Max number of arguments expected (-1 => no limit)
    maxargs = 0
}

record Arg {
    argtype: enum { STRING | NUMBER | IDENT | KVPAIR }
    argval: any
}
```

aws ec2 describe-instances --help


The hardest part of this parsing our command line tokens are parsed avoiding any ambiguities while calling the right 

```
How do we assemble/parse a series of "tokens" on the command line to build an AST that is representative of our logical request in #2?
```

We canthink of this AST as simply a different representation of the request that is accepted by the service.

Once this parsing is performed the transforming of a Coma



There could be other bits 
1. All specs expose a number of "endpoints" where users have a path (to indicate the request) and specify the parameters to be sent as part of this request.
2. The endpoi

## Proposal
Today the way to interface with a s
# Goal of our swagger2cli (this should also work eventually on gRPC files) tool is:
# 1. Represent a CLI structure for each http/api request
# 2. If a structure is not specified - create one based on templates
# 3. What does structure here mean?
our cmd tructure:

```
GET /v1/dags    -   cli v1 dags get
GET /v1/dags/{id} -   cli v1 dags get <id>
// We need to be smart about whether ids should be a query param or a "list"
GET /v1/dags:batchGet -   cli v1 dags batchget id1 id2 id3 ...
DELETE /v1/dags/id -   cli v1 dags delete <dagid>
POST /v1/dags   -   cli v1 dags create <payload_flags>
PATCH /v1/dags  -   cli v1 dags patch  <dagid> <payload_flags>

POST /v1/dags/{dagid}/execs   -   Create a new dag exec
                -   cli v1 dags execs get <dagid>
GET /v1/execs/{id}   -   Get info about an exec
                -   cli v1 execs get <id>

// Same with sessions
GET /v1/sessions    -   cli v1 sessions get
GET /v1/sessions/id -   cli v1 sessions get <sessionid>
// We need to be smart about whether ids should be a query param or a "list"
GET /v1/sessions:batchGet -   cli v1 sessions batchget id1 id2 id3 ...
DELETE /v1/sessions/id -   cli v1 sessions delete <sessionid>
POST /v1/sessions   -   cli v1 sessions create <payload_flags>
PATCH /v1/sessions  -   cli v1 sessions patch  <sessionid> <payload_flags>
```

So our idea is:

1. break path into parts:
2. static = filter(parts, if not param)
3. params = filter(parts, if param)
4. method = req.method

cmd = *static method *params

Advantages:
    - clean/consistent: resource first, command next, args then flags
Unambiguous:
    - method will always come after a "clean" trie path
      so method and param name confusion wont be there

How should we represent this in our Trie?
Our Trie path will be list(static) + method
method node will ALWAYS be the leaf!

How do we convert our body data flags/params?

Say if our body as 3 parameters (and this could also be nested).  At the leaf we can have a --json or --file param that says where the body should be loaded from and its schema should match.  For GET requests, we have an extra step to turn the body parameters into query params (lists become "," seprated i think).

We also want to specify "individual" fields, eg:

    field_path1=value1 fieldpath2=value2 etc.

So our convention is that --json or --file comes first and then individual values are patched by using these k=v entries

How should we do auth?
Since our app is just called from "main" we can prepopulate a context object with what ever is needed. - Need to look into to see if we can look at some of the header params (like DagKnowsHost and Token) from ENV (list), config file or just argument

How should the request be created?
* As each subcommand is visited - it sets the context object with "param" values
* Once all params are done - we construct the URL from all values set in the context
* this has one for setting the path and one for the query params (latter could be implicit if method does not allow a body)
* Load file, Load Json and patch with kv pairs
* sent http req from above

May need other params like "path prefix" eg if our api gw starts with /api/

## Thought Experiment

The convention above is good for removing ambiguities.

But if we ever wanted to do a more 'natural looking' form like:

```
GET /dags/{dagid}/  ->  dags {dagid} get 
GET /dags/          ->  dags get            (or dags list)
```

Then the {dagid} and "get" cause an ambiguity.   Here what we *may* want to think about is whether this can be turned to use a LL grammar.

So we might do something like:

```
CLI := Command | Command CLI

Command := Name Arg * Flags *

Arg := IDENT | Literal | KV_PAIR

Literal := NUMBER | QUOTED_STRING

KVPair := (IDENT | QUOTED_STRING) "=" Literal

Flag := "--"IDENT ( "=" VALUE ) ?
```

Applying this to our dags example, we could have:

```
    Cli := {"name": "dags",
            "args": [ "dagid" ],
            "flags": 
```

Which means we can have commands of the form:

```
cmd1 arg1 arg2 --arg1flag=1 --arg1flag2=2 arg5 subcommand2 subarg1 --subarg1flag1 ...
```

An ex

This grammar obviously is ambiguous, eg it could be parsed as:

```
cmd1 
    |-- arg1 arg2 --arg1flag1 --arg1flag2
    |-- arg5 subcommand2 subarg1 --subarg1flag1
```

This is not the right parse as what we really want is:

```
cmd1
    |-- arg1 arg2 --arg1flag1 --arg1flag2
    |-- arg5
    |-- subcommand2 subarg1 --subarg1flag1
```

We have this conflict because our argv parser doesnt konw if arg5 (if it is a subcommand) needs subcommand2 as its argument or does it need to stop.

In any cli builder we have the concept of nested commands anyway.  So we could let the "nested" list be a guide.

Here for cmd1 we would have done something like:

```
cmd1.add_nested("arg1", arg1_command)
cmd1.add_nested("arg5", arg5_command)
cmd1.add_nested("subcommand2", subcommand_command)

By virtual of this, cmd1 would know where the boundaries are. And demarcate its first child command until it seems a subcommand in its child list arg5

One problem is it is not clear if subcommand is a child of arg1 or of arg5.  As both these are valid options.  TBD
