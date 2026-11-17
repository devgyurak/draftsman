"""Run the benchmark: one isolated Claude Code session per (task, repo, class, arm, run).

    python3 bench/run.py pilot      [--dry-run]
    python3 bench/run.py measured   [--dry-run]

Each run starts a fresh container from the draftsman-bench image (bench/container),
copies the pinned repository into the container's own filesystem, and runs
`claude --print` there with only the arm's plugin. The stream-json transcript goes to
results/raw/<set>/<run id>.jsonl and its metadata to <run id>.meta.json. Runs whose
transcript already exists are skipped, so an interrupted set can be resumed.

Authentication is passed through from the environment (ANTHROPIC_API_KEY or
CLAUDE_CODE_OAUTH_TOKEN), or read from ~/.config/draftsman-bench/oauth-token (a token
from `claude setup-token`); it reaches the container as an environment variable and is
never written to the results.
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
    script = (f'cp -R /opt/bench/repos/{run["repo"]} work && cd work && '
              f'exec timeout {seconds} {shlex.join(claude)}')
    env = [a for v in AUTH_VARS if os.environ.get(v) for a in ('-e', v)]
    return ['docker', 'run', '--rm', '-i', *env, IMAGE, 'bash', '-c', script]


def image_labels() -> dict:
    out = subprocess.run(['docker', 'image', 'inspect', IMAGE, '--format', '{{json .Config.Labels}}'],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('set', choices=['pilot', 'measured'])
    ap.add_argument('--dry-run', action='store_true', help='print the runs, start nothing')
    args = ap.parse_args()

    tasks = yaml.safe_load((BENCH / 'tasks.yaml').read_text())
    focus = yaml.safe_load((BENCH / 'focus.yaml').read_text())
    runs = matrix(tasks, focus, args.set)
    if args.dry_run:
        for r in runs:
            print(r['id'])
        print(f'{len(runs)} runs; first command:\n' + shlex.join(command(tasks, runs[0])))
        return
    if not any(os.environ.get(v) for v in AUTH_VARS) and TOKEN_FILE.is_file():
        os.environ['CLAUDE_CODE_OAUTH_TOKEN'] = TOKEN_FILE.read_text().strip()
    if not any(os.environ.get(v) for v in AUTH_VARS):
        raise SystemExit(f'no credentials: set one of {", ".join(AUTH_VARS)} or write {TOKEN_FILE}')
    auth = next(v for v in AUTH_VARS if os.environ.get(v))

    labels = image_labels()
    out_dir = BENCH / 'results' / 'raw' / args.set
    out_dir.mkdir(parents=True, exist_ok=True)
    for n, run in enumerate(runs, 1):
        transcript = out_dir / f'{run["id"]}.jsonl'
        if transcript.exists():
            continue
        print(f'[{n}/{len(runs)}] {run["id"]}', flush=True)
        started = time.time()
        with open(transcript, 'w') as fh:
            proc = subprocess.run(command(tasks, run), stdout=fh, stderr=subprocess.PIPE, text=True)
        meta = {**run, 'model': tasks['model'], 'effort': tasks['effort'], 'image': labels,
                'auth': auth,
                'started': datetime.fromtimestamp(started, timezone.utc).isoformat(),
                'wall_seconds': round(time.time() - started, 1), 'exit_code': proc.returncode,
                'timed_out': proc.returncode == 124, 'stderr_tail': proc.stderr[-2000:]}
        (out_dir / f'{run["id"]}.meta.json').write_text(json.dumps(meta, indent=2) + '\n')


if __name__ == '__main__':
    main()
