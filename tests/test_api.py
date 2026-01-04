"""Tests for FastAPI endpoints."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, test_client: TestClient) -> None:
        """Test health endpoint returns healthy status."""
        response = test_client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestSitesEndpoints:
    """Tests for sites API endpoints."""

    def test_get_sites(self, test_client: TestClient) -> None:
        """Test getting list of sites."""
        response = test_client.get("/api/sites")
        assert response.status_code == 200

        sites = response.json()
        assert len(sites) == 2
        assert any(s["site_id"] == "001" for s in sites)
        assert any(s["site_id"] == "002" for s in sites)

    def test_get_site_by_id(self, test_client: TestClient) -> None:
        """Test getting specific site."""
        response = test_client.get("/api/sites/001")
        assert response.status_code == 200

        site = response.json()
        assert site["site_id"] == "001"
        assert site["name"] == "site_001"
        assert "LR1" in site["switches"]
        assert "LR2" in site["switches"]

    def test_get_nonexistent_site(self, test_client: TestClient) -> None:
        """Test getting non-existent site returns 404."""
        response = test_client.get("/api/sites/999")
        assert response.status_code == 404


class TestSwitchEndpoints:
    """Tests for switch API endpoints."""

    def test_get_switch_info(self, test_client: TestClient) -> None:
        """Test getting switch information."""
        response = test_client.get("/api/sites/001/switches/LR1")
        assert response.status_code == 200

        switch = response.json()
        assert switch["role"] == "LR1"
        assert switch["host"] == "10.74.1.245"
        assert switch["vendor"] == "arista"

    def test_get_switch_case_insensitive(self, test_client: TestClient) -> None:
        """Test switch role is case insensitive."""
        response = test_client.get("/api/sites/001/switches/lr1")
        assert response.status_code == 200
        assert response.json()["role"] == "LR1"

    def test_get_nonexistent_switch(self, test_client: TestClient) -> None:
        """Test getting non-existent switch returns 404."""
        response = test_client.get("/api/sites/001/switches/LR3")
        assert response.status_code == 404


class TestCommandsEndpoint:
    """Tests for commands API endpoint."""

    def test_get_commands(self, test_client: TestClient) -> None:
        """Test getting list of available commands."""
        response = test_client.get("/api/commands")
        assert response.status_code == 200

        commands = response.json()
        assert len(commands) > 0

        # Check for expected commands
        command_ids = [c["id"] for c in commands]
        assert "show_version" in command_ids
        assert "show_bgp_summary" in command_ids
        assert "show_route" in command_ids


class TestExecuteEndpoint:
    """Tests for command execution endpoint."""

    @patch("app.main.get_network_manager")
    def test_execute_command_success(
        self, mock_get_manager: MagicMock, test_client: TestClient
    ) -> None:
        """Test successful command execution."""
        from app.network import CommandResult

        mock_manager = MagicMock()
        mock_manager.execute_command.return_value = CommandResult(
            success=True,
            output="System version 1.0.0",
            command="show version",
            switch_name="dc1-lr1",
            switch_host="10.74.1.245",
        )
        mock_get_manager.return_value = mock_manager

        response = test_client.post(
            "/api/execute",
            json={
                "site_id": "001",
                "switch_role": "LR1",
                "command_id": "show_version",
            },
        )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "version" in result["output"].lower()

    @patch("app.main.get_network_manager")
    def test_execute_command_failure(
        self, mock_get_manager: MagicMock, test_client: TestClient
    ) -> None:
        """Test failed command execution."""
        from app.network import CommandResult

        mock_manager = MagicMock()
        mock_manager.execute_command.return_value = CommandResult(
            success=False,
            output="",
            command="show version",
            switch_name="dc1-lr1",
            switch_host="10.74.1.245",
            error="Connection timeout",
        )
        mock_get_manager.return_value = mock_manager

        response = test_client.post(
            "/api/execute",
            json={
                "site_id": "001",
                "switch_role": "LR1",
                "command_id": "show_version",
            },
        )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
        assert "timeout" in result["error"].lower()

    def test_execute_nonexistent_site(self, test_client: TestClient) -> None:
        """Test executing on non-existent site returns 404."""
        response = test_client.post(
            "/api/execute",
            json={
                "site_id": "999",
                "switch_role": "LR1",
                "command_id": "show_version",
            },
        )
        assert response.status_code == 404


class TestIndexPage:
    """Tests for main index page."""

    def test_index_page_loads(self, test_client: TestClient) -> None:
        """Test index page loads successfully."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_index_contains_sites(self, test_client: TestClient) -> None:
        """Test index page contains site dropdown options."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "site_001" in response.text or "Site 001" in response.text

    def test_index_contains_commands(self, test_client: TestClient) -> None:
        """Test index page contains command options."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "Show Version" in response.text
        assert "Show BGP Summary" in response.text


class TestInventoryReload:
    """Tests for inventory reload endpoint."""

    def test_reload_inventory(self, test_client: TestClient) -> None:
        """Test inventory reload endpoint."""
        response = test_client.post("/api/inventory/reload")
        assert response.status_code == 200

        result = response.json()
        assert result["success"] is True
        assert result["site_count"] == 2
