"""Plugin manifests for Claude Code and Codex must agree with each other and the code."""

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]


def load(rel):
    return json.loads((ROOT / rel).read_text())


def test_versions_agree():
    claude = load(".claude-plugin/plugin.json")
    codex = load(".codex-plugin/plugin.json")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert claude["version"] == codex["version"] == project["version"]
    assert claude["name"] == codex["name"] == "draftsman"
    assert claude.get("license") == codex.get("license") == project.get("license")


def test_codex_manifest_points_at_skills():
    codex = load(".codex-plugin/plugin.json")
    skills = ROOT / codex["skills"]
    assert (skills / "draftsman" / "SKILL.md").is_file()
    assert (skills / "draftsman" / "agents" / "openai.yaml").is_file()
    for key in ("displayName", "shortDescription", "category", "defaultPrompt"):
        assert codex["interface"][key]


def test_marketplaces_list_the_plugin():
    claude = load(".claude-plugin/marketplace.json")
    codex = load(".agents/plugins/marketplace.json")
    assert [p["name"] for p in claude["plugins"]] == ["draftsman"]
    (entry,) = codex["plugins"]
    assert entry["name"] == "draftsman"
    assert entry["source"] == {"source": "local", "path": "./"}
    assert {"installation", "authentication"} <= set(entry["policy"]) and entry["category"]


def test_skill_frontmatter():
    text = (ROOT / "skills/draftsman/SKILL.md").read_text()
    front = re.match(r"---\n(.*?)\n---\n", text, re.S).group(1)
    assert re.search(r"^name: draftsman$", front, re.M)
    desc = re.search(r"^description: (.+)$", front, re.M).group(1)
    assert len(desc) <= 1024  # Agent Skills limit


def test_no_command_shadows_the_skill():
    """A plugin command named like a skill is what the Skill tool loads for that name
    (Claude Code 2.1.326): the agent then gets the command's text, not SKILL.md and its
    directory. The skill is a slash command of its own: /draftsman:draftsman, or /draftsman
    while no other command has that name (both checked on 2.1.326)."""
    commands = ROOT / "commands"
    skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    clashing = {p.stem for p in commands.glob("*.md")} & skills if commands.is_dir() else set()
    assert not clashing


def test_skill_stays_small():
    """SKILL.md is read in every run; detail belongs in references/."""
    assert len((ROOT / "skills/draftsman/SKILL.md").read_text()) < 6500


def test_elk_version_is_the_same_everywhere():
    """SVG (node) and the HTML viewer (inline or CDN) must lay out with one elkjs."""
    import json

    from draftsman.render_web import ELK_CDN, ELK_VERSION
    scripts = ROOT / "skills" / "draftsman" / "scripts"
    pkg = json.loads((scripts / "package.json").read_text())
    lock = json.loads((scripts / "package-lock.json").read_text())
    assert pkg["dependencies"]["elkjs"] == ELK_VERSION          # exact, not a range
    assert lock["packages"]["node_modules/elkjs"]["version"] == ELK_VERSION
    assert f"elkjs@{ELK_VERSION}/" in ELK_CDN
    # the lockfile is part of the repository, not ignored
    assert "package-lock.json" not in (ROOT / ".gitignore").read_text()
