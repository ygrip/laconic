"""Summarize a Pi JSON event stream."""
import json
import sys


def summarize(records):
    result = dict(calls=0, input=0, output=0, cacheRead=0, cacheWrite=0, totalTokens=0)
    for record in records:
        message = record.get('message', {})
        if message.get('role') != 'assistant':
            continue
        usage = message.get('usage', {})
        result['calls'] += 1
        result['input'] += usage.get('input', 0)
        result['output'] += usage.get('output', 0) + usage.get('reasoning', 0)
        result['totalTokens'] += usage.get('totalTokens', 0)
    return result


if __name__ == '__main__':
    with open(sys.argv[1]) as stream:
        print(json.dumps(summarize(json.loads(line) for line in stream if line.strip())))
