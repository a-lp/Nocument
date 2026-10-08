@echo off
setlocal

set "ROOT=%~dp0"
if exist "%ROOT%.venv\Scripts\python.exe" (
    set "PYTHON=%ROOT%.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

rem Port of the development backend, also used by the Vite /api proxy (default 5000).
if not defined NOCUMENT_BACKEND_PORT set "NOCUMENT_BACKEND_PORT=5000"
start "Nocument Backend" /D "%ROOT%" cmd /k "pip install -r requirements.txt && %PYTHON% -m src.app"
start "Nocument Frontend" /D "%ROOT%web" cmd /k "npm install & npm run dev"

endlocal
