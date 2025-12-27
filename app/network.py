"""Network device communication using Netmiko."""

import logging
from dataclasses import dataclass
from typing import Any

from netmiko import ConnectHandler
from netmiko.exceptions import (
    AuthenticationException,
    NetmikoTimeoutException,
)

from app.config import VENDOR_COMMANDS, settings
from app.inventory import Switch

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of executing a command on a switch."""

    success: bool
    output: str
    command: str
    switch_name: str
    switch_host: str
    error: str = ""


class NetworkManager:
    """Manage network device connections and command execution."""

    def __init__(self):
        self.connection_timeout = settings.connection_timeout
        self.command_timeout = settings.command_timeout

    def execute_command(
        self,
        switch: Switch,
        command_id: str,
    ) -> CommandResult:
        """Execute a command on a switch.

        Args:
            switch: Switch object with connection details
            command_id: Command identifier (e.g., 'show_bgp_summary')

        Returns:
            CommandResult with output or error
        """
        # Get vendor-specific command
        vendor_commands = VENDOR_COMMANDS.get(switch.device_type, {})
        command = vendor_commands.get(command_id)

        if not command:
            return CommandResult(
                success=False,
                output="",
                command=command_id,
                switch_name=switch.name,
                switch_host=switch.host,
                error=f"Command '{command_id}' not supported for device type '{switch.device_type}'",
            )

        # Build Netmiko connection parameters
        device_params: dict[str, Any] = {
            "device_type": switch.device_type,
            "host": switch.host,
            "username": switch.username,
            "password": switch.password,
            "port": switch.port,
            "timeout": self.connection_timeout,
            "conn_timeout": self.connection_timeout,
            "auth_timeout": self.connection_timeout,
            "banner_timeout": self.connection_timeout,
        }

        try:
            logger.info(f"Connecting to {switch.name} ({switch.host})")

            with ConnectHandler(**device_params) as conn:
                logger.info(f"Executing command: {command}")
                output = conn.send_command(
                    command,
                    read_timeout=self.command_timeout,
                )

            return CommandResult(
                success=True,
                output=output,
                command=command,
                switch_name=switch.name,
                switch_host=switch.host,
            )

        except AuthenticationException as e:
            logger.error(f"Authentication failed for {switch.host}: {e}")
            return CommandResult(
                success=False,
                output="",
                command=command,
                switch_name=switch.name,
                switch_host=switch.host,
                error=f"Authentication failed: {e}",
            )

        except NetmikoTimeoutException as e:
            logger.error(f"Connection timeout for {switch.host}: {e}")
            return CommandResult(
                success=False,
                output="",
                command=command,
                switch_name=switch.name,
                switch_host=switch.host,
                error=f"Connection timeout: {e}",
            )

        except Exception as e:
            logger.error(f"Error executing command on {switch.host}: {e}")
            return CommandResult(
                success=False,
                output="",
                command=command,
                switch_name=switch.name,
                switch_host=switch.host,
                error=str(e),
            )

    def test_connection(self, switch: Switch) -> tuple[bool, str]:
        """Test connectivity to a switch.

        Returns:
            Tuple of (success, message)
        """
        device_params: dict[str, Any] = {
            "device_type": switch.device_type,
            "host": switch.host,
            "username": switch.username,
            "password": switch.password,
            "port": switch.port,
            "timeout": self.connection_timeout,
            "conn_timeout": self.connection_timeout,
        }

        try:
            with ConnectHandler(**device_params) as conn:
                prompt = conn.find_prompt()
                return True, f"Connected successfully. Prompt: {prompt}"

        except AuthenticationException:
            return False, "Authentication failed"
        except NetmikoTimeoutException:
            return False, "Connection timeout"
        except Exception as e:
            return False, str(e)


# Global network manager instance
_network_manager: NetworkManager | None = None


def get_network_manager() -> NetworkManager:
    """Get the global network manager instance."""
    global _network_manager
    if _network_manager is None:
        _network_manager = NetworkManager()
    return _network_manager
