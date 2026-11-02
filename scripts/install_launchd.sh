#!/bin/sh
set -eu

label="com.fosghen.agent-retro"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(dirname "$script_dir")
python=$(command -v python3)
target_dir="$HOME/Library/LaunchAgents"
log_dir="$HOME/.codex/logs"
target="$target_dir/$label.plist"

mkdir -p "$target_dir" "$log_dir"
sed \
  -e "s|__PYTHON__|$python|g" \
  -e "s|__SCRIPT__|$repo_dir/scripts/daily_codex_retro.py|g" \
  -e "s|__LOG_DIR__|$log_dir|g" \
  "$repo_dir/launchd/$label.plist.in" > "$target"

plutil -lint "$target"
launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$target"
echo "Installed $label; it runs daily at 09:00 local time."
