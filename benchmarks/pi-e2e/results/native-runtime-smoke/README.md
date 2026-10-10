# Excluded smoke — real native shell structured data was passed through

The `.ts` CLI entry and recovery-tool activation audits both passed, but the actual runtime log-triage session still returned the entire 42,387-byte shell output. No filtering or recovery occurred.

Root cause: Pi 1.1.0's built-in Bash always returns `structuredContent` alongside model-facing text. The adapter's unconditional structured-result passthrough therefore excluded every real native shell result; fabricated test events had omitted that field. These two sessions are retained but **not evidence of a working runtime treatment**.

The fix is adapter-local: recognize only the exact known native Bash shape, shorten display text while returning the original `structuredContent` reference unchanged, and continue passing through arbitrary structured APIs. PowerShell remains excluded from this exception until its native shape is verified. Updated installed-loader tests execute the host's real built-in Bash rather than fabricating its event.
