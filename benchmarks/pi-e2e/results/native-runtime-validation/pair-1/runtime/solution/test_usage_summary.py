import json
import subprocess
import sys
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
        excluded = [event(kind=kind, usage=dict(input=100))
                    for kind in ('message_start', 'message_update', 'tool_result')]
        excluded += [event(role='user', usage=dict(input=100)),
                     event(role='toolResult', usage=dict(input=100))]
        excluded += [event(stop=stop, usage=dict(input=100))
                     for stop in ('error', 'aborted', None)]
        included = [event(stop=stop, usage=dict(input=1))
                    for stop in ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(excluded + included), dict(
            calls=3, input=3, output=0, cacheRead=0, cacheWrite=0, totalTokens=3))

    def test_missing_usage_and_untrusted_totals(self):
        without_usage = dict(type='message_end', message=dict(role='assistant', stopReason='stop'))
        records = [without_usage, event(usage=dict(input=10, output=5, cacheRead=8,
                                                    cacheWrite=2, reasoning=4, totalTokens=999))]
        self.assertEqual(summarize(records), dict(
            calls=2, input=10, output=5, cacheRead=8, cacheWrite=2, totalTokens=25))

    def test_cli_fixture_ignores_blank_lines(self):
        fixture = Path(__file__).with_name('session.jsonl')
        script = Path(__file__).with_name('usage_summary.py')
        output = subprocess.check_output([sys.executable, str(script), str(fixture)], text=True)
        self.assertEqual(json.loads(output), dict(
            calls=2, input=150, output=35, cacheRead=50, cacheWrite=10, totalTokens=245))
        self.assertEqual(len(output.splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
