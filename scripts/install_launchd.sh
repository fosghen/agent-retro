#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(dirname "$script_dir")
action=${1:-install}
exec "$repo_dir/.venv/bin/python" "$repo_dir/scripts/manage_install.py" "$action"
