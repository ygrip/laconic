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
        records = [event(stop=stop, usage={'input': 1}) for stop in ('stop', 'toolUse', 'length')]
        records += [event(kind=kind, usage={'input': 100}) for kind in ('message_start', 'message_update')]
        records += [event(role='toolResult', usage={'input': 100}),
                    event(stop='error', usage={'input': 100}),
                    event(stop='aborted', usage={'input': 100}),
                    event(stop=None, usage={'input': 100}),
                    {'type': 'message_end', 'message': {'role': 'assistant', 'usage': {'input': 100}}}]
        self.assertEqual(summarize(records), dict(calls=3, input=3, output=0,
                                                  cacheRead=0, cacheWrite=0, totalTokens=3))

    def test_missing_usage_and_fields_count_as_zero(self):
        records = [{'type': 'message_end', 'message': {'role': 'assistant', 'stopReason': 'stop'}},
                   event(stop='length', usage={'cacheRead': 4})]
        self.assertEqual(summarize(records), dict(calls=2, input=0, output=0,
                                                  cacheRead=4, cacheWrite=0, totalTokens=4))

    def test_totals_ignore_supplied_total_and_reasoning(self):
        records = [event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                                    reasoning=3, totalTokens=999)),
                   event(stop='toolUse', usage=dict(input=2, output=4, totalTokens=1))]
        self.assertEqual(summarize(records), dict(calls=2, input=12, output=9,
                                                  cacheRead=8, cacheWrite=2, totalTokens=31))

    def test_cli_ignores_blank_lines_and_emits_one_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n' + json.dumps(event(usage={'output': 2})) + '\n  \n')
            output = subprocess.check_output([sys.executable, 'usage_summary.py', str(path)], text=True)
        self.assertEqual(len(output.splitlines()), 1)
        self.assertEqual(json.loads(output), dict(calls=1, input=0, output=2,
                                                  cacheRead=0, cacheWrite=0, totalTokens=2))


if __name__ == '__main__':
    unittest.main()
