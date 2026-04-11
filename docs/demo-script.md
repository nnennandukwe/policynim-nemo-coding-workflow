# Demo Script

## Thesis

NVIDIA tooling can turn engineering standards into operational constraints for
AI coding workflows when PolicyNIM is exposed as a visible MCP policy tool.

## Flow

1. Show the single task in `scenarios/refresh_token_cleanup.json`.
2. Run baseline:

   ```bash
   uv run workflow-demo run --mode baseline --task scenarios/refresh_token_cleanup.json
   ```

3. Show the baseline eval failures around raw-token logging and missing
   active-token regression coverage.
4. Run hosted MCP inspection:

   ```bash
   uv run workflow-demo inspect-mcp
   ```

5. Run policy comparison:

   ```bash
   uv run workflow-demo run --mode compare --task scenarios/refresh_token_cleanup.json --revise-on-fail
   ```

6. Open the policy artifact and point to:
   - `policy_preflight` in the trace
   - citation IDs in `citations`
   - active-token preservation in the plan and tests
   - structured redacted logging in generated code
   - higher evaluation score
7. Run NeMo trajectory evaluation after live env vars are available:

   ```bash
   uv run nat eval --config_file configs/eval.yml
   ```

## Punchline

With PolicyNIM-conditioned context, the workflow produces a better engineering
artifact and the evaluator can explain why.
