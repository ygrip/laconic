import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from usage_summary import summarize


def event(kind='message_end', role='assistant', stop='stop', usage=None):
    return dict(type=kind, message=dict(role=role, stopReason=stop, usage=usage or {}))


class UsageTests(unittest.TestCase):
    def test_completed(self):
        self.assertEqual(summarize([event(usage=dict(input=10, output=5))])['calls'], 1)

    def test_only_completed_assistant_messages_count(self):
        ignored = [event(kind=kind, usage={'input': 100}) for kind in
                   ('message_start', 'message_update', 'tool_result')]
        ignored += [event(role='toolResult', usage={'input': 100})]
        ignored += [event(stop=stop, usage={'input': 100}) for stop in
                    ('error', 'aborted', None)]
        counted = [event(stop=stop, usage={'input': 1}) for stop in
                   ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(ignored + counted), {
            'calls': 3, 'input': 3, 'output': 0, 'cacheRead': 0,
            'cacheWrite': 0, 'totalTokens': 3,
        })

    def test_missing_usage_and_fields(self):
        no_usage = dict(type='message_end', message=dict(role='assistant', stopReason='stop'))
        self.assertEqual(summarize([no_usage, event(stop='length', usage={'cacheWrite': 4})]), {
            'calls': 2, 'input': 0, 'output': 0, 'cacheRead': 0,
            'cacheWrite': 4, 'totalTokens': 4,
        })

    def test_cache_is_included(self):
        result = summarize([event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2))])
        self.assertEqual(result['totalTokens'], 25)
        self.assertEqual(result['cacheRead'], 8)
        self.assertEqual(result['cacheWrite'], 2)

    def test_reasoning_and_supplied_total_are_not_added(self):
        result = summarize([event(usage=dict(input=2, output=5, reasoning=3, totalTokens=999))])
        self.assertEqual(result['output'], 5)
        self.assertEqual(result['totalTokens'], 7)

    def test_cli_ignores_blank_lines_and_prints_one_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n' + json.dumps(event(usage={'output': 3})) + '\n  \n')
            process = subprocess.run([sys.executable, str(Path(__file__).with_name('usage_summary.py')),
                                      str(path)], capture_output=True, text=True, check=True)
        self.assertEqual(len(process.stdout.splitlines()), 1)
        self.assertEqual(json.loads(process.stdout), {
            'calls': 1, 'input': 0, 'output': 3, 'cacheRead': 0,
            'cacheWrite': 0, 'totalTokens': 3,
        })


if __name__ == '__main__':
    unittest.main()
