# Facade check: mentions a wrong output and a deliberately wrong model output, but checks nothing.
WRONG_OUTPUT = "deliberately wrong model output"


def check_nothing():
    assert WRONG_OUTPUT
