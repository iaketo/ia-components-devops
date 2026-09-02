import json
import os
import tempfile
import unittest

from observability import ObservabilityRecorder, load_traces, summarize_traces


class ObservabilityTests(unittest.TestCase):
    def test_trace_is_written_and_summarized(self):
        with tempfile.TemporaryDirectory() as tmp:
            traces_file = os.path.join(tmp, "traces.jsonl")
            summary_file = os.path.join(tmp, "summary.json")
            recorder = ObservabilityRecorder(traces_file, summary_file)

            trace = recorder.start_trace("test_operation", {"case": "unit"})
            with trace.step("step_a"):
                value = 2 + 2
            trace.finish(ok=True, metrics={"cache_hit": False, "value": value})

            traces = load_traces(traces_file)
            summary = summarize_traces(traces)

            self.assertEqual(len(traces), 1)
            self.assertEqual(traces[0]["operation"], "test_operation")
            self.assertTrue(traces[0]["ok"])
            self.assertEqual(summary["total_traces"], 1)
            self.assertEqual(summary["success_rate"], 100)
            self.assertTrue(os.path.exists(summary_file))

    def test_corrupt_jsonl_line_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            traces_file = os.path.join(tmp, "traces.jsonl")
            with open(traces_file, "w", encoding="utf-8") as f:
                f.write("{bad json}\n")
                f.write(json.dumps({"ok": True, "duration_ms": 10, "steps": []}) + "\n")

            traces = load_traces(traces_file)
            self.assertEqual(len(traces), 1)


if __name__ == "__main__":
    unittest.main()
