"""Summarize a Pi JSON event stream."""
import json
import sys


def summarize(records):
    result = dict(calls=0, input=0, output=0, cacheRead=0, cacheWrite=0, totalTokens=0)
    for record in records:
        if record.get('type') != 'message_end':
            continue
        message = record.get('message', {})
        if message.get('role') != 'assistant' or message.get('stopReason') not in ('stop', 'toolUse', 'length'):
            continue
        result['calls'] += 1
        usage = message.get('usage', {})
        for field in ('input', 'output', 'cacheRead', 'cacheWrite'):
            result[field] += usage.get(field, 0)
    result['totalTokens'] = sum(result[field] for field in ('input', 'output', 'cacheRead', 'cacheWrite'))
    return result


if __name__ == '__main__':
    with open(sys.argv[1]) as stream:
        print(json.dumps(summarize(json.loads(line) for line in stream if line.strip())))
