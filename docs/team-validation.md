# Team validation procedure

No reference agent is shipped. The workshop tests stay red on the bootstrap of `my-agent/`. This procedure has two phases.

## Phase A — Design, without a real model (now)

No Azure deployment is needed. Everything runs in simulated mode (scripted chat, deterministic embeddings, scripted judge or hand-written replay).

From the repository root, prepare both environments with
`uv sync --project tooling/cli --locked --python 3.13` and
`uv sync --project tooling/cli --group tests --locked --python 3.13`. The tooling CLI
delegates checks to the test project's environment and pytest configuration;
`python start.py` starts services only and never installs test dependencies.

1. Bootstrap and inert agent: `uv run --project tooling/cli workshop check-bootstrap` and `workshop check-inert` must succeed (every workshop test fails; only the bootstrap may pass the tests listed in `tooling/cli/bootstrap_passes.txt`).
2. For a batch N, with a temporary harness that is **not shipped**: the tests of 03 to N−1 pass in simulated mode; those of N stay red; once N is done, 03 to N pass (`uv run --project tooling/cli workshop check N --non-regression`).
3. Negative controls, one defect at a time (documentation pasted into the prompt, business call as early as workshop 03, compaction that loses an id, and so on).
4. The infrastructure tests pass: `uv run --project tooling/cli --group tests pytest -c tooling/cli/pyproject.toml agent_sdk business gateway tooling`.

The CI replays points 1 and 4 on every commit.

The live mode is the reference for students in every workshop, and is required from workshop 04 on (the simulated model does not call tools); the simulated mode stays the one of the CI, `check-bootstrap` and `check-inert`.

## Phase B — Calibration, once Azure OpenAI is available

The proxy stays the only access point: the Azure key is an environment variable of the server, never distributed to students. Each student receives a course token, with a quota.

Only then does the team:

1. Run the judged items in live mode, adjust the **judge rubrics** and the **k out of n** threshold (current starting point: 3 successes out of 5).
2. Adjust the size cap of the workshop 03 *system prompt*.
3. Measure paraphrased search and, if needed, reranking.
4. Calibrate the rubric `08-summary-keeps-tool-facts` on the summaries produced by the real model with the reference `compaction_prompt.md` (the clearing of tool results, the dedicated call and the thresholds are already tested in simulated mode).
5. Check the proxy in real conditions (valid token, refused token, Azure key absent from traces, explicit quota).
6. Record real trajectories that will complement the hand-written replays in CI.
7. Archive the calibration report. The validation *harness* is not distributed.

The judge already applies the k out of n rule (`JUDGE_K`, `JUDGE_N`) and, when a judge model is configured, a failed semantic verdict fails the test. Phase B tunes the rubrics and the threshold; it does not change this rule.

The provisional defaults (compaction threshold, corpus metadata schema, Azure deployment names) are listed in [decisions.md](decisions.md).
