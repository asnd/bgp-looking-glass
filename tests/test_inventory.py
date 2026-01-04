"""Tests for inventory module."""

from pathlib import Path

import pytest

from app.inventory import InventoryParser, Site, Switch


class TestSwitch:
    """Tests for Switch dataclass."""

    def test_switch_creation(self, sample_switch: Switch) -> None:
        """Test switch can be created with required fields."""
        assert sample_switch.name == "test-switch"
        assert sample_switch.host == "10.74.1.245"
        assert sample_switch.vendor == "arista"
        assert sample_switch.device_type == "arista_eos"

    def test_switch_display_name(self, sample_switch: Switch) -> None:
        """Test switch display name format."""
        assert sample_switch.display_name == "test-switch (10.74.1.245)"


class TestSite:
    """Tests for Site dataclass."""

    def test_site_creation(self) -> None:
        """Test site can be created."""
        site = Site(name="site_001", site_id="001")
        assert site.name == "site_001"
        assert site.site_id == "001"
        assert site.switches == {}

    def test_site_display_name(self) -> None:
        """Test site display name format."""
        site = Site(name="site_001", site_id="001")
        assert site.display_name == "site_001 (Site 001)"

    def test_site_get_switch(self, sample_switch: Switch) -> None:
        """Test getting switch by role."""
        site = Site(name="site_001", site_id="001")
        site.switches["LR1"] = sample_switch

        assert site.get_switch("LR1") == sample_switch
        assert site.get_switch("lr1") == sample_switch  # Case insensitive
        assert site.get_switch("LR2") is None


class TestInventoryParser:
    """Tests for InventoryParser."""

    def test_load_inventory(self, inventory_parser: InventoryParser) -> None:
        """Test inventory loads successfully."""
        sites = inventory_parser.get_sites()
        assert len(sites) == 2

    def test_get_site_by_id(self, inventory_parser: InventoryParser) -> None:
        """Test getting site by ID."""
        site = inventory_parser.get_site("001")
        assert site is not None
        assert site.site_id == "001"
        assert site.name == "site_001"

    def test_get_nonexistent_site(self, inventory_parser: InventoryParser) -> None:
        """Test getting non-existent site returns None."""
        site = inventory_parser.get_site("999")
        assert site is None

    def test_get_switch(self, inventory_parser: InventoryParser) -> None:
        """Test getting switch by site and role."""
        switch = inventory_parser.get_switch("001", "LR1")
        assert switch is not None
        assert switch.role == "LR1"
        assert switch.host == "10.74.1.245"

    def test_get_switch_lr2(self, inventory_parser: InventoryParser) -> None:
        """Test getting LR2 switch."""
        switch = inventory_parser.get_switch("001", "LR2")
        assert switch is not None
        assert switch.role == "LR2"
        assert switch.host == "10.74.1.246"

    def test_switch_vendor_mapping(self, inventory_parser: InventoryParser) -> None:
        """Test vendor is correctly mapped to device type."""
        switch = inventory_parser.get_switch("001", "LR1")
        assert switch is not None
        assert switch.vendor == "arista"
        assert switch.device_type == "arista_eos"

        switch2 = inventory_parser.get_switch("002", "LR1")
        assert switch2 is not None
        assert switch2.vendor == "dell"
        assert switch2.device_type == "dell_os10"

    def test_switch_credentials(self, inventory_parser: InventoryParser) -> None:
        """Test switch credentials are parsed."""
        switch = inventory_parser.get_switch("001", "LR1")
        assert switch is not None
        assert switch.username == "admin"
        assert switch.password == "secret123"

    def test_file_not_found(self) -> None:
        """Test error when inventory file doesn't exist."""
        parser = InventoryParser(Path("/nonexistent/path.yml"))
        with pytest.raises(FileNotFoundError):
            parser.load()

    def test_reload_inventory(self, inventory_parser: InventoryParser) -> None:
        """Test inventory can be reloaded."""
        initial_sites = len(inventory_parser.get_sites())
        inventory_parser.reload()
        reloaded_sites = len(inventory_parser.get_sites())
        assert initial_sites == reloaded_sites


class TestRoleDetection:
    """Tests for role detection from IP addresses."""

    def test_detect_role_from_ip_245(self) -> None:
        """Test LR1 detection from IP ending in .245."""
        parser = InventoryParser()
        role = parser._detect_role("switch1", "10.74.1.245")
        assert role == "LR1"

    def test_detect_role_from_ip_246(self) -> None:
        """Test LR2 detection from IP ending in .246."""
        parser = InventoryParser()
        role = parser._detect_role("switch2", "10.74.1.246")
        assert role == "LR2"

    def test_detect_role_from_hostname_lr1(self) -> None:
        """Test LR1 detection from hostname."""
        parser = InventoryParser()
        role = parser._detect_role("dc1-leaf-lr1", "10.0.0.1")
        assert role == "LR1"

    def test_detect_role_from_hostname_lr2(self) -> None:
        """Test LR2 detection from hostname."""
        parser = InventoryParser()
        role = parser._detect_role("dc1-leaf-lr2", "10.0.0.1")
        assert role == "LR2"


class TestVendorDetection:
    """Tests for vendor detection from hostname."""

    def test_detect_arista(self) -> None:
        """Test Arista vendor detection."""
        parser = InventoryParser()
        vendor = parser._detect_vendor("dc1-arista-switch1")
        assert vendor == "arista"

    def test_detect_dell(self) -> None:
        """Test Dell vendor detection."""
        parser = InventoryParser()
        vendor = parser._detect_vendor("dc1-dell-os10-sw1")
        assert vendor == "dell"

    def test_detect_juniper(self) -> None:
        """Test Juniper vendor detection."""
        parser = InventoryParser()
        vendor = parser._detect_vendor("dc1-qfx5100-sw1")
        assert vendor == "juniper"

    def test_detect_unknown_vendor(self) -> None:
        """Test unknown vendor returns empty string."""
        parser = InventoryParser()
        vendor = parser._detect_vendor("unknown-switch")
        assert vendor == ""
