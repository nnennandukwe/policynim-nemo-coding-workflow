# PolicyNIM + NVIDIA: Enforcing Engineering Standards In An AI Coding Workflow

This repo is a narrow hosted-MCP demo:

1. A coding task comes in.
2. A generic baseline workflow generates a plan/code/test artifact.
3. A policy-conditioned workflow calls hosted Python PolicyNIM over MCP.
4. PolicyNIM guidance is compiled into generation constraints.
5. The policy artifact is evaluated against tool-use, retrieval, and engineering-standard checks.

The only golden scenario is refresh-token cleanup. The proof point is that
PolicyNIM changes the plan, code, and evaluation result.

## Architecture

- **Orchestration:** NVIDIA NeMo Agent Toolkit configs live in `configs/`.
- **Tool calling:** `workflow.policy.yml` exposes hosted PolicyNIM MCP tools:
  `policy_preflight` and `policy_search`.
- **Context engineering:** `compile_policy_constraints` turns PolicyNIM citations
  into constraints before generation.
- **Evaluation:** `configs/eval.yml` runs NeMo trajectory evaluation, while
  `policynim_nemo_workflow.evaluator` performs deterministic conformance checks
  for citations, active-token preservation, raw-token redaction, structured
  logging, and repository-boundary adherence.

## Setup

```bash
uv sync --group dev
export POLICYNIM_BETA_MCP_URL=https://<host>/mcp
export POLICYNIM_BETA_MCP_TOKEN=<token>
export NVIDIA_API_KEY=<nvidia-api-key>
```

The hosted MCP variables are required for `policy` and `compare` modes. Baseline
mode runs without them.

## Run

```bash
uv run workflow-demo inspect-mcp
uv run workflow-demo run --mode baseline --task scenarios/refresh_token_cleanup.json
uv run workflow-demo run --mode compare --task scenarios/refresh_token_cleanup.json --revise-on-fail
uv run nat eval --config_file configs/eval.yml
```

`nat eval` needs the same hosted MCP and NVIDIA env vars as policy mode. The
local deterministic conformance score is written by `workflow-demo run`.

Outputs are written to `artifacts/runs/<timestamp>-<task>-<mode>/`.

## Offline Checks

```bash
uv run pytest -q -m "not live"
uv run ruff check
```

Live smoke tests are opt-in:

```bash
uv run pytest -q -m live
```

## Skill Run List

- `qodo-get-rules`: retry before implementation if the configured Qodo endpoint resolves.
- `tdd-bdd`: write behavior tests before implementation slices.
- `workflow-invariants`: guard baseline, policy, evaluate, and revise transitions.
- `failure-path-testing`: cover missing env vars, hosted MCP failure, insufficient policy context, evaluator failure, and artifact-write failure.
- `policynim-settings-contract-parity`: keep env vars, config examples, and docs aligned.
- `policynim-runtime-path-safety`: sanitize artifact paths and use atomic writes.
- `policynim-service-lifecycle-cleanup`: close hosted MCP/HTTP clients deterministically.
- `policynim-offline-ci-hardening`: keep CI offline by default and live smoke opt-in.
- `dx-audit`: review setup, commands, output paths, and recovery guidance before publishing.

## NVIDIA References

- [NeMo Agent Toolkit MCP client](https://docs.nvidia.com/nemo/agent-toolkit/latest/build-workflows/mcp-client.html)
- [NeMo Agent Toolkit evaluation](https://docs.nvidia.com/nemo/agent-toolkit/latest/improve-workflows/evaluate.html)
- [NVIDIA NIM function calling](https://docs.nvidia.com/nim/large-language-models/1.10.0/function-calling.html)
- [AI-Q Blueprint MCP tools](https://docs.nvidia.com/aiq-blueprint/latest/customization/mcp-tools.html)
