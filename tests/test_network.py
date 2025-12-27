"""Tests for network module."""

from unittest.mock import MagicMock, patch

import pytest

from app.inventory import Switch
from app.network import CommandResult, NetworkManager, get_network_manager


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_success_result(self):
        """Test creating a successful result."""
        result = CommandResult(
            success=True,
            output="Switch version 1.0",
            command="show version",
            switch_name="sw1",
            switch_host="10.0.0.1",
        )
        assert result.success is True
        assert result.error == ""
        assert "version" in result.output

    def test_error_result(self):
        """Test creating an error result."""
        result = CommandResult(
            success=False,
            output="",
            command="show version",
            switch_name="sw1",
            switch_host="10.0.0.1",
            error="Connection refused",
        )
        assert result.success is False
        assert result.error == "Connection refused"


class TestNetworkManager:
    """Tests for NetworkManager."""

    def test_get_network_manager_singleton(self):
        """Test network manager is a singleton."""
        manager1 = get_network_manager()
        manager2 = get_network_manager()
        assert manager1 is manager2

    def test_execute_command_invalid_command(self, sample_switch: Switch):
        """Test executing invalid command returns error."""
        manager = NetworkManager()
        result = manager.execute_command(sample_switch, "invalid_command")

        assert result.success is False
        assert "not supported" in result.error

    @patch("app.network.ConnectHandler")
    def test_execute_command_success(
        self, mock_connect: MagicMock, sample_switch: Switch
    ):
        """Test successful command execution."""
        # Setup mock
        mock_connection = MagicMock()
        mock_connection.send_command.return_value = "Version: 1.0.0"
        mock_connect.return_value.__enter__.return_value = mock_connection

        manager = NetworkManager()
        result = manager.execute_command(sample_switch, "show_version")

        assert result.success is True
        assert "Version: 1.0.0" in result.output
        assert result.command == "show version"

    @patch("app.network.ConnectHandler")
    def test_execute_command_auth_failure(
        self, mock_connect: MagicMock, sample_switch: Switch
    ):
        """Test authentication failure handling."""
        from netmiko.exceptions import AuthenticationException

        mock_connect.side_effect = AuthenticationException("Auth failed")

        manager = NetworkManager()
        result = manager.execute_command(sample_switch, "show_version")

        assert result.success is False
        assert "Authentication failed" in result.error

    @patch("app.network.ConnectHandler")
    def test_execute_command_timeout(
        self, mock_connect: MagicMock, sample_switch: Switch
    ):
        """Test connection timeout handling."""
        from netmiko.exceptions import NetmikoTimeoutException

        mock_connect.side_effect = NetmikoTimeoutException("Timeout")

        manager = NetworkManager()
        result = manager.execute_command(sample_switch, "show_version")

        assert result.success is False
        assert "timeout" in result.error.lower()

    @patch("app.network.ConnectHandler")
    def test_test_connection_success(
        self, mock_connect: MagicMock, sample_switch: Switch
    ):
        """Test connection test success."""
        mock_connection = MagicMock()
        mock_connection.find_prompt.return_value = "switch#"
        mock_connect.return_value.__enter__.return_value = mock_connection

        manager = NetworkManager()
        success, message = manager.test_connection(sample_switch)

        assert success is True
        assert "Connected successfully" in message

    @patch("app.network.ConnectHandler")
    def test_test_connection_failure(
        self, mock_connect: MagicMock, sample_switch: Switch
    ):
        """Test connection test failure."""
        from netmiko.exceptions import NetmikoTimeoutException

        mock_connect.side_effect = NetmikoTimeoutException("Timeout")

        manager = NetworkManager()
        success, message = manager.test_connection(sample_switch)

        assert success is False
        assert "timeout" in message.lower()


class TestVendorCommands:
    """Tests for vendor-specific command mapping."""

    def test_arista_commands(self, sample_switch: Switch):
        """Test Arista command mapping."""
        from app.config import VENDOR_COMMANDS

        arista_cmds = VENDOR_COMMANDS["arista_eos"]
        assert arista_cmds["show_bgp_summary"] == "show ip bgp summary"
        assert arista_cmds["show_route"] == "show ip route"
        assert arista_cmds["show_version"] == "show version"

    def test_dell_commands(self):
        """Test Dell OS10 command mapping."""
        from app.config import VENDOR_COMMANDS

        dell_cmds = VENDOR_COMMANDS["dell_os10"]
        assert dell_cmds["show_bgp_summary"] == "show ip bgp summary"
        assert dell_cmds["show_route"] == "show ip route"

    def test_juniper_commands(self):
        """Test Juniper command mapping."""
        from app.config import VENDOR_COMMANDS

        junos_cmds = VENDOR_COMMANDS["juniper_junos"]
        assert junos_cmds["show_bgp_summary"] == "show bgp summary"
        assert junos_cmds["show_route"] == "show route"
        assert junos_cmds["show_vlan"] == "show vlans"
