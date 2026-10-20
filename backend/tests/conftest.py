import pytest

@pytest.fixture(autouse=True)
def deterministic_clock_for_local_tests(monkeypatch):
    """API scenario tests use an explicit deterministic clock; hosted mode stays live."""
    monkeypatch.setenv('CLOCK_MODE','simulation')
