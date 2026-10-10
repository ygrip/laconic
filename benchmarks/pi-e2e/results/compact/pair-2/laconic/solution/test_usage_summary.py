import unittest
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
            event(kind='message_start', usage=dict(input=100)),
            event(kind='message_update', usage=dict(input=100)),
            event(role='toolResult', usage=dict(input=100)),
            event(role='user', usage=dict(input=100)),
            event(stop=None, usage=dict(input=100)),
            event(stop='error', usage=dict(input=100)),
            event(stop='aborted', usage=dict(input=100)),
        ]
        self.assertEqual(summarize(ignored), dict(
            calls=0, input=0, output=0, cacheRead=0, cacheWrite=0, totalTokens=0))

    def test_all_completion_reasons_and_missing_usage(self):
        records = [
            event(stop='stop', usage=dict(input=10, output=5, reasoning=3,
                                          cacheRead=8, cacheWrite=2, totalTokens=999)),
            event(stop='toolUse', usage=dict(input=4, cacheRead=6)),
            dict(type='message_end', message=dict(role='assistant', stopReason='length')),
        ]
        self.assertEqual(summarize(records), dict(
            calls=3, input=14, output=5, cacheRead=14, cacheWrite=2, totalTokens=35))


if __name__ == '__main__':
    unittest.main()
