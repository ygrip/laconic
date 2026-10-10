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


def verify(work, task='usage'):
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
    acceptance = json.loads(p.stdout) if p.stdout else []
    if task == 'log-triage':
        try: incident = json.loads((work/'incident.json').read_text())
        except (ValueError, OSError): incident = None
        acceptance.append(dict(name='incident record from diagnostic command', passed=incident ==
                               dict(customer='cedar', batch=463, reason='stale-cache', lost_calls=17), actual=incident))
        acceptance.append(dict(name='diagnostic generator unchanged', passed=(work/'diagnose.py').read_bytes() == (ROOT/'log-triage.py').read_bytes()))
    return dict(acceptance_exit_code=p.returncode if all(c['passed'] for c in acceptance) else 1, acceptance=acceptance,
                acceptance_stderr=p.stderr, suite_exit_code=tests.returncode,
                suite_output=tests.stdout + tests.stderr)


def run_one(pair, arm, args, output):
    with tempfile.TemporaryDirectory(prefix='laconic-e2e-') as temporary:
        temp = Path(temporary)
        work, config = temp/'work', temp/'config'
        shutil.copytree(ROOT/'fixture', work)
        if args.task == 'log-triage': shutil.copy2(ROOT/'log-triage.py', work/'diagnose.py')
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
        if args.task == 'log-triage':
            prompt += '\nFirst run `python3 diagnose.py` directly (no pipe, redirect, or source inspection). Diagnose the failed reconciliation from its emitted log. If the result is partial, recover the incident record before continuing. Write incident.json with customer, batch (integer), reason, and lost_calls (integer). Do not modify diagnose.py. Then complete the utility repair above.\n'
        command = ['pi', '--mode', 'json', '--print', '--no-session', '--no-extensions',
                   '--no-mcp', '--no-skills', '--no-prompt-templates', '--no-themes',
                   '--no-context-files', '--tools', 'read,bash,edit,write' + (',laconic_read_result' if arm in ('runtime','both') else ''),
                   '--provider', args.provider, '--model', args.model, '--thinking', args.thinking]
        if arm in ('laconic', 'both'):
            command += ['--skill', str(skill)]
            prompt = '/skill:laconic ' + prompt
        # Pi's CLI resource resolver accepts .ts/.js, not .mjs (even though the
        # low-level extension loader can import .mjs). Use a real CLI entry.
        entry = temp/'benchmark-extension.ts'
        entry.write_text('import audit from ' + json.dumps((ROOT/'audit-extension.ts').as_uri()) + ';\n' +
                         'import laconic from ' + json.dumps((REPO/'runtime/adapters/pi.mjs').as_uri()) + ';\n' +
                         'export default async function(pi) { ' +
                         ('await laconic(pi); ' if arm in ('runtime','both') else '') + 'audit(pi); }\n')
        command += ['--extension', str(entry)]
        command += [prompt]
        env = dict(os.environ, PI_CODING_AGENT_DIR=str(config), PI_SKIP_VERSION_CHECK='1', PI_TELEMETRY='0')
        policy_file = temp/'policy.json'
        policy_file.write_text('{}')  # Explicit defaults; ignore the user's runtime settings.
        env.update(LACONIC_CONFIG=str(policy_file), LACONIC_STORE_DIR=str(temp/'recovery'),
                   LACONIC_BENCHMARK_RUNTIME='1' if arm in ('runtime','both') else '0',
                   LACONIC_BENCHMARK_AUDIT=str(temp/'startup-audit.json'))
        env.pop('LACONIC_BENCHMARK_PREFLIGHT', None)
        for key in ('PI_SESSION_ID', 'PI_SESSION_FILE', 'PI_PROVIDER', 'PI_MODEL', 'PI_REASONING_LEVEL'):
            env.pop(key, None)
        preflight = subprocess.run(command, cwd=work, env=dict(env, LACONIC_BENCHMARK_PREFLIGHT='1'),
                                   capture_output=True, text=True, timeout=30)
        audit_path = temp/'startup-audit.json'
        if preflight.returncode or not audit_path.exists():
            raise RuntimeError(f'Pi activation preflight failed for {arm}: {preflight.returncode}; {preflight.stderr}')
        preflight_audit = json.loads(audit_path.read_text())
        if not preflight_audit.get('correct_active_tools'): raise RuntimeError('Incorrect preflight tool activation')
        audit_path.unlink()
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
        if not audit_path.exists(): raise RuntimeError('Benchmark observer was not loaded in provider session')
        startup_audit = json.loads(audit_path.read_text())
        if not startup_audit.get('correct_active_tools'): raise RuntimeError('Incorrect provider-session tool activation')
        (dest/'startup-audit.json').write_text(json.dumps(dict(preflight=preflight_audit, session=startup_audit),indent=2)+'\n')

        def sanitize(text):
            return text.replace(str(work), '<WORKSPACE>').replace(str(skill), '<SKILL>').replace(str(temp), '<TEMP>').replace(str(REPO), '<REPO>')

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
        if (temp/'recovery').exists():
            recovery_dest = dest/'recovery'
            recovery_dest.mkdir()
            for stored in (temp/'recovery').iterdir():
                (recovery_dest/stored.name).write_text(sanitize(stored.read_text()))
        checks = verify(work, args.task)
        (dest/'verification.json').write_text(json.dumps(checks, indent=2)+'\n')
        totals = {k:sum(m.get('usage', {}).get(k, 0) for m in messages) for k in FIELDS}
        tool_messages = [e['message'] for e in events if e.get('type') == 'message_end'
                         and e.get('message', {}).get('role') == 'toolResult']
        optimized = [m for m in tool_messages if any('[Laconic: partial ' in b.get('text','') for b in m['content'])]
        metrics = dict(pair=pair, arm=arm, task=args.task, started_utc=started, elapsed_seconds=round(elapsed, 3),
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
                       runtime_filtered_results=len(optimized),
                       recovery_calls=sum(m.get('toolName') == 'laconic_read_result' for m in tool_messages),
                       tool_errors=sum(bool(m.get('isError')) for m in tool_messages),
                       acceptance_passed=sum(c['passed'] for c in checks['acceptance']),
                       acceptance_total=len(checks['acceptance']), suite_exit_code=checks['suite_exit_code'])
        (dest/'metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')
        print(json.dumps(metrics), flush=True)
        return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pairs', type=int, default=3)
    parser.add_argument('--arms', nargs='+', choices=['baseline','laconic','runtime','both'], default=['baseline','laconic'])
    parser.add_argument('--tasks', nargs='+', choices=['usage','log-triage'], default=['usage'])
    parser.add_argument('--provider', default='openai-codex')
    parser.add_argument('--model', default='gpt-6-sol')
    parser.add_argument('--thinking', default='medium')
    parser.add_argument('--agent-dir', default='~/.pi/agent')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.pairs < 1: parser.error('--pairs must be positive')
    if len(set(args.arms)) != len(args.arms) or len(set(args.tasks)) != len(args.tasks): parser.error('duplicate arms/tasks')
    if 'baseline' not in args.arms: parser.error('baseline arm is required')
    output = args.output.resolve()
    if output.exists(): parser.error('output already exists; choose a new directory to preserve evidence')
    output.mkdir(parents=True)
    version = subprocess.check_output(['pi','--version'], text=True).strip()
    runtime_hashes = {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in sorted((REPO/'runtime').rglob('*.mjs'))}
    manifest = dict(pi_version=version, pairs=args.pairs, arms=args.arms, tasks=args.tasks,
                    runtime_sha256=runtime_hashes, runtime_policy='explicit defaults, fresh local recovery store per run',
                    observer_sha256=hashlib.sha256((ROOT/'audit-extension.ts').read_bytes()).hexdigest(),
                    activation='temporary .ts CLI entry; identical silent startup observer in all arms; pre-inference CLI preflight and published active-tool audits',
                    log_triage_sha256=hashlib.sha256((ROOT/'log-triage.py').read_bytes()).hexdigest(),
                    provider=args.provider, model=args.model,
                    thinking=args.thinking, skill_sha256=hashlib.sha256((REPO/'SKILL.md').read_bytes()).hexdigest(),
                    prompt_sha256=hashlib.sha256((ROOT/'prompt.txt').read_bytes()).hexdigest(),
                    order='odd pairs: requested arm order; even pairs: reverse order; tasks in requested order',
                    isolation='temporary cwd/config; no MCP/context/discovered skills/templates/themes; explicit silent startup observer in all arms; runtime hook and recovery only in runtime/both; four built-in tools plus recovery tool in runtime/both',
                    skill_activation='--no-skills --skill <SKILL>; /skill:laconic <identical task>',
                    event_filter='message_end only; thinking and opaque signatures removed; temporary paths replaced',
                    platform=os.uname().sysname, python_version=subprocess.check_output(['python3','--version'], text=True).strip())
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    shutil.copy2(REPO/'SKILL.md', output/'SKILL.md')
    metrics = []
    for task in args.tasks:
        args.task = task
        task_output = output/task if len(args.tasks) > 1 else output
        for pair in range(1, args.pairs+1):
            for arm in (args.arms if pair % 2 else list(reversed(args.arms))):
                metrics.append(run_one(pair, arm, args, task_output))
    (output/'metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')


if __name__ == '__main__':
    main()
