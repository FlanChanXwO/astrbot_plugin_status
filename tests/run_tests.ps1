$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pluginDir = Split-Path -Parent $scriptDir
Set-Location $pluginDir

uv run ruff check main.py core tests
uv run ruff format --check main.py core tests
python -m compileall main.py core tests
pytest tests/ -v -o cache_dir=/private/tmp/astrbot_plugin_status_pytest_cache
