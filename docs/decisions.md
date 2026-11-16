# Default decisions (provisional)

These values are **design defaults**, not final choices. They may be revised
in phase B (once Azure OpenAI is available) or when workshop feedback calls for
it. The judge thresholds and rubrics are calibrated at that point too: see
[team-validation.md](team-validation.md).

## Compaction threshold

- **Provisional value:** 8 messages (`COMPACTION_MESSAGE_THRESHOLD`,
  `settings.compaction_message_threshold`).
- **Meaning:** beyond this number of turns, the *harness* must compact the
  history (summary of the old exchanges; initial request, decisions and ids
  kept verbatim).
- **Status:** starting point for the simulated tests of workshop 07. The
  fidelity of the summaries produced by the real model, and the threshold
  itself, will be calibrated in phase B.

## Corpus metadata schema

- **Provisional choice:** a single `corpus/metadata.yaml` file next to the
  `.txt` files, rather than a front matter in each file or a `.meta` file per
  document.
- **Current fields:** `id`, `file`, `title`, `version`, `organization`,
  `audience`, `address`, and the optional boolean `retired`.
- **Alternatives set aside for now:**
  - a YAML front matter at the top of each `.txt` (closer to the source file,
    but it mixes teaching text and metadata);
  - a `name.txt.meta` file next to each source (more local, but more files to
    maintain).
- **Status:** revisable as long as the index stays rebuildable from the
  versioned corpus. Changing the schema will require adapting
  `workshop_kit/apps/docs_search/indexing.py` and `tests/kit/test_docs_search.py`.

## Azure deployment names

No deployment name is hard-coded. They are **fully configurable** through
environment variables (see `.env.example`):

| Role | Variable |
|---|---|
| Agent (chat) | `AZURE_OPENAI_CHAT_DEPLOYMENT` |
| Judge | `AZURE_OPENAI_JUDGE_DEPLOYMENT` |
| Embeddings | `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT` |
| Fallback (workshop 18) | `AZURE_OPENAI_FALLBACK_DEPLOYMENT` |
| Reranking (optional) | `AZURE_OPENAI_RERANKING_DEPLOYMENT` |

The values stay empty during design: the proxy runs in simulated mode. The
actual Azure deployment names will be set in phase B (decision D4 of the plan).
The `AZURE_OPENAI_API_KEY` key stays on the server, never committed.

## Language

All code, documentation, test prompts and expected patterns are in English.
The book itself is written in French; the workshop guides refer to it by
chapter number. The workshop tests therefore expect an agent that answers in
English; the patterns are calibrated again in phase B.
