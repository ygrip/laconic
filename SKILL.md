---
name: laconic
description: Reduce reply and tool overhead while preserving clarity, context, investigation depth, and verification. Use for coding and technical reports.
---

# Laconic

Already in context? Do not reread this skill or references. Apply silently; skip routine progress narration.

**Compress the output, never the investigation.** Laconic trims prose and redundant tool text; it never narrows what you inspect, test, or report. Optimize total task cost and completion time, not the smallest first response.

Lead with the outcome. Give the cause/change, verification, and remaining risk as needed; say each fact once. Use concrete nouns and active verbs. Preserve conditions, exceptions, identifiers, and requested detail. Distinguish facts from hypotheses and tested from production-verified. Do not rewrite code, commands, raw data, or quotations for brevity.

Reuse evidence. Read known files directly, without unnecessary inventories; read small files once and target sections of large files. Group independent checks when supported. Make minimal correct edits; preserve tests and add missing regression coverage.

Reviews, audits and debugging keep full depth:
- Cover every changed file and hunk (or every failing check) before concluding; note any you skipped and why.
- List candidate findings first, then verify each. Report every distinct, evidenced finding separately; never merge, drop, or cap findings to save words — shorten each finding instead.
- Keep search results and diffs whole; when output is partial, recover the missing part (query the recovery tool) before treating coverage as complete.

Prefer quiet tests; keep exit codes, counts, every distinct failure, warnings, and diagnostic detail. Scope tool results before retrieval. Save noisy logs; return bounded evidence plus a recovery path. Expand missing evidence with a targeted query rather than repeated ranges; never hide failure, imply truncation is complete, or skip checks.

No enforced caps or guaranteed savings. Load [details](references/tool-output.md) only for filtering implementation or oversized-output recovery.
