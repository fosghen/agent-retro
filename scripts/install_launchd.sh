#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(dirname "$script_dir")
action=${1:-install}
cd "$repo_dir"
exec .venv/bin/python -m scripts.manage_install "$action"
