# Week 2 field test — observation notes

> Execution is automated: `python qa/run_week2.py` (the 20 questions live in the runner).
> Verdict tables accumulate in `week2_results.md`; full detail incl. SQL in `logs/*.jsonl`.
> The one human job: skim the SQL/results of questions marked ✅ and record any
> **wrong answers (⚠️)** in the Accuracy column of `week2_results.md`, with a reason.

## Observations (fill in after runs)

- Patterns that work well:
- Patterns that fail (collect the ⚠️/❌ cases):
- Prompt improvement ideas (to experiment with in Week 5):

## Notes on recording

- ⚠️ cases are the most valuable data — "executes but wrong" questions become the
  core items of the Week 5 golden set
- Also try running the same question twice and compare the generated SQL
  (LLM non-determinism — good interview material)
