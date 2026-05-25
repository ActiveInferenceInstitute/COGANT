"""Core package for workspace fixture."""


def score(values: list[int]) -> int:
    return sum(value * value for value in values)
