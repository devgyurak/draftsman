#!/usr/bin/env bash
# Build the benchmark image: repositories and plugins at the commits in tasks.yaml.
#   bench/container/build.sh <scratch dir>
# The scratch dir holds the build context; the image is tagged draftsman-bench.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../.." && pwd)"
ctx="${1:?scratch directory for the build context}/context"
rm -rf "$ctx" && mkdir -p "$ctx/repos" "$ctx/plugins"

yq() { uv run --project "$root" python -c "import sys, yaml; d = yaml.safe_load(open('$root/bench/tasks.yaml')); print(eval(sys.argv[1]))" "$1"; }

for repo in $(yq "' '.join(d['repos'])"); do
  url=$(yq "d['repos']['$repo']['url']"); commit=$(yq "d['repos']['$repo']['commit']")
  git clone -q --filter=blob:none --no-checkout "$url" "$ctx/repos/$repo"
  git -C "$ctx/repos/$repo" checkout -q "$commit"
  rm -rf "$ctx/repos/$repo/.git"
done

# arm B: the plugin's own files at HEAD (uncommitted changes are not measured). Only these:
# bench/, docs/ and the READMEs hold the answer key and must not reach any arm.
draftsman_commit=$(git -C "$root" rev-parse HEAD)
mkdir -p "$ctx/plugins/draftsman"
git -C "$root" archive HEAD .claude-plugin skills commands assets/icon.png LICENSE NOTICE \
  | tar -x -C "$ctx/plugins/draftsman"

# arm C: night-market's cartograph plugin at the pinned commit
nm_url=$(yq "d['arms']['C']['source']"); nm_commit=$(yq "d['arms']['C']['commit']")
nm_plugin=$(yq "d['arms']['C']['plugin']")
git clone -q --filter=blob:none --no-checkout "$nm_url" "$ctx/night-market"
git -C "$ctx/night-market" checkout -q "$nm_commit"
cp -R "$ctx/night-market/plugins/$nm_plugin" "$ctx/plugins/night-market"
rm -rf "$ctx/night-market"

docker build -t draftsman-bench -f "$here/Dockerfile" \
  --build-arg CLAUDE_CODE_VERSION="$(yq "d['claude_code_version']")" \
  --build-arg DRAFTSMAN_COMMIT="$draftsman_commit" \
  --build-arg NIGHT_MARKET_COMMIT="$nm_commit" \
  "$ctx"
