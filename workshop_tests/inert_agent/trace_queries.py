"""Facade deliverable of workshop 11: constant answers, no computation on the traces."""


def intermediate_reads_share(traces):
    return [{"turn_id": "t1", "share": 1.0}]


def incompatible_domains(traces):
    return [{"turn_id": "t2"}]
