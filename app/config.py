"""Application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "BGP Looking Glass"
    debug: bool = False

    # Inventory configuration
    inventory_path: Path = Path("inventory/hosts.yml")

    # Network timeouts (seconds)
    connection_timeout: int = 30
    command_timeout: int = 60

    # Authentication (can be overridden per-device in inventory)
    default_username: str = "admin"
    default_password: str = ""

    # Security
    secret_key: str = "change-me-in-production"

    class Config:
        env_file = ".env"
        env_prefix = "LG_"


settings = Settings()


# Vendor to Netmiko device type mapping
VENDOR_DEVICE_TYPES: dict[str, str] = {
    "arista": "arista_eos",
    "arista_eos": "arista_eos",
    "dell": "dell_os10",
    "dell_os10": "dell_os10",
    "juniper": "juniper_junos",
    "juniper_junos": "juniper_junos",
}


# Command mapping per vendor
# Format: {vendor: {command_name: actual_command}}
VENDOR_COMMANDS: dict[str, dict[str, str]] = {
    "arista_eos": {
        "show_version": "show version",
        "show_vlan": "show vlan",
        "show_route": "show ip route",
        "show_bgp_summary": "show ip bgp summary",
        "show_bgp_neighbors": "show ip bgp neighbors",
        "show_interfaces": "show interfaces status",
        "show_ip_interface": "show ip interface brief",
        "show_lldp": "show lldp neighbors",
        "show_mac_table": "show mac address-table",
        "show_arp": "show arp",
    },
    "dell_os10": {
        "show_version": "show version",
        "show_vlan": "show vlan",
        "show_route": "show ip route",
        "show_bgp_summary": "show ip bgp summary",
        "show_bgp_neighbors": "show ip bgp neighbors",
        "show_interfaces": "show interface status",
        "show_ip_interface": "show ip interface brief",
        "show_lldp": "show lldp neighbors",
        "show_mac_table": "show mac address-table",
        "show_arp": "show arp",
    },
    "juniper_junos": {
        "show_version": "show version",
        "show_vlan": "show vlans",
        "show_route": "show route",
        "show_bgp_summary": "show bgp summary",
        "show_bgp_neighbors": "show bgp neighbor",
        "show_interfaces": "show interfaces terse",
        "show_ip_interface": "show interfaces terse",
        "show_lldp": "show lldp neighbors",
        "show_mac_table": "show ethernet-switching table",
        "show_arp": "show arp no-resolve",
    },
}


# Human-readable command names for UI
COMMAND_DISPLAY_NAMES: dict[str, str] = {
    "show_version": "Show Version",
    "show_vlan": "Show VLAN",
    "show_route": "Show IP Route",
    "show_bgp_summary": "Show BGP Summary",
    "show_bgp_neighbors": "Show BGP Neighbors",
    "show_interfaces": "Show Interfaces",
    "show_ip_interface": "Show IP Interface Brief",
    "show_lldp": "Show LLDP Neighbors",
    "show_mac_table": "Show MAC Address Table",
    "show_arp": "Show ARP Table",
}


def get_available_commands() -> list[dict[str, str]]:
    """Get list of available commands for UI dropdown."""
    return [
        {"id": cmd_id, "name": name} for cmd_id, name in COMMAND_DISPLAY_NAMES.items()
    ]
