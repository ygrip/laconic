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

    def test_streaming_is_not_a_call(self):
        self.assertEqual(summarize([event(kind='message_update')])['calls'], 0)

    def test_cache_is_included(self):
        result = summarize([event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2))])
        self.assertEqual(result['totalTokens'], 25)
        self.assertEqual(result['cacheRead'], 8)
        self.assertEqual(result['cacheWrite'], 2)

    def test_reasoning_is_not_added_twice(self):
        self.assertEqual(summarize([event(usage=dict(output=5, reasoning=3))])['output'], 5)

    def test_only_completed_assistant_end_events_count(self):
        records = [
            event(kind='message_start', usage=dict(input=100)),
            event(kind='message_update', usage=dict(input=100)),
            event(role='toolResult', usage=dict(input=100)),
            event(role='user', usage=dict(input=100)),
            event(stop='error', usage=dict(input=100)),
            event(stop='aborted', usage=dict(input=100)),
            event(stop=None, usage=dict(input=100)),
            event(stop='stop', usage=dict(input=2, output=3)),
            event(stop='toolUse', usage=dict(cacheRead=4)),
            event(stop='length', usage=dict(cacheWrite=5)),
        ]
        self.assertEqual(summarize(records), dict(
            calls=3, input=2, output=3, cacheRead=4, cacheWrite=5, totalTokens=14
        ))

    def test_missing_usage_and_untrusted_extra_fields(self):
        records = [
            dict(type='message_end', message=dict(role='assistant', stopReason='stop')),
            event(usage=dict(input=7, output=11, cacheRead=13, cacheWrite=17,
                             reasoning=9, totalTokens=9999)),
        ]
        self.assertEqual(summarize(records), dict(
            calls=2, input=7, output=11, cacheRead=13, cacheWrite=17, totalTokens=48
        ))

    def test_cli_ignores_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n' + json.dumps(event(usage=dict(input=2, output=3))) + '\n  \n')
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name('usage_summary.py')), str(path)],
                check=True, capture_output=True, text=True,
            )
        self.assertEqual(json.loads(result.stdout), dict(
            calls=1, input=2, output=3, cacheRead=0, cacheWrite=0, totalTokens=5
        ))
        self.assertEqual(len(result.stdout.splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
