#!/usr/bin/env bash
# Replace arm B's plugin in an existing benchmark image and leave everything else as it
# was: repositories, Claude Code, Python packages and night-market stay byte for byte.
#   bench/container/update_draftsman.sh <scratch dir> <base tag>
# e.g. `docker tag draftsman-bench draftsman-bench:v1` first, then pass draftsman-bench:v1;
# the result is tagged draftsman-bench (latest) and labelled with its base.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../.." && pwd)"
ctx="${1:?scratch directory for the build context}/update-context"
base="${2:?base image tag}"
rm -rf "$ctx" && mkdir -p "$ctx/plugins/draftsman"

# as in build.sh: the plugin's own files at HEAD, never bench/ or docs/
# (commands/ went in 0.3.0; list only what HEAD has)
plugin_files=$(git -C "$root" ls-tree --name-only HEAD -- .claude-plugin skills commands assets/icon.png LICENSE NOTICE)
git -C "$root" archive HEAD $plugin_files \
  | tar -x -C "$ctx/plugins/draftsman"

docker build -t draftsman-bench -f "$here/Dockerfile.update" \
  --build-arg BASE="$base" \
  --build-arg BASE_ID="$(docker image inspect "$base" --format '{{.Id}}')" \
  --build-arg DRAFTSMAN_COMMIT="$(git -C "$root" rev-parse HEAD)" \
  "$ctx"
