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
        excluded = [event(kind=kind, usage=dict(input=100))
                    for kind in ('message_start', 'message_update', 'tool_result')]
        excluded += [event(role='toolResult', usage=dict(input=100)),
                     event(role='user', usage=dict(input=100))]
        excluded += [event(stop=stop, usage=dict(input=100))
                     for stop in (None, 'error', 'aborted')]
        included = [event(stop=stop, usage=dict(input=1))
                    for stop in ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(excluded + included), dict(
            calls=3, input=3, output=0, cacheRead=0, cacheWrite=0, totalTokens=3))

    def test_missing_usage_and_supplied_totals(self):
        no_usage = dict(type='message_end', message=dict(role='assistant', stopReason='stop'))
        records = [no_usage, event(usage=dict(output=5, reasoning=3, totalTokens=999)),
                   event(usage=dict(input=2, cacheRead=4, cacheWrite=6))]
        self.assertEqual(summarize(records), dict(
            calls=3, input=2, output=5, cacheRead=4, cacheWrite=6, totalTokens=17))

    def test_cli_ignores_blank_lines_and_prints_one_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.jsonl'
            path.write_text('\n  \n'.join(json.dumps(record) for record in [
                event(kind='message_update', usage=dict(input=100)),
                event(stop='length', usage=dict(input=2, output=3, cacheRead=4, cacheWrite=5)),
            ]) + '\n')
            completed = subprocess.run([sys.executable, str(Path(__file__).with_name('usage_summary.py')),
                                        str(path)], capture_output=True, text=True, check=True)
        self.assertEqual(len(completed.stdout.splitlines()), 1)
        self.assertEqual(json.loads(completed.stdout), dict(
            calls=1, input=2, output=3, cacheRead=4, cacheWrite=5, totalTokens=14))


if __name__ == '__main__':
    unittest.main()
