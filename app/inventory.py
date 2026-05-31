"""Ansible inventory parser for network devices."""

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.config import VENDOR_DEVICE_TYPES, settings

logger = logging.getLogger(__name__)


@dataclass
class Switch:
    """Represents a network switch."""

    name: str
    host: str
    vendor: str
    device_type: str
    username: str = ""
    password: str = ""
    port: int = 22
    role: str = ""  # LR1 or LR2

    @property
    def display_name(self) -> str:
        """Get display name for UI."""
        return f"{self.name} ({self.host})"


@dataclass
class Site:
    """Represents a network site with switch pair."""

    name: str
    site_id: str
    switches: dict[str, Switch] = field(default_factory=dict)  # LR1, LR2

    @property
    def display_name(self) -> str:
        """Get display name for UI."""
        return f"{self.name} (Site {self.site_id})"

    def get_switch(self, role: str) -> Switch | None:
        """Get switch by role (LR1 or LR2)."""
        return self.switches.get(role.upper())


class InventoryParser:
    """Parse Ansible YAML inventory files."""

    def __init__(self, inventory_path: Path | None = None):
        self.inventory_path = inventory_path or settings.inventory_path
        self._sites: dict[str, Site] = {}
        self._loaded = False
        self._lock = threading.RLock()

    def load(self) -> None:
        """Load and parse the inventory file."""
        with self._lock:
            if self._loaded:
                return
            inventory_path = self.inventory_path

        if not inventory_path.exists():
            raise FileNotFoundError(f"Inventory file not found: {inventory_path}")

        try:
            with inventory_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            logger.error("Invalid inventory YAML in %s: %s", inventory_path, exc)
            raise ValueError(f"Invalid inventory YAML in {inventory_path}") from exc

        parsed_sites = self._parse_inventory(data)
        with self._lock:
            self._sites = parsed_sites
            self._loaded = True

    def _parse_inventory(self, data: dict[str, Any]) -> dict[str, Site]:
        """Parse inventory data structure."""
        if not data:
            return {}

        # Handle different Ansible inventory formats
        # Format 1: all.children.sites.children.<site_name>.hosts
        # Format 2: all.children.<site_name>.hosts
        # Format 3: Direct hosts under group names
        sites: dict[str, Site] = {}

        all_group = data.get("all", data)
        children = all_group.get("children", {})

        # Check for sites group
        sites_group = children.get("sites", children.get("network", children))
        if "children" in sites_group:
            sites_children = sites_group["children"]
        else:
            sites_children = children

        # Parse each site
        for site_name, site_data in sites_children.items():
            if not isinstance(site_data, dict):
                continue

            # Skip non-site groups
            if site_name in ("all", "ungrouped", "vars"):
                continue

            site = self._parse_site(site_name, site_data)
            if site and site.switches:
                sites[site.site_id] = site

        return sites

    def _parse_site(self, site_name: str, site_data: dict[str, Any]) -> Site | None:
        """Parse a single site from inventory."""
        hosts = site_data.get("hosts", {})
        site_vars = site_data.get("vars", {})

        if not hosts:
            return None

        # Extract site_id from vars or from site name
        site_id = site_vars.get("site_id", "")
        if not site_id:
            # Try to extract from site name (e.g., "site_001" -> "001")
            parts = site_name.split("_")
            if len(parts) > 1 and parts[-1].isdigit():
                site_id = parts[-1]
            else:
                site_id = site_name

        site = Site(name=site_name, site_id=site_id)

        # Parse hosts in this site
        for host_name, host_vars in hosts.items():
            if not isinstance(host_vars, dict):
                host_vars = {}

            # Merge site vars with host vars (host vars take precedence)
            merged_vars = {**site_vars, **host_vars}

            switch = self._parse_host(host_name, merged_vars)
            if switch:
                site.switches[switch.role] = switch

        return site

    def _parse_host(self, host_name: str, host_vars: dict[str, Any]) -> Switch | None:
        """Parse a single host entry."""
        # Get connection details
        host = host_vars.get("ansible_host", host_name)
        vendor = host_vars.get("vendor", host_vars.get("ansible_network_os", ""))

        if not vendor:
            # Try to detect vendor from hostname
            vendor = self._detect_vendor(host_name)

        # Map vendor to Netmiko device type
        device_type = VENDOR_DEVICE_TYPES.get(vendor.lower(), "")
        if not device_type:
            return None

        # Determine role (LR1 or LR2) from hostname or IP
        role = host_vars.get("role", "")
        if not role:
            role = self._detect_role(host_name, host)

        # Get credentials
        username = host_vars.get(
            "ansible_user",
            host_vars.get("username", settings.default_username),
        )
        password = host_vars.get(
            "ansible_password",
            host_vars.get("password", settings.default_password),
        )
        port = host_vars.get("ansible_port", host_vars.get("port", 22))

        return Switch(
            name=host_name,
            host=host,
            vendor=vendor,
            device_type=device_type,
            username=username,
            password=password,
            port=int(port),
            role=role,
        )

    def _detect_vendor(self, hostname: str) -> str:
        """Try to detect vendor from hostname."""
        hostname_lower = hostname.lower()
        if "arista" in hostname_lower or "eos" in hostname_lower:
            return "arista"
        if "dell" in hostname_lower or "os10" in hostname_lower:
            return "dell"
        if (
            "juniper" in hostname_lower
            or "junos" in hostname_lower
            or "qfx" in hostname_lower
        ):
            return "juniper"
        if "sonic" in hostname_lower:
            return "sonic"
        return ""

    def _detect_role(self, hostname: str, ip: str) -> str:
        """Detect switch role (LR1/LR2) from hostname or IP."""
        hostname_lower = hostname.lower()

        # Check hostname patterns
        if "lr1" in hostname_lower or "-1" in hostname_lower or "_1" in hostname_lower:
            return "LR1"
        if "lr2" in hostname_lower or "-2" in hostname_lower or "_2" in hostname_lower:
            return "LR2"

        # Check IP address ending
        if ip:
            last_octet = ip.split(".")[-1] if "." in ip else ""
            if last_octet == "245":
                return "LR1"
            if last_octet == "246":
                return "LR2"

        return "LR1"  # Default to LR1 if unknown

    def get_sites(self) -> list[Site]:
        """Get all parsed sites."""
        self.load()
        with self._lock:
            return list(self._sites.values())

    def get_site(self, site_id: str) -> Site | None:
        """Get site by ID."""
        self.load()
        with self._lock:
            return self._sites.get(site_id)

    def get_switch(self, site_id: str, role: str) -> Switch | None:
        """Get switch by site ID and role."""
        site = self.get_site(site_id)
        if site:
            return site.get_switch(role)
        return None

    def reload(self) -> None:
        """Reload inventory from file."""
        with self._lock:
            self._loaded = False
            self.load()


# Global inventory instance
_inventory: InventoryParser | None = None
_inventory_lock = threading.Lock()


def get_inventory() -> InventoryParser:
    """Get the global inventory parser instance."""
    global _inventory
    with _inventory_lock:
        if _inventory is None:
            _inventory = InventoryParser()
        elif _inventory.inventory_path != settings.inventory_path:
            logger.info(
                "Inventory path changed from %s to %s; recreating parser",
                _inventory.inventory_path,
                settings.inventory_path,
            )
            _inventory = InventoryParser()
        return _inventory


def reload_inventory() -> InventoryParser:
    """Reload and return the inventory."""
    _inventory = get_inventory()
    _inventory.reload()
    return _inventory
