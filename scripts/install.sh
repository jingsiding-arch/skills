#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_DEST="${CODEX_HOME:-$HOME/.codex}/skills"
AGENTS_DEST="$HOME/.agents/skills"
FAIL_ON="${SKILL_RISK_FAIL_ON:-none}"
SELECTED_SKILLS=("$@")
installed_skill_dirs=()

resolve_skill_dirs() {
  local skill_name
  local skill_dir

  if [ "${#SELECTED_SKILLS[@]}" -eq 0 ]; then
    for skill_dir in "$ROOT_DIR"/codex-skills/*; do
      [ -d "$skill_dir" ] || continue
      installed_skill_dirs+=("$CODEX_DEST/$(basename "$skill_dir")")
      rsync -a "$skill_dir/" "$CODEX_DEST/$(basename "$skill_dir")/"
    done
    return
  fi

  for skill_name in "${SELECTED_SKILLS[@]}"; do
    skill_dir="$ROOT_DIR/codex-skills/$skill_name"
    if [ ! -d "$skill_dir" ]; then
      echo "Error: skill '$skill_name' was not found under $ROOT_DIR/codex-skills" >&2
      exit 1
    fi

    installed_skill_dirs+=("$CODEX_DEST/$skill_name")
    mkdir -p "$CODEX_DEST/$skill_name"
    rsync -a "$skill_dir/" "$CODEX_DEST/$skill_name/"
  done
}

echo "Installing custom Codex skills to: $CODEX_DEST"
mkdir -p "$CODEX_DEST"
resolve_skill_dirs

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
  if [ "${#installed_skill_dirs[@]}" -gt 0 ]; then
    python3 "$ROOT_DIR/scripts/scan-skills-risk.py" --fail-on "$FAIL_ON" "${installed_skill_dirs[@]}"
    echo
    python3 "$ROOT_DIR/scripts/show-skill-recommendations.py" --installed-root "$CODEX_DEST" "${installed_skill_dirs[@]}"
  else
    echo "No custom skills found to scan."
  fi
else
  echo "Warning: python3 not found; skipped post-install risk scan and companion skill suggestions."
fi

echo
echo "Done. Restart Codex to load the updated skills."
