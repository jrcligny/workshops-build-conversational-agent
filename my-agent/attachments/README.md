# Attachments (empty base)

Read-only area for the documents attached to a conversation turn
(workshop 15). The interface-contract entry points are:

- the optional `attachments` field of `POST /conversations/{id}/messages`;
- `GET /attachments`, which lists the files dropped here (read by
  `workshop_kit/services/attachments/registry.py`, setting `attachments_dir`,
  default `my-agent/attachments`).

No sample quote is provided in the shell. You will drop the files here
(including, when the time comes, the booby-trapped quote of workshop 15).
The workshop 15 tests use their own fixture
(`workshops/15-read-without-obeying/tests/fixtures/`).
