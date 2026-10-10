#!/usr/bin/env python3
"""Run matched real Pi CLI sessions. Requires Pi authentication; no Python dependencies."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
FIELDS = ('input', 'output', 'cacheRead', 'cacheWrite')


def completed_messages(events):
    return [e['message'] for e in events if e.get('type') == 'message_end'
            and e.get('message', {}).get('role') == 'assistant']


def verify(work):
    # Independent acceptance checks, not visible to the agent.
    code = r'''
import importlib.util, json, subprocess, sys
spec = importlib.util.spec_from_file_location('candidate', 'usage_summary.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
def e(kind='message_end', role='assistant', stop='stop', usage=None):
    message = dict(role=role, stopReason=stop)
    if usage is not None: message['usage'] = usage
    return dict(type=kind, message=message)
zero = dict(calls=0, input=0, output=0, cacheRead=0, cacheWrite=0, totalTokens=0)
checks = [
    ('empty', [], zero),
    ('streaming', [e(kind='message_update'), e(kind='message_start')], zero),
    ('tool result', [e(role='toolResult', usage={'input':99})], zero),
    ('unsuccessful', [e(stop=s) for s in ['pending','error','aborted']], zero),
    ('missing usage', [e()], dict(zero, calls=1)),
    ('partial usage', [e(usage={'output':7})], dict(zero, calls=1, output=7, totalTokens=7)),
    ('cache and reasoning', [e(usage=dict(input=11, output=9, cacheRead=30, cacheWrite=4, reasoning=6, totalTokens=999))], dict(calls=1, input=11, output=9, cacheRead=30, cacheWrite=4, totalTokens=54)),
    ('accepted stops', [e(stop=s, usage={'input':2}) for s in ['stop','toolUse','length']], dict(zero, calls=3, input=6, totalTokens=6)),
]
results = []
for name, records, expected in checks:
    actual = m.summarize(records)
    results.append(dict(name=name, passed=actual == expected, actual=actual, expected=expected))
p = subprocess.run([sys.executable, 'usage_summary.py', 'session.jsonl'], capture_output=True, text=True)
expected = dict(calls=2, input=150, output=35, cacheRead=50, cacheWrite=10, totalTokens=245)
try: actual = json.loads(p.stdout)
except ValueError: actual = p.stdout
results.append(dict(name='CLI fixture with blank lines', passed=p.returncode == 0 and actual == expected, exit_code=p.returncode, actual=actual, expected=expected))
print(json.dumps(results))
assert all(r['passed'] for r in results)
'''
    p = subprocess.run(['python3', '-c', code], cwd=work, capture_output=True, text=True)
    tests = subprocess.run(['python3', '-m', 'unittest', 'discover', '-v'], cwd=work,
                           capture_output=True, text=True)
    return dict(acceptance_exit_code=p.returncode, acceptance=json.loads(p.stdout) if p.stdout else [],
                acceptance_stderr=p.stderr, suite_exit_code=tests.returncode,
                suite_output=tests.stdout + tests.stderr)


def run_one(pair, arm, args, output):
    with tempfile.TemporaryDirectory(prefix='laconic-e2e-') as temporary:
        temp = Path(temporary)
        work, config = temp/'work', temp/'config'
        shutil.copytree(ROOT/'fixture', work)
        subprocess.run(['git', 'init', '-q', str(work)], check=True)
        config.mkdir()
        source = Path(args.agent_dir).expanduser()
        # Credentials never enter artifacts. Isolate settings, skills and extensions.
        shutil.copy2(source/'auth.json', config/'auth.json')
        if (source/'models.json').exists():
            shutil.copy2(source/'models.json', config/'models.json')
        (config/'settings.json').write_text(json.dumps({'packages': [], 'compaction': {'enabled': False}}))
        skill = temp/'laconic'
        skill.mkdir()
        shutil.copy2(REPO/'SKILL.md', skill/'SKILL.md')
        prompt = (ROOT/'prompt.txt').read_text()
        command = ['pi', '--mode', 'json', '--print', '--no-session', '--no-extensions',
                   '--no-mcp', '--no-skills', '--no-prompt-templates', '--no-themes',
                   '--no-context-files', '--tools', 'read,bash,edit,write',
                   '--provider', args.provider, '--model', args.model, '--thinking', args.thinking]
        if arm == 'laconic':
            command += ['--skill', str(skill)]
            prompt = '/skill:laconic ' + prompt
        command += [prompt]
        env = dict(os.environ, PI_CODING_AGENT_DIR=str(config), PI_SKIP_VERSION_CHECK='1', PI_TELEMETRY='0')
        for key in ('PI_SESSION_ID', 'PI_SESSION_FILE', 'PI_PROVIDER', 'PI_MODEL', 'PI_REASONING_LEVEL'):
            env.pop(key, None)
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        start = time.monotonic()
        p = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=args.timeout)
        elapsed = time.monotonic() - start
        events = []
        for line in p.stdout.splitlines():
            try: events.append(json.loads(line))
            except ValueError: pass
        messages = completed_messages(events)
        if p.returncode or not messages or messages[-1].get('stopReason') in ('error', 'aborted'):
            raise RuntimeError(f'Pi failed for {pair}/{arm}: exit={p.returncode}; {p.stderr}; {messages[-1:]!r}')
        dest = output/f'pair-{pair}'/arm
        dest.mkdir(parents=True)

        def sanitize(text):
            return text.replace(str(work), '<WORKSPACE>').replace(str(skill), '<SKILL>').replace(str(temp), '<TEMP>')

        # Publish complete non-streaming messages; omit private reasoning and opaque signatures.
        public = []
        for event in events:
            if event.get('type') != 'message_end': continue
            message = dict(event['message'])
            if isinstance(message.get('content'), list):
                message['content'] = [{k:v for k,v in block.items() if k not in
                                      ('textSignature','thinkingSignature','thoughtSignature')}
                                     for block in message['content'] if block.get('type') != 'thinking']
            public.append(dict(type='message_end', message=message))
        (dest/'events.jsonl').write_text(sanitize(''.join(json.dumps(e, ensure_ascii=False)+'\n' for e in public)))
        prose = ['\n'.join(b['text'] for b in m['content'] if b['type'] == 'text') for m in messages]
        final = prose[-1]
        (dest/'final.md').write_text(sanitize(final)+'\n')
        (dest/'prose.md').write_text(sanitize('\n\n'.join(t for t in prose if t))+'\n')
        (dest/'stderr.txt').write_text(sanitize(p.stderr))
        shutil.copy2(work/'usage_summary.py', dest/'usage_summary.py')
        shutil.copytree(work, dest/'solution', ignore=shutil.ignore_patterns('.git','__pycache__'))
        checks = verify(work)
        (dest/'verification.json').write_text(json.dumps(checks, indent=2)+'\n')
        totals = {k:sum(m.get('usage', {}).get(k, 0) for m in messages) for k in FIELDS}
        tool_messages = [e['message'] for e in events if e.get('type') == 'message_end'
                         and e.get('message', {}).get('role') == 'toolResult']
        metrics = dict(pair=pair, arm=arm, started_utc=started, elapsed_seconds=round(elapsed, 3),
                       pi_exit_code=p.returncode, model=args.model, provider=args.provider,
                       thinking=args.thinking, model_calls=len(messages), **totals,
                       total_tokens=sum(totals.values()),
                       reported_total_tokens=sum(m.get('usage', {}).get('totalTokens', 0) for m in messages),
                       reasoning_tokens=sum(m.get('usage', {}).get('reasoning', 0) for m in messages),
                       final_words=len(re.findall(r'\b[\w]+(?:[’\x27-][\w]+)*\b', final)),
                       prose_words=len(re.findall(r'\b[\w]+(?:[’\x27-][\w]+)*\b', '\n'.join(prose))),
                       final_characters=len(final), tool_calls=len(tool_messages),
                       tool_result_text_bytes=sum(len(b['text'].encode()) for m in tool_messages
                                                  for b in m['content'] if b['type'] == 'text'),
                       acceptance_passed=sum(c['passed'] for c in checks['acceptance']),
                       acceptance_total=len(checks['acceptance']), suite_exit_code=checks['suite_exit_code'])
        (dest/'metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')
        print(json.dumps(metrics), flush=True)
        return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pairs', type=int, default=3)
    parser.add_argument('--provider', default='openai-codex')
    parser.add_argument('--model', default='gpt-6-sol')
    parser.add_argument('--thinking', default='medium')
    parser.add_argument('--agent-dir', default='~/.pi/agent')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.pairs < 1: parser.error('--pairs must be positive')
    output = args.output.resolve()
    if output.exists(): parser.error('output already exists; choose a new directory to preserve evidence')
    output.mkdir(parents=True)
    version = subprocess.check_output(['pi','--version'], text=True).strip()
    manifest = dict(pi_version=version, pairs=args.pairs, provider=args.provider, model=args.model,
                    thinking=args.thinking, skill_sha256=hashlib.sha256((REPO/'SKILL.md').read_bytes()).hexdigest(),
                    prompt_sha256=hashlib.sha256((ROOT/'prompt.txt').read_bytes()).hexdigest(),
                    order='odd pairs: baseline then laconic; even pairs: laconic then baseline',
                    isolation='temporary cwd/config; no extensions/MCP/context/discovered skills/templates/themes; four built-in tools',
                    skill_activation='--no-skills --skill <SKILL>; /skill:laconic <identical task>',
                    event_filter='message_end only; thinking and opaque signatures removed; temporary paths replaced',
                    platform=os.uname().sysname, python_version=subprocess.check_output(['python3','--version'], text=True).strip())
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    shutil.copy2(REPO/'SKILL.md', output/'SKILL.md')
    metrics = []
    for pair in range(1, args.pairs+1):
        for arm in (['baseline','laconic'] if pair % 2 else ['laconic','baseline']):
            metrics.append(run_one(pair, arm, args, output))
    (output/'metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')


if __name__ == '__main__':
    main()
