#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(dirname "$script_dir")
sandbox=$(mktemp -d)
test_home="$sandbox/user"
cleanup() { rm -rf "$sandbox"; }
trap cleanup 0 HUP INT TERM

mkdir -p "$sandbox/bin" "$test_home/.local/state/agent-retro"
cat > "$sandbox/bin/launchctl" <<'EOF'
#!/bin/sh
set -eu
printf '%s\n' "$*" >> "${AGENT_RETRO_LAUNCHCTL_LOG:?}"
EOF
chmod +x "$sandbox/bin/launchctl"
touch "$test_home/.local/state/agent-retro/proposals.sqlite3"

export HOME="$test_home"
export PATH="$sandbox/bin:$PATH"
export AGENT_RETRO_LAUNCHCTL_LOG="$sandbox/launchctl.log"
cd "$repo_dir"

./scripts/install_launchd.sh install
./scripts/install_launchd.sh install
test -L "$HOME/.codex/skills/agent-retro"
test -L "$HOME/.local/bin/agent-retro"
plist="$HOME/Library/LaunchAgents/com.fosghen.agent-retro.plist"
test -f "$plist"
plutil -lint "$plist" >/dev/null

./scripts/install_launchd.sh uninstall
test ! -e "$HOME/.codex/skills/agent-retro"
test ! -e "$HOME/.local/bin/agent-retro"
test ! -e "$plist"
test -f "$HOME/.local/state/agent-retro/proposals.sqlite3"
grep -q bootstrap "$AGENT_RETRO_LAUNCHCTL_LOG"
grep -q bootout "$AGENT_RETRO_LAUNCHCTL_LOG"
