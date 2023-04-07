our cmd tructure:

```
GET /v1/dags    -   cli v1 dags get
GET /v1/dags/id -   cli v1 dags get <dagid>
// We need to be smart about whether ids should be a query param or a "list"
GET /v1/dags:batchGet -   cli v1 dags batchget id1 id2 id3 ...
DELETE /v1/dags/id -   cli v1 dags delete <dagid>
POST /v1/dags   -   cli v1 dags create <payload_flags>
PATCH /v1/dags  -   cli v1 dags patch  <dagid> <payload_flags>

POST /v1/dags/dagid/execs   -   Create a new dag exec
                -   cli v1 dags execs get <dagid>
GET /v1/execs/id   -   Get info about an exec
                -   cli v1 execs get <dagid>

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
