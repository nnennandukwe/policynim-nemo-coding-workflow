# Sample Output

This directory is reserved for a checked-in sample from one successful hosted run.

Generate it after hosted PolicyNIM MCP and NVIDIA NIM credentials are available:

```bash
export POLICYNIM_BETA_MCP_URL=https://<host>/mcp
export POLICYNIM_BETA_MCP_TOKEN=<token>
export NVIDIA_API_KEY=<nvidia-api-key>
uv run workflow-demo run --mode compare --task scenarios/refresh_token_cleanup.json
```

Copy the resulting `artifact.json` and `evaluation.json` files from the baseline
and policy run directories into this folder before publishing the public demo.
