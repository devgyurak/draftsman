#!/usr/bin/env bash
# Syntax-check a Mermaid file.  usage: validate.sh diagram.mmd
#
# Uses, in order: mermaid-cli (mmdc) if on PATH, otherwise the bundled node
# checker (needs `npm ci --prefix <skill>/scripts` once).
# Exit codes: 0 valid, 1 invalid, 2 no validator available.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
file="${1:?usage: validate.sh diagram.mmd}"

if command -v mmdc >/dev/null 2>&1; then
  out="$(mktemp -t draftsman-XXXXXX).svg"
  trap 'rm -f "$out"' EXIT
  if mmdc -q -i "$file" -o "$out" >/dev/null 2>&1; then
    echo "mermaid: OK"; exit 0
  fi
  mmdc -q -i "$file" -o "$out" 2>&1 | head -20 >&2 || true
  exit 1
fi

if command -v node >/dev/null 2>&1 && [ -d "$here/node_modules/mermaid" ]; then
  exec node "$here/validate.mjs" "$file"
fi

echo "mermaid: no validator available (install mermaid-cli, or run: npm ci --prefix '$here')" >&2
exit 2
