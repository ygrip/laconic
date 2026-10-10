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

    def test_only_completed_assistant_messages_count(self):
        ignored = [event(kind=kind, usage={'input': 100})
                   for kind in ('message_start', 'message_update', 'message_delta')]
        ignored += [event(role='toolResult', usage={'input': 100}),
                    event(role='user', usage={'input': 100})]
        ignored += [event(stop=stop, usage={'input': 100})
                    for stop in ('error', 'aborted', None)]
        completed = [event(stop=stop, usage={'input': 1})
                     for stop in ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(ignored + completed), dict(
            calls=3, input=3, output=0, cacheRead=0, cacheWrite=0, totalTokens=3))

    def test_missing_usage_and_untrusted_totals(self):
        no_usage = dict(type='message_end', message=dict(role='assistant', stopReason='stop'))
        records = [no_usage, event(usage={'output': 5, 'reasoning': 3, 'totalTokens': 999}),
                   event(usage={'input': 2, 'cacheRead': 7, 'cacheWrite': 4})]
        self.assertEqual(summarize(records), dict(
            calls=3, input=2, output=5, cacheRead=7, cacheWrite=4, totalTokens=18))

    def test_cli_ignores_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n' + json.dumps(event(usage={'input': 2})) + '\n \n')
            output = subprocess.check_output([sys.executable, 'usage_summary.py', str(path)], text=True)
        self.assertEqual(json.loads(output), dict(
            calls=1, input=2, output=0, cacheRead=0, cacheWrite=0, totalTokens=2))


if __name__ == '__main__':
    unittest.main()
