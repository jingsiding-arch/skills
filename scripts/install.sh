#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_DEST="${CODEX_HOME:-$HOME/.codex}/skills"
AGENTS_DEST="$HOME/.agents/skills"

echo "Installing custom Codex skills to: $CODEX_DEST"
mkdir -p "$CODEX_DEST"
rsync -a "$ROOT_DIR/codex-skills/" "$CODEX_DEST/"

echo "Installing UI overrides to: $AGENTS_DEST"
mkdir -p "$AGENTS_DEST"

while IFS= read -r -d '' file; do
  rel_path="${file#"$ROOT_DIR/agents-overrides/"}"
  dest_path="$AGENTS_DEST/$rel_path"
  mkdir -p "$(dirname "$dest_path")"
  cp "$file" "$dest_path"
done < <(find "$ROOT_DIR/agents-overrides" -type f -name "openai.yaml" -print0)

echo
echo "Done. Restart Codex to load the updated skills."
