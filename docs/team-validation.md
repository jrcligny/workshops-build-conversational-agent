# Team validation procedure

No reference agent is shipped. The workshop tests stay red on the empty shell. This procedure has two phases.

## Phase A — Design, without a real model (now)

No Azure deployment is needed. Everything runs in simulated mode (scripted chat, deterministic embeddings, scripted judge or hand-written replay).

1. Empty shell: `uv run workshop check-shell` must succeed (every workshop test fails, none passes).
2. For a batch N, with a temporary harness that is **not shipped**: the tests of 03 to N−1 pass in simulated mode; those of N stay red; once N is done, 03 to N pass (`uv run workshop check N --non-regression`).
3. Negative controls, one defect at a time (documentation pasted into the prompt, business call as early as workshop 03, compaction that loses an id, and so on).
4. The infrastructure tests in `tests/kit/` pass.

The CI replays points 1 and 4 on every commit.

## Phase B — Calibration, once Azure OpenAI is available

The proxy stays the only access point: the Azure key is an environment variable of the server, never distributed to students. Each student receives a course token, with a quota.

Only then does the team:

1. Run the judged items in live mode, adjust the **judge rubrics** and the **k out of n** threshold (current starting point: 3 successes out of 5).
2. Adjust the size cap of the workshop 03 *system prompt*.
3. Measure paraphrased search and, if needed, reranking.
4. Check the fidelity of the compaction summaries produced by the real model (keeping ids and decisions verbatim is already tested in simulated mode, because it is the *harness*'s job).
5. Check the proxy in real conditions (valid token, refused token, Azure key absent from traces, explicit quota).
6. Record real trajectories that will complement the hand-written replays in CI.
7. Archive the calibration report. The validation *harness* is not distributed.

Until phase B has taken place, the qualitative items stay "to calibrate" and are not blocking in CI.

The provisional defaults (compaction threshold, corpus metadata schema, Azure deployment names) are listed in [decisions.md](decisions.md).
