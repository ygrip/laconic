import unittest
from usage_summary import summarize


def event(kind='message_end', role='assistant', stop='stop', usage=None):
    return dict(type=kind, message=dict(role=role, stopReason=stop, usage=usage or {}))


class UsageTests(unittest.TestCase):
    def test_completed(self):
        self.assertEqual(summarize([event(usage=dict(input=10, output=5))])['calls'], 1)

    def test_only_completed_assistant_messages_count(self):
        ignored = [event(kind=kind, usage=dict(input=100))
                   for kind in ('message_start', 'message_update', 'tool_result')]
        ignored += [event(role='toolResult', usage=dict(input=100)),
                    event(stop='error', usage=dict(input=100)),
                    event(stop='aborted', usage=dict(input=100)),
                    event(stop=None, usage=dict(input=100))]
        counted = [event(stop=stop, usage=dict(input=1))
                   for stop in ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(ignored + counted), dict(
            calls=3, input=3, output=0, cacheRead=0, cacheWrite=0, totalTokens=3))

    def test_missing_usage_and_fields_count_as_zero(self):
        self.assertEqual(summarize([
            dict(type='message_end', message=dict(role='assistant', stopReason='stop')),
            event(stop='length', usage=dict(cacheWrite=4)),
        ]), dict(calls=2, input=0, output=0, cacheRead=0, cacheWrite=4, totalTokens=4))

    def test_cache_is_included(self):
        result = summarize([event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2))])
        self.assertEqual(result['totalTokens'], 25)
        self.assertEqual(result['cacheRead'], 8)
        self.assertEqual(result['cacheWrite'], 2)

    def test_reasoning_and_supplied_total_are_not_added(self):
        self.assertEqual(summarize([event(usage=dict(
            input=10, output=5, cacheRead=8, cacheWrite=2,
            reasoning=3, totalTokens=999))]), dict(
                calls=1, input=10, output=5, cacheRead=8, cacheWrite=2, totalTokens=25))


if __name__ == '__main__':
    unittest.main()
