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
        ignored = [
            event(kind='message_start', usage={'input': 100}),
            event(kind='message_update', usage={'input': 100}),
            event(kind='message_end', role='toolResult', usage={'input': 100}),
            event(stop='error', usage={'input': 100}),
            event(stop='aborted', usage={'input': 100}),
            event(stop=None, usage={'input': 100}),
            {'type': 'message_end'},
        ]
        counted = [
            event(stop='stop', usage={'input': 2, 'output': 3, 'reasoning': 2, 'totalTokens': 999}),
            event(stop='toolUse', usage={'cacheRead': 5, 'cacheWrite': 7}),
            {'type': 'message_end', 'message': {'role': 'assistant', 'stopReason': 'length'}},
        ]
        self.assertEqual(summarize(ignored + counted), {
            'calls': 3, 'input': 2, 'output': 3, 'cacheRead': 5,
            'cacheWrite': 7, 'totalTokens': 17,
        })

    def test_cli_ignores_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.jsonl'
            path.write_text('\n' + json.dumps(event(usage={'input': 4})) + '\n  \n')
            output = subprocess.check_output([sys.executable, str(Path(__file__).with_name('usage_summary.py')), str(path)], text=True)
        self.assertEqual(json.loads(output), {
            'calls': 1, 'input': 4, 'output': 0, 'cacheRead': 0,
            'cacheWrite': 0, 'totalTokens': 4,
        })


if __name__ == '__main__':
    unittest.main()
