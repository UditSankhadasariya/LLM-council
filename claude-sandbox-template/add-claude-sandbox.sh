#!/bin/bash
# add-claude-sandbox.sh
# Copies the .devcontainer setup into a target project directory.
#
# Usage:
#   ./add-claude-sandbox.sh /path/to/your/repo
#   ./add-claude-sandbox.sh .    # current directory

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-.}"

if [ ! -d "$TARGET" ]; then
  echo "❌ Directory not found: $TARGET"
  exit 1
fi

if [ -d "$TARGET/.devcontainer" ]; then
  echo "⚠️  $TARGET/.devcontainer already exists."
  read -p "Overwrite? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
fi

cp -r "$SCRIPT_DIR/.devcontainer" "$TARGET/.devcontainer"
chmod +x "$TARGET/.devcontainer/init-firewall.sh"
chmod +x "$TARGET/.devcontainer/setup.sh"

echo "✅ Claude Code sandbox added to $TARGET"
echo ""
echo "Next steps:"
echo "  1. cd $TARGET"
echo "  2. Open in VS Code: code ."
echo "  3. Click 'Reopen in Container' when prompted"
echo "  4. In the container terminal: claude --dangerously-skip-permissions"
