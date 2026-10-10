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
        self.assertEqual(summarize([event(usage=dict(output=5, reasoning=3, totalTokens=999))]),
                         dict(calls=1, input=0, output=5, cacheRead=0, cacheWrite=0, totalTokens=5))

    def test_only_completed_assistant_messages_count(self):
        usage = dict(input=100, output=20, cacheRead=30, cacheWrite=40)
        records = [event(kind=kind, usage=usage) for kind in ('message_start', 'message_update')]
        records += [event(role='toolResult', usage=usage), event(role='user', usage=usage)]
        records += [event(stop=stop, usage=usage) for stop in ('error', 'aborted', None)]
        records += [event(stop=stop, usage=dict(input=1)) for stop in ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(records),
                         dict(calls=3, input=3, output=0, cacheRead=0, cacheWrite=0, totalTokens=3))

    def test_missing_usage_and_fields(self):
        no_usage = dict(type='message_end', message=dict(role='assistant', stopReason='stop'))
        self.assertEqual(summarize([no_usage, event(stop='length', usage=dict(cacheWrite=4))]),
                         dict(calls=2, input=0, output=0, cacheRead=0, cacheWrite=4, totalTokens=4))

    def test_cli_ignores_blank_lines_and_prints_one_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n  \n'.join(json.dumps(record) for record in [
                event(kind='message_update', usage=dict(input=100)),
                event(usage=dict(input=2, output=3, cacheRead=4, cacheWrite=5,
                                 reasoning=2, totalTokens=999)),
                event(stop='error', usage=dict(input=100)),
            ]) + '\n')
            output = subprocess.check_output([sys.executable, 'usage_summary.py', str(path)],
                                             cwd=Path(__file__).resolve().parent, text=True)
        self.assertEqual(output.count('\n'), 1)
        self.assertEqual(json.loads(output),
                         dict(calls=1, input=2, output=3, cacheRead=4, cacheWrite=5, totalTokens=14))


if __name__ == '__main__':
    unittest.main()
