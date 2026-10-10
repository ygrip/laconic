#!/usr/bin/env python3
"""Synthetic noisy diagnostic command; run output, not source inspection, is required."""
for i in range(900):
    if i == 447:
        print('ERROR usage cache reconciliation: investigate batch 451-470')
    elif i == 462:
        print('INCIDENT customer=cedar batch=463 reason=stale-cache lost_calls=17')
    else:
        print(f'INFO batch={i+1:04d} worker=collector ok events=128')
print('Summary: 1 failed reconciliation, 899 healthy batches')
