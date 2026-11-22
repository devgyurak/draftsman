# One image for every arm: the three repositories at their pinned commits, both plugins,
# Claude Code, and Draftsman's dependencies installed ahead (warm runs). Built by
# bench/container/build.sh, which fills the build context; see tasks.yaml for versions.
FROM node:22-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip git ca-certificates ripgrep \
 && rm -rf /var/lib/apt/lists/*

ARG CLAUDE_CODE_VERSION
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

RUN pip3 install --break-system-packages "tree-sitter>=0.25" tree-sitter-language-pack pyyaml

# bypassPermissions is refused as root
RUN useradd --create-home --shell /bin/bash bench
USER bench
WORKDIR /home/bench

# read-only templates; run.sh copies one to a fresh directory per run
COPY --chown=bench repos/ /opt/bench/repos/
COPY --chown=bench plugins/ /opt/bench/plugins/
RUN npm ci --prefix /opt/bench/plugins/draftsman/skills/draftsman/scripts --no-audit --no-fund
# the language pack downloads each grammar on first use: fetch Java's now, so a run never
# depends on GitHub (third-round runs and before downloaded it, and that time was theirs)
RUN python3 -c "import tree_sitter_language_pack as t; t.get_language('java')"

ARG DRAFTSMAN_COMMIT
ARG NIGHT_MARKET_COMMIT
# labels only: an environment variable would be visible to the agent
LABEL bench.draftsman=${DRAFTSMAN_COMMIT} bench.night-market=${NIGHT_MARKET_COMMIT} \
      bench.claude-code=${CLAUDE_CODE_VERSION}
