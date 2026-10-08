"""
Plugin: table of the work items returned by a saved Azure DevOps (TFS) query.

The columns of the table are the columns of the query, in the same order; the rows are its work items. Written with the
standard library only (urllib), because the backend does not install requests.

Configuration (environment variables of the backend):
- AZURE_DEVOPS_URL: collection URL, e.g. http://your-server:8080/tfs/DefaultCollection (required);
- AZURE_DEVOPS_TOKEN: personal access token used when the Token field is left empty (optional).
"""
import base64
import json
import os
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from src.plugins import IPlugin, PluginError, PluginParameter

API_VERSION = "5.0"
# Maximum number of work items per workitemsbatch request (limit of the API).
BATCH_SIZE = 200
TIMEOUT_SECONDS = 60
QUERY_ID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


class AzureDevOpsTablePlugin(IPlugin):
    id = "azure-devops-query"
    name = "Azure DevOps query"
    description = "Table of the work items of a saved Azure DevOps (TFS) query, with the query's columns."
    version = "1.0"

    def parameters(self, content_type):
        has_default_token = bool(os.getenv("AZURE_DEVOPS_TOKEN"))
        return [
            PluginParameter(
                "token", "Azure token", type="password", required=not has_default_token,
                # The server token (AZURE_DEVOPS_TOKEN) is never sent to the browser: the empty field uses it.
                placeholder="Using the server token" if has_default_token else "",
                help="Personal access token with the Work Items (read) scope."
                     + (" Leave it empty to use the token configured on the server." if has_default_token else ""),
            ),
            PluginParameter(
                "query", "Query", required=True,
                help="ID of the saved query (e.g. 1a2b3c4d-...) or its link copied from Azure DevOps.",
            ),
            PluginParameter(
                "project", "Project Area", required=True,
                help="Project of the query, as named in Azure DevOps.",
            ),
        ]

    def compile_table(self, values):
        token = values["token"] or os.getenv("AZURE_DEVOPS_TOKEN")
        if not token:
            raise PluginError("Write the Azure token.")
        match = QUERY_ID.search(values["query"])
        if not match:
            raise PluginError("The query must be the ID of a saved query (or a link containing it).")
        url = os.getenv("AZURE_DEVOPS_URL", "").strip()
        if not url:
            raise PluginError("The server has no Azure DevOps URL: set AZURE_DEVOPS_URL in its .env file.")
        client = _AzureDevOpsClient(url, token)
        project = values["project"].strip()
        query_id = match.group(0)
        result = client.run_query(project, query_id)
        columns = result.get("columns") or [{"referenceName": "System.Id", "name": "ID"}]
        fields = [column["referenceName"] for column in columns]
        ids = _work_item_ids(result)
        if not ids:
            raise PluginError("The query did not return any work item.")
        items = client.work_items(project, ids, fields)

        rows = [[column.get("name") or column["referenceName"] for column in columns]]
        for work_item_id in ids:
            item_fields = items.get(work_item_id)
            if item_fields is not None:
                rows.append([_cell(item_fields.get(field)) for field in fields])
        return self.table(rows, header=True, caption=client.query_name(project, query_id) or "")


class _AzureDevOpsClient:
    """Calls to the Azure DevOps REST API (version 5.0, also TFS 2019)."""

    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip("/")
        credentials = base64.b64encode(f":{token}".encode()).decode("ascii")
        self.headers = {"Authorization": f"Basic {credentials}", "Content-Type": "application/json",
                        "Accept": "application/json"}

    def run_query(self, project, query_id):
        """Result of the saved query (WIQL by ID): columns and work items."""
        return self._request("GET", f"{_path(project)}/_apis/wit/wiql/{query_id}?api-version={API_VERSION}")

    def query_name(self, project, query_id):
        """Name of the saved query, used as caption; None if it cannot be read."""
        try:
            return self._request("GET", f"{_path(project)}/_apis/wit/queries/{query_id}?api-version={API_VERSION}").get("name")
        except PluginError:
            return None

    def work_items(self, project, ids, fields):
        """Fields of the work items by ID, read in batches of BATCH_SIZE; deleted or hidden items are skipped."""
        result = {}
        url = f"{_path(project)}/_apis/wit/workitemsbatch?api-version={API_VERSION}"
        for start in range(0, len(ids), BATCH_SIZE):
            body = {"ids": ids[start:start + BATCH_SIZE], "fields": fields, "errorPolicy": "omit"}
            for item in self._request("POST", url, body).get("value", []):
                if item:
                    result[item["id"]] = item.get("fields", {})
        return result

    def _request(self, method, path, body=None):
        """JSON answer of the API; network and HTTP errors become PluginError with a readable message."""
        data = json.dumps(body).encode() if body is not None else None
        request = Request(f"{self.base_url}/{path}", data=data, headers=self.headers, method=method)
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in (401, 203):
                raise PluginError("Azure DevOps refused the token: check that it is valid and not expired.") from error
            if error.code == 404:
                raise PluginError("Query or project not found: check the query ID and the Project Area.") from error
            raise PluginError(f"Azure DevOps answered {error.code}: {_error_message(error)}") from error
        except URLError as error:
            if isinstance(error.reason, socket.gaierror):
                host = urlsplit(self.base_url).hostname
                raise PluginError(
                    f"The server running Nocument cannot resolve the host name \"{host}\". Set AZURE_DEVOPS_URL with "
                    "a name or IP address it can reach (e.g. its fully qualified name), or run "
                    "Nocument inside the company network."
                ) from error
            raise PluginError(f"Cannot reach Azure DevOps at {self.base_url}: {error.reason}") from error
        except TimeoutError as error:
            raise PluginError(f"Azure DevOps at {self.base_url} did not answer within {TIMEOUT_SECONDS} seconds.") from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            # A login page instead of JSON usually means the token was not accepted.
            raise PluginError("Azure DevOps did not answer with data: check the token and the server URL.") from error


def _path(project):
    """Project name in a URL (it can contain spaces, e.g. "My Project")."""
    return quote(project, safe="")


def _work_item_ids(result):
    """IDs of the query result in order: flat queries (workItems) and tree or link queries (workItemRelations)."""
    if result.get("workItems"):
        return [item["id"] for item in result["workItems"]]
    ids = []
    for relation in result.get("workItemRelations") or []:
        for end in (relation.get("source"), relation.get("target")):
            if end and end["id"] not in ids:
                ids.append(end["id"])
    return ids


def _cell(value):
    """Text of a field: people by name, whole numbers without decimals, dates as YYYY-MM-DD, nothing as empty."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("displayName") or value.get("uniqueName") or "")
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}T", value):
        return value[:10]
    return str(value)


def _error_message(error):
    """Message of an API error answer, if it has one."""
    try:
        return json.loads(error.read().decode("utf-8")).get("message", error.reason)
    except Exception:
        return error.reason
