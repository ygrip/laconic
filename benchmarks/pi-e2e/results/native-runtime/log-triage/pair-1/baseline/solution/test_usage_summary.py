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
    def test_only_completed_assistant_messages_count(self):
        records = [event(stop=stop) for stop in ('stop', 'toolUse', 'length')]
        records += [event(kind=kind, usage={'input': 100})
                    for kind in ('message_start', 'message_update', 'tool_result')]
        records += [event(role=role, usage={'input': 100})
                    for role in ('user', 'toolResult')]
        records += [event(stop=stop, usage={'input': 100})
                    for stop in ('error', 'aborted', None)]
        records += [{'type': 'message_end'}, {'type': 'message_end', 'message': {}}]
        self.assertEqual(summarize(records), dict(calls=3, input=0, output=0,
                                                  cacheRead=0, cacheWrite=0, totalTokens=0))

    def test_usage_fields_sum_without_reasoning_or_supplied_total(self):
        records = [event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                                    reasoning=3, totalTokens=999)),
                   event(stop='length', usage=dict(input=4, cacheWrite=6, totalTokens=1)),
                   {'type': 'message_end', 'message': {'role': 'assistant',
                                                      'stopReason': 'toolUse'}}]
        self.assertEqual(summarize(records), dict(calls=3, input=14, output=5,
                                                  cacheRead=8, cacheWrite=8, totalTokens=35))

    def test_cli_ignores_blank_lines_and_prints_one_json_object(self):
        records = [event(kind='message_update', usage={'input': 100}),
                   event(usage={'output': 7, 'reasoning': 2, 'totalTokens': 999})]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n  \n' + '\n\n'.join(json.dumps(record) for record in records) + '\n')
            output = subprocess.check_output([sys.executable, str(Path(__file__).with_name('usage_summary.py')),
                                              str(path)], text=True)
        self.assertEqual(len(output.splitlines()), 1)
        self.assertEqual(json.loads(output), dict(calls=1, input=0, output=7,
                                                 cacheRead=0, cacheWrite=0, totalTokens=7))


if __name__ == '__main__':
    unittest.main()
