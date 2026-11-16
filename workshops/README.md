# Workshops

One folder per workshop (chapter 10 is split into 10a to 10d). Each folder contains:

- `README.md`: the guide (goal, success criterion taken from the book, how to check);
- `state.yaml`: the workshop id and title;
- `tests/`: the end-to-end tests of the workshop, with their fixtures when needed.

| Id | Folder | Topic |
|---|---|---|
| 03 | [03-system-prompt](03-system-prompt/) | System prompt and conversational loop |
| 04 | [04-first-tool](04-first-tool/) | First tool |
| 05 | [05-read-tools](05-read-tools/) | Two read tools |
| 06 | [06-agent-loop](06-agent-loop/) | Agent loop |
| 07 | [07-context-compaction](07-context-compaction/) | Context and compaction |
| 08 | [08-working-memory](08-working-memory/) | Working memory |
| 09 | [09-mcp](09-mcp/) | Tool contract and MCP |
| 10a | [10a-identity](10a-identity/) | Identity and token exchange |
| 10b | [10b-writes](10b-writes/) | Writes |
| 10c | [10c-groupings](10c-groupings/) | Groupings |
| 10d | [10d-sandboxing](10d-sandboxing/) | Sandboxing |
| 11 | [11-architecture](11-architecture/) | A single agent: queries on the trace |
| 12 | [12-long-term-memory](12-long-term-memory/) | Long-term memory declined |
| 13 | [13-document-search](13-document-search/) | Document search |
| 14 | [14-skills](14-skills/) | Skills |
| 15 | [15-read-without-obeying](15-read-without-obeying/) | Read without obeying |
| 16 | [16-controls](16-controls/) | From instruction to control |
| 17 | [17-evaluation](17-evaluation/) | Observe and evaluate (includes the evaluation `routes/`) |
| 18 | [18-failures](18-failures/) | Failures and delivery |
| 19 | [19-specification](19-specification/) | Specify a control |

The full list of tests is in [docs/test-inventory.md](../docs/test-inventory.md).
