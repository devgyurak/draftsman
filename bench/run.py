"""Run the benchmark: one isolated Claude Code session per (task, repo, class, arm, run).

    python3 bench/run.py pilot      [--dry-run]
    python3 bench/run.py measured   [--dry-run]
    python3 bench/run.py measured --version v2 [--arms B]

--version names a later round of the same set (results/raw/<set>-<version>/), run with
the same configuration on an image whose plugin changed; --arms runs only those arms.

Each run starts a fresh container from the draftsman-bench image (bench/container),
copies the pinned repository into the container's own filesystem, and runs
`claude --print` there with only the arm's plugin. The stream-json transcript goes to
results/raw/<set>/<run id>.jsonl and its metadata to <run id>.meta.json. A run counts
as done once its metadata is written, so an interrupted set resumes with the run that
was cut off. The metadata keeps the session's init event (tools, skills, MCP servers,
plugins) to check that the arms differ only in their plugin.

Authentication is passed through from the environment (ANTHROPIC_API_KEY or
CLAUDE_CODE_OAUTH_TOKEN), or read from ~/.config/draftsman-bench/oauth-token (a token
from `claude setup-token`); it reaches the container as an environment variable and is
never written to the results: its value is masked in the transcript and stderr.
"""

import argparse
import json
import os
import random
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

BENCH = Path(__file__).resolve().parent
IMAGE = 'draftsman-bench'
AUTH_VARS = ('ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN')
TOKEN_FILE = Path.home() / '.config' / 'draftsman-bench' / 'oauth-token'


def matrix(tasks: dict, focus: dict, which: str) -> list[dict]:
    runs = []
    t1, t2 = tasks['tasks']['T1'], tasks['tasks']['T2']
    if which == 'pilot':
        targets = [('T2', repo, c, 1) for repo, cs in focus['pilot'].items() for c in cs]
    else:
        targets = [('T1', repo, None, t1['runs']) for repo in t1['repos']]
        targets += [('T2', repo, c, t2['runs']) for repo in t2['repos'] for c in focus['measured'][repo]]
    for task, repo, cls, n in targets:
        prompt = tasks['tasks'][task]['prompt']
        if cls:
            prompt = prompt.format(name=cls['name'], fqn=cls['fqn'])
        for arm in tasks['arms']:
            for i in range(1, n + 1):
                name = cls['name'] if cls else 'all'
                runs.append({'id': f'{task}-{repo}-{name}-{arm}-{i}', 'task': task, 'repo': repo,
                             'focus': cls['fqn'] if cls else None, 'arm': arm, 'run': i,
                             'prompt': prompt})
    random.Random(tasks['selection']['seed']).shuffle(runs)
    return runs


def command(tasks: dict, run: dict) -> list[str]:
    plugins = tasks['arms'][run['arm']]['plugins']
    claude = ['claude', *tasks['run']['flags'], '--model', tasks['model'], '--effort', tasks['effort']]
    if tasks['run']['max_budget_usd'] is not None:
        claude += ['--max-budget-usd', str(tasks['run']['max_budget_usd'])]
    for p in plugins:
        claude += ['--plugin-dir', f'/opt/bench/plugins/{p}']
    claude += [run['prompt']]
    seconds = tasks['run']['timeout_minutes'] * 60
    # the other arms' plugins leave the container before the session starts
    others = sorted({p for a in tasks['arms'].values() for p in a['plugins']} - set(plugins))
    remove = ''.join(f'rm -rf /opt/bench/plugins/{p} && ' for p in others)
    script = (f'{remove}cp -R /opt/bench/repos/{run["repo"]} work && cd work && '
              f'exec timeout {seconds} {shlex.join(claude)}')
    env = [a for v in AUTH_VARS if os.environ.get(v) for a in ('-e', v)]
    return ['docker', 'run', '--rm', *env, IMAGE, 'bash', '-c', script]


def image() -> dict:
    out = subprocess.run(['docker', 'image', 'inspect', IMAGE, '--format',
                          '{{json .Config.Labels}}\t{{.Id}}'], capture_output=True, text=True, check=True)
    labels, image_id = out.stdout.strip().split('\t')
    return {'id': image_id, 'labels': json.loads(labels)}


def init_event(transcript: Path) -> dict | None:
    """What the session started with, from its first system/init event."""
    with open(transcript) as fh:
        for line in fh:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get('type') == 'system' and event.get('subtype') == 'init':
                keys = ('model', 'claude_code_version', 'apiKeySource', 'permissionMode', 'tools',
                        'mcp_servers', 'skills', 'agents', 'plugins', 'slash_commands')
                return {k: event[k] for k in keys if k in event}
    return None


def mask(path: Path, secret: str) -> int:
    text = path.read_text()
    if secret not in text:
        return 0
    path.write_text(text.replace(secret, '[credential]'))
    return text.count(secret)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('set', choices=['pilot', 'measured'])
    ap.add_argument('--dry-run', action='store_true', help='print the runs, start nothing')
    ap.add_argument('--version', help='a later round: results go to <set>-<version>')
    ap.add_argument('--arms', help='only these arms, e.g. B')
    args = ap.parse_args()

    tasks = yaml.safe_load((BENCH / 'tasks.yaml').read_text())
    focus = yaml.safe_load((BENCH / 'focus.yaml').read_text())
    runs = [r for r in matrix(tasks, focus, args.set) if not args.arms or r['arm'] in args.arms]
    if args.dry_run:
        for r in runs:
            print(r['id'])
        print(f'{len(runs)} runs; first command:\n' + shlex.join(command(tasks, runs[0])))
        return
    if not any(os.environ.get(v) for v in AUTH_VARS) and TOKEN_FILE.is_file():
        os.environ['CLAUDE_CODE_OAUTH_TOKEN'] = TOKEN_FILE.read_text().strip()
    present = [v for v in AUTH_VARS if os.environ.get(v)]
    if not present:
        raise SystemExit(f'no credentials: set one of {", ".join(AUTH_VARS)} or write {TOKEN_FILE}')
    if len(present) > 1:
        raise SystemExit(f'both {" and ".join(present)} are set; keep one, so every run bills one way')
    auth = present[0]
    secret = os.environ[auth]

    img = image()
    out_dir = BENCH / 'results' / 'raw' / (f'{args.set}-{args.version}' if args.version else args.set)
    out_dir.mkdir(parents=True, exist_ok=True)
    for n, run in enumerate(runs, 1):
        transcript = out_dir / f'{run["id"]}.jsonl'
        meta_file = out_dir / f'{run["id"]}.meta.json'
        if meta_file.exists():
            continue
        print(f'[{n}/{len(runs)}] {run["id"]}', flush=True)
        started = time.time()
        with open(transcript, 'w') as fh:
            proc = subprocess.run(command(tasks, run), stdin=subprocess.DEVNULL, stdout=fh,
                                  stderr=subprocess.PIPE, text=True)
        masked = mask(transcript, secret)
        stderr = proc.stderr.replace(secret, '[credential]')
        meta = {**run, 'model': tasks['model'], 'effort': tasks['effort'], 'image': img,
                'auth': auth, 'credential_masked': masked + proc.stderr.count(secret),
                'started': datetime.fromtimestamp(started, timezone.utc).isoformat(),
                'wall_seconds': round(time.time() - started, 1), 'exit_code': proc.returncode,
                'timed_out': proc.returncode == 124, 'init': init_event(transcript),
                'stderr_tail': stderr[-2000:]}
        meta_file.write_text(json.dumps(meta, indent=2) + '\n')


if __name__ == '__main__':
    main()
