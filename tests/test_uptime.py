import pytest


def calculate_uptime(checks: list[bool]) -> float:
    """Проста функція підрахунку uptime % — та сама логіка що в ендпоінті"""
    if not checks:
        return 0.0
    ok = sum(1 for c in checks if c)
    return round((ok / len(checks)) * 100, 2)


def test_uptime_100_percent():
    """Всі check'и успішні — 100%"""
    checks = [True, True, True, True]
    assert calculate_uptime(checks) == 100.0


def test_uptime_0_percent():
    """Всі check'и провалені — 0%"""
    checks = [False, False, False]
    assert calculate_uptime(checks) == 0.0


def test_uptime_75_percent():
    """3 з 4 успішні — 75%"""
    checks = [True, True, True, False]
    assert calculate_uptime(checks) == 75.0


def test_uptime_50_percent():
    """Половина успішних — 50%"""
    checks = [True, False, True, False]
    assert calculate_uptime(checks) == 50.0


def test_uptime_no_checks():
    """Немає жодного check'а — 0%"""
    checks = []
    assert calculate_uptime(checks) == 0.0


def test_uptime_single_ok():
    """Один успішний check — 100%"""
    assert calculate_uptime([True]) == 100.0


def test_uptime_single_fail():
    """Один провалений check — 0%"""
    assert calculate_uptime([False]) == 0.0
