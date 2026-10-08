# Configuration

Nocument is configured with environment variables. All of them, with their defaults, are listed in `.env.example`: copy it to `.env` and uncomment the ones to change.

- **Docker Compose** reads `.env` both for the values of the compose files (ports, gunicorn workers...) and as variables of the app containers; the variables set under `environment` in the compose files (e.g. `MONGODB_URI`) win over it.
- **Locally** the backend does not read `.env` by itself: load it in the shell first (`set -a; . ./.env; set +a; python -m src.app`).
- **Settings → Environment variables** in the web app shows every variable, marked *Set* or *Default*; secret values are never sent to the browser (see [Settings](Settings.md)).

## Docker Compose

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `NOCUMENT_PORT` | Port of the web app in production (compose.yaml). | `8080` |
| `NOCUMENT_DEV_PORT` | Port of the web app in development (compose.dev.yaml, Vite dev server). | `5173` |
| `NOCUMENT_DEV_ALLOWED_HOSTS` | Host names, separated by commas, the development web app answers to besides localhost. | — |
| `MONGODB_DEV_PORT` | Port of MongoDB published on 127.0.0.1 in development. | `27017` |
| `GUNICORN_WORKERS` | Number of gunicorn workers (production image only). | `2` |

## Content blocks database

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `MONGODB_URI` | MongoDB URI: when set the content blocks are saved in MongoDB, otherwise in the SQLite file. | — |
| `MONGODB_DATABASE` | MongoDB database of the content blocks (only with MONGODB_URI). | `nocument` |
| `NOCUMENT_DATABASE` | SQLite file of the content blocks, used when MONGODB_URI is not set. | `instance/nocument.sqlite3` |
| `NOCUMENT_STORAGE` | "memory" keeps the content blocks in memory: they are lost when the server restarts. | — |

## Server settings

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `NOCUMENT_SETTINGS` | JSON file of the settings chosen in this page. | `instance/settings.json` |
| `NOCUMENT_BACKEND_PORT` | Port of the development backend (python -m src.app); the Vite /api proxy uses the same one. | `5000` |
| `NOCUMENT_BACKEND_HOST` | Address the development backend listens on. | `127.0.0.1` |
| `NOCUMENT_COMMIT` | Git commit of the code, shown in Settings → Version; by default read from git (set by the Docker build). | found automatically |
| `NOCUMENT_COMMIT_DATE` | Date of that commit (ISO 8601); by default read from git. | found automatically |

## Logging

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `NOCUMENT_LOG_LEVEL` | Minimum level of the log: DEBUG, INFO, WARNING or ERROR. | `INFO` |
| `NOCUMENT_LOG_LEVELS` | Levels of single loggers, comma separated (e.g. werkzeug=WARNING). | — |
| `NOCUMENT_LOG_FILE` | Log file, rotated by size; empty to log only to the console. | `instance/logs/nocument.log` |
| `NOCUMENT_LOG_MAX_BYTES` | Size of the log file before rotation, in bytes. | `5242880` |
| `NOCUMENT_LOG_BACKUPS` | Number of old log files kept. | `5` |

## PDF renderers (LibreOffice)

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `SOFFICE_PATH` | LibreOffice executable; by default searched in the PATH and in the standard folders. | found automatically |
| `SOFFICE_TIMEOUT` | Timeout of a LibreOffice conversion, in seconds. | `120` |
| `UNO_PYTHON` | Python with LibreOffice's uno module, used to update the tables of contents; by default searched automatically. | found automatically |

## Plugins

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `NOCUMENT_PLUGINS_DIR` | Folder of the plugin scripts. | `plugins` |
| `NOCUMENT_PLUGIN_UPLOAD` | "false" forbids installing and removing plugins from the web app. | `true` |

## Plugin: Azure DevOps query

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `AZURE_DEVOPS_URL` | URL of the Azure DevOps / TFS collection, required by the plugin. | — |
| `AZURE_DEVOPS_TOKEN` | Personal access token used when the Token field of the plugin is left empty. Secret: set it only in `.env`. | — |
