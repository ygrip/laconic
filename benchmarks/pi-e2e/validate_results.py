#!/usr/bin/env python3
"""Audit treatment activation, matched diagnostic input, usage accounting, and correctness."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from run import REPO, ROOT, FIELDS


def validate(root):
    manifest = json.loads((root/'manifest.json').read_text())
    for name, digest in manifest['runtime_sha256'].items():
        assert hashlib.sha256((REPO/name).read_bytes()).hexdigest() == digest, f'Changed runtime source: {name}'
    assert hashlib.sha256((ROOT/'audit-extension.ts').read_bytes()).hexdigest() == manifest['observer_sha256']
    original_log = subprocess.check_output(['python3', str(ROOT/'log-triage.py')]).decode()
    runs = []
    for task in manifest['tasks']:
        task_root = root/task if len(manifest['tasks']) > 1 else root
        for pair in range(1, manifest['pairs']+1):
            for arm in manifest['arms']:
                dest = task_root/f'pair-{pair}'/arm
                metric = json.loads((dest/'metrics.json').read_text())
                checks = json.loads((dest/'verification.json').read_text())
                audit = json.loads((dest/'startup-audit.json').read_text())
                expected = sorted(['read','bash','edit','write'] + (['laconic_read_result'] if arm in ('runtime','both') else []))
                for phase in ('preflight','session'):
                    assert audit[phase]['correct_active_tools'] and audit[phase]['active_tools'] == expected, (task,pair,arm,phase)
                expected_checks = 11 if task == 'log-triage' else 9
                assert checks['suite_exit_code'] == checks['acceptance_exit_code'] == 0, dest
                assert len(checks['acceptance']) == expected_checks and all(c['passed'] for c in checks['acceptance']), dest
                assert metric['acceptance_passed'] == metric['acceptance_total'] == expected_checks
                events = [json.loads(line)['message'] for line in (dest/'events.jsonl').read_text().splitlines()]
                assistant = [m for m in events if m.get('role') == 'assistant']
                total = sum(m.get('usage',{}).get(field,0) for m in assistant for field in FIELDS)
                assert total == metric['total_tokens'] == metric['reported_total_tokens'], dest
                assert len(assistant) == metric['model_calls'], dest
                record = dict(task=task,pair=pair,arm=arm,checks_passed=expected_checks,activation_verified=True,usage_accounting_verified=True)
                if task == 'log-triage':
                    calls = [block for m in assistant for block in m.get('content',[]) if block.get('type') == 'toolCall']
                    probes = [c for c in calls if c['name'] == 'bash' and c.get('arguments',{}).get('command','').strip() == 'python3 diagnose.py']
                    assert len(probes) == 1, f'Diagnostic command not run exactly once/directly: {dest}'
                    messages = [m for m in events if m.get('role') == 'toolResult']
                    result = next(m for m in messages if m['toolCallId'] == probes[0]['id'])
                    text = '\n'.join(block['text'] for block in result['content'] if block['type'] == 'text')
                    if arm in ('runtime','both'):
                        assert '[Laconic: partial ' in text, f'Native runtime did not filter: {dest}'
                        assert 'INCIDENT customer=cedar' not in text, f'Incident was not outside the excerpt: {dest}'
                        recovery_id = re.search(r'lr_[a-f0-9]{32}',text).group()
                        assert (dest/'recovery'/recovery_id).read_text() == original_log, f'Original log not preserved: {dest}'
                        # A native recovery tool or an explicit read/CLI lookup of this exact
                        # stored ID must expose the incident. Correct guesses are not recovery.
                        recovery_calls = [c for c in calls if
                            (c['name'] == 'laconic_read_result' and c.get('arguments',{}).get('id') == recovery_id) or
                            recovery_id in str(c.get('arguments',{}))]
                        assert any('INCIDENT customer=cedar batch=463 reason=stale-cache lost_calls=17' in
                                   '\n'.join(b.get('text','') for b in m.get('content',[]))
                                   for c in recovery_calls for m in messages if m['toolCallId'] == c['id']), f'Incident not recovered: {dest}'
                        record.update(filtering_verified=True,original_log_verified=True,incident_recovery_verified=True)
                    else:
                        assert text == original_log, f'Baseline/skill log differs: {dest}'
                        record.update(original_log_verified=True,filtering_verified=False)
                runs.append(record)
    return dict(runs=len(runs),independent_checks_passed=sum(r['checks_passed'] for r in runs),
                runtime_source_hashes_match=True,all_activation_audits_passed=True,
                all_usage_totals_crosschecked=True,all_log_inputs_matched=True,
                all_runtime_log_incidents_recovered=True,details=runs,
                limitation='Workflow-specific checks, not universal correctness, blinded clarity, or provider billing verification.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    args=parser.parse_args()
    report=validate(args.results)
    (args.results/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='details'}))


if __name__ == '__main__':
    main()
