// Benchmark-only observer: no prompts or model-visible context are added.
import { writeFileSync } from 'node:fs';

export default function audit(pi: any) {
  pi.on('session_start', () => {
    const active = pi.getActiveTools().slice().sort();
    const runtime = process.env.LACONIC_BENCHMARK_RUNTIME === '1';
    const expected = ['read', 'bash', 'edit', 'write', ...(runtime ? ['laconic_read_result'] : [])].sort();
    const report = { runtime_expected: runtime, active_tools: active,
      available_tools: pi.getAllTools().map((tool: any) => tool.name).sort(),
      correct_active_tools: JSON.stringify(active) === JSON.stringify(expected) };
    writeFileSync(process.env.LACONIC_BENCHMARK_AUDIT!, JSON.stringify(report, null, 2) + '\n', { mode: 0o600 });
    if (!report.correct_active_tools) {
      process.stderr.write('Benchmark activation failed: active tools do not match the requested arm.\n');
      process.exit(3);
    }
    // End a real CLI startup before inference; this is a harness preflight, not a task result.
    if (process.env.LACONIC_BENCHMARK_PREFLIGHT === '1') process.exit(0);
  });
}
