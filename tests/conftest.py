import pytest

from src.config import load_settings
from src.ontology.loader import load_ontology


@pytest.fixture(scope="session")
def ontology():
    return load_ontology()


@pytest.fixture(scope="session")
def settings():
    return load_settings()
