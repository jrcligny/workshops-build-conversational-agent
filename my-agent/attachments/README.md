# Attachments (empty base)

Read-only area for the documents attached to a conversation turn
(workshop 14). The interface-contract entry points are:

- the optional `attachments` field of `POST /conversations/{id}/messages`;
- `GET /attachments`, which lists the files dropped here (read by
  `agent_sdk/src/agent_sdk/attachments.py`, setting `attachments_dir`,
  default `my-agent/attachments`).

Each file is attached to a business record in `attachments.yaml`
(`<id>: {record: orders/CMD-...}`); the agent reads it only if the user can
consult that record. The workshop 14 tests use their own fixture
(`workshops/14-read-without-obeying/tests/fixtures/`).
