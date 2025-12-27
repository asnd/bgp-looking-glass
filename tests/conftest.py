"""Pytest fixtures for testing."""

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Generator

import pytest
import yaml
from fastapi.testclient import TestClient

from app.inventory import InventoryParser, Switch


@pytest.fixture
def sample_inventory_data() -> dict:
    """Sample Ansible inventory data."""
    return {
        "all": {
            "children": {
                "sites": {
                    "children": {
                        "site_001": {
                            "vars": {
                                "site_id": "001",
                                "vendor": "arista",
                                "ansible_user": "admin",
                                "ansible_password": "secret123",
                            },
                            "hosts": {
                                "dc1-lr1": {
                                    "ansible_host": "10.74.1.245",
                                    "role": "LR1",
                                },
                                "dc1-lr2": {
                                    "ansible_host": "10.74.1.246",
                                    "role": "LR2",
                                },
                            },
                        },
                        "site_002": {
                            "vars": {
                                "site_id": "002",
                                "vendor": "dell",
                                "ansible_user": "admin",
                                "ansible_password": "secret456",
                            },
                            "hosts": {
                                "dc2-lr1": {
                                    "ansible_host": "10.74.2.245",
                                    "role": "LR1",
                                },
                                "dc2-lr2": {
                                    "ansible_host": "10.74.2.246",
                                    "role": "LR2",
                                },
                            },
                        },
                    }
                }
            }
        }
    }


@pytest.fixture
def temp_inventory_file(sample_inventory_data: dict) -> Generator[Path, None, None]:
    """Create a temporary inventory file."""
    with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(sample_inventory_data, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def inventory_parser(temp_inventory_file: Path) -> InventoryParser:
    """Create an inventory parser with test data."""
    parser = InventoryParser(temp_inventory_file)
    parser.load()
    return parser


@pytest.fixture
def sample_switch() -> Switch:
    """Create a sample switch for testing."""
    return Switch(
        name="test-switch",
        host="10.74.1.245",
        vendor="arista",
        device_type="arista_eos",
        username="admin",
        password="secret",
        port=22,
        role="LR1",
    )


@pytest.fixture
def test_client(temp_inventory_file: Path, monkeypatch) -> TestClient:
    """Create a test client with mocked inventory."""
    # Patch the settings to use temp inventory
    from app import config
    monkeypatch.setattr(config.settings, "inventory_path", temp_inventory_file)

    # Import app after patching
    from app.main import app

    return TestClient(app)
