# DagKnows Tools

Welcome to the CLI tools for DagKnows.  With this you can manage all your dags, nodes, executions and sessions without ever leaving the comfort of your terminal.

## Getting Started

Install the cli with:

```
pip install dagknows
```

## Setup your account

DagKnows uses the auth token associated with your organization and account.  You can either use an existing token or login and create a new one.

To use an existing token simply do:

```
dk init --access-token <EXISTING_ACCESS_TOKEN>
```

You can also login to get a fresh one:

```
dk login ORG
```

Here you will be prompted for your org's username and password.

## Get going

For a full list of commands and help descriptions do:

```
dk --help
```
