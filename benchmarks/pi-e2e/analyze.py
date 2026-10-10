#!/usr/bin/env python3
"""Recompute paired metrics and tool-result efficiency from published E2E evidence."""
import argparse
import json
from pathlib import Path
import statistics

METRICS = ('final_words', 'prose_words', 'output', 'input', 'cacheRead', 'cacheWrite',
           'total_tokens', 'input_context_tokens', 'tool_calls', 'tool_result_text_bytes',
           'skill_read_bytes', 'skill_read_calls', 'task_tool_result_text_bytes', 'model_calls',
           'estimated_cost_usd', 'elapsed_seconds', 'runtime_filtered_results', 'recovery_calls', 'tool_errors')


def analyze(root):
    runs = []
    paths = list(root.glob('pair-*/*/metrics.json'))
    if not paths and (root/'manifest.json').exists():
        manifest = json.loads((root/'manifest.json').read_text())
        if len(manifest.get('tasks',[])) > 1:
            paths = [path for task in manifest['tasks'] for path in (root/task).glob('pair-*/*/metrics.json')]
    for path in sorted(paths):
        metric = json.loads(path.read_text())
        events = [json.loads(line) for line in (path.parent/'events.jsonl').read_text().splitlines()]
        by_tool = {}
        truncations = 0
        skill_bytes = 0
        skill_calls = 0
        calls = {block['id']: block for event in events
                 if event['message'].get('role') == 'assistant'
                 for block in event['message'].get('content', []) if block.get('type') == 'toolCall'}
        for event in events:
            message = event['message']
            if message.get('role') != 'toolResult': continue
            tool = message['toolName']
            text = '\n'.join(b['text'] for b in message['content'] if b['type'] == 'text')
            entry = by_tool.setdefault(tool, dict(calls=0, text_bytes=0, errors=0))
            entry['calls'] += 1
            entry['text_bytes'] += sum(len(b['text'].encode()) for b in message['content'] if b['type'] == 'text')
            entry['errors'] += int(message.get('isError', False))
            truncations += int('truncat' in text.lower())
            call = calls.get(message.get('toolCallId'), {})
            if call.get('name') == 'read' and call.get('arguments', {}).get('path') == '<SKILL>/SKILL.md':
                skill_calls += 1
                skill_bytes += sum(len(b['text'].encode()) for b in message['content'] if b['type'] == 'text')
        # Sanitized paths can slightly change byte counts; original counts are in metrics.json.
        metric['runtime_filtered_results'] = sum('[Laconic: partial ' in '\n'.join(b.get('text','') for b in e['message'].get('content', []))
                                                   for e in events if e['message'].get('role') == 'toolResult')
        metric['recovery_calls'] = by_tool.get('laconic_read_result', {}).get('calls',0)
        metric['tool_errors'] = sum(t['errors'] for t in by_tool.values())
        metric['estimated_cost_usd'] = sum(event['message'].get('usage', {}).get('cost', {}).get('total', 0)
                                           for event in events if event['message'].get('role') == 'assistant')
        metric['input_context_tokens'] = sum(metric[k] for k in ('input', 'cacheRead', 'cacheWrite'))
        metric['skill_read_bytes'] = skill_bytes
        metric['skill_read_calls'] = skill_calls
        metric['task_tool_result_text_bytes'] = metric['tool_result_text_bytes'] - skill_bytes
        runs.append(dict(**metric, by_tool_sanitized=by_tool, results_mentioning_truncation=truncations,
                         acceptance_checks_per_1000_tool_bytes=round(metric['acceptance_passed']*1000 /
                                                                    metric['tool_result_text_bytes'], 3)))
    arms = {}
    arm_names = [arm for arm in ('baseline','laconic','runtime','both') if any(r['arm']==arm for r in runs)]
    if 'baseline' not in arm_names or len(arm_names) < 2: raise ValueError('baseline and at least one treatment are required')
    for arm in arm_names:
        subset = [r for r in runs if r['arm'] == arm]
        if not subset: raise ValueError(f'missing arm: {arm}')
        arms[arm] = {k: dict(sum=sum(r[k] for r in subset), mean=statistics.mean(r[k] for r in subset),
                             median=statistics.median(r[k] for r in subset)) for k in METRICS}
        arms[arm]['verified'] = all(r['acceptance_passed'] == r['acceptance_total'] and r['suite_exit_code'] == 0 for r in subset)
    comparisons = {arm: {k: round(100*(arms['baseline'][k]['sum']-arms[arm][k]['sum']) /
                                 arms['baseline'][k]['sum'], 3) if arms['baseline'][k]['sum'] else None for k in METRICS}
                   for arm in arm_names if arm != 'baseline'}
    paired = []
    groups = sorted(set((r.get('task','usage'),r['pair']) for r in runs))
    for task, pair in groups:
        subset = [r for r in runs if r.get('task','usage') == task and r['pair'] == pair]
        b = next(r for r in subset if r['arm']=='baseline')
        for arm in arm_names:
            if arm == 'baseline': continue
            l = next(r for r in subset if r['arm']==arm)
            paired.append(dict(task=task, pair=pair, arm=arm, savings_percent={k:round(100*(b[k]-l[k])/b[k], 3)
                                                                           if b[k] else None for k in METRICS}))
    return dict(runs=runs, arms=arms, aggregate_savings_percent=comparisons.get('laconic', next(iter(comparisons.values()))),
                comparisons_to_baseline=comparisons, paired=paired,
                definitions=dict(savings='100 * (baseline sum - laconic sum) / baseline sum; negative means increase',
                                 total_tokens='input + output + cacheRead + cacheWrite summed once per completed assistant message; reasoning is already output',
                                 estimated_cost_usd='sum of Pi usage.cost.total metadata; catalog-based estimate, not billed/subscription cost',
                                 input_context='input + cacheRead + cacheWrite; repeated context counted as the provider reports it',
                                 words='regex word count; prose includes all assistant text, not reasoning/code tool arguments',
                                 tool_bytes='UTF-8 text content bytes; excludes envelopes, images and tool-call arguments; not token counts',
                                 tool_efficiency='independent acceptance checks passed / tool-result bytes * 1000; meaningful only for this identical task',
                                 artifact_policy='non-streaming message_end events; reasoning/signatures omitted, temporary paths replaced'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    summary = analyze(args.results)
    (args.results/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    for arm, comparison in summary['comparisons_to_baseline'].items():
        print(arm)
        for key, value in comparison.items():
            print(f'  {key}: {value:+.3f}% reduction' if value is not None else f'  {key}: n/a')
    print('verified:', {arm: data['verified'] for arm, data in summary['arms'].items()})


if __name__ == '__main__':
    main()
