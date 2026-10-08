# Azure DevOps query

Creates a table with the work items returned by a **saved query** of Azure DevOps (or Team Foundation Server): the
columns of the table are the columns of the query, in the same order.

## Use

In the Builder, in *Add new content* and in the Compiler choose **Table**, open **From plugin**, choose
*Azure DevOps query* and fill in:

- **Token**: a personal access token with the *Work Items (read)* scope. Leave it empty to use the token configured on
  the server (`AZURE_DEVOPS_TOKEN`).
- **Query**: the id of the saved query (e.g. `1a2b3c4d-...`) or its link copied from Azure DevOps.
- **Project Area**: the project of the query (e.g. `MyProject`).

## Interface

The plugin page (**Plugins → Installed plugins → Azure DevOps query**) runs a query and previews the table. The
queries you run are listed in **Recent queries** (saved in this browser), to run them again with one click. The
token is never saved: type it each time, or configure it on the server.

## Configuration (server)

Environment variables of the backend (see Settings → Environment variables):

| Variable              | Meaning                                                        |
| --------------------- | -------------------------------------------------------------- |
| `AZURE_DEVOPS_URL`    | URL of the collection, e.g. `http://your-server:8080/tfs/DefaultCollection` (required) |
| `AZURE_DEVOPS_TOKEN`  | token used when the Token field is empty (a secret: set it only in `.env`)   |

## Files

- `plugin.py`: the plugin, using the Azure DevOps REST API with the standard library only (`urllib`).
- `ui.svelte`: the query runner with the recent queries.
- `README.md`: this guide.
