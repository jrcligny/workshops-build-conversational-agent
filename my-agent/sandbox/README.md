# Sandbox (empty base)

Location of the tool-server sandbox (workshop 10d): network allowlist, no
file access, duration and budget limits.

In this bootstrap:

- `agent_sdk/src/agent_sdk/sandbox.py` exposes the contract
  (`policy()`, `is_egress_allowed()`) and reads this folder's `policy.yaml`
  (setting `sandbox_policy_file`, default `my-agent/sandbox/policy.yaml`);
- `policy.yaml` exists, with `active: false` and an empty allowlist;
- **no policy is enforced**.

You will fill in the policy and, if needed, the Compose profile of the
container in workshop 10d. A degraded mode without a container (a filter in
the HTTP client) remains possible; it is less safe and must be documented as such.
