#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_DEST="${CODEX_HOME:-$HOME/.codex}/skills"
AGENTS_DEST="$HOME/.agents/skills"
FAIL_ON="${SKILL_RISK_FAIL_ON:-none}"

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
if command -v python3 >/dev/null 2>&1; then
  echo "Running post-install skill risk scan..."
  installed_skill_dirs=()
  for src_dir in "$ROOT_DIR"/codex-skills/*; do
    [ -d "$src_dir" ] || continue
    installed_skill_dirs+=("$CODEX_DEST/$(basename "$src_dir")")
  done

  if [ "${#installed_skill_dirs[@]}" -gt 0 ]; then
    python3 "$ROOT_DIR/scripts/scan-skills-risk.py" --fail-on "$FAIL_ON" "${installed_skill_dirs[@]}"
  else
    echo "No custom skills found to scan."
  fi
else
  echo "Warning: python3 not found; skipped post-install risk scan."
fi

echo
echo "Done. Restart Codex to load the updated skills."
