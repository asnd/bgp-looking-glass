"""FastAPI application for BGP Looking Glass."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.config import get_available_commands, settings
from app.inventory import get_inventory, reload_inventory
from app.network import get_network_manager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler."""
    # Startup
    logger.info("Starting BGP Looking Glass application")
    try:
        inventory = get_inventory()
        inventory.load()
        logger.info(f"Loaded {len(inventory.get_sites())} sites from inventory")
    except FileNotFoundError:
        logger.warning("Inventory file not found. Create inventory/hosts.yml")
    except Exception as e:
        logger.error(f"Error loading inventory: {e}")

    yield

    # Shutdown
    logger.info("Shutting down BGP Looking Glass application")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Network BGP Looking Glass for multi-vendor switches",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Setup templates
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_path)


# Pydantic models for API
class ExecuteCommandRequest(BaseModel):
    """Request model for command execution."""

    site_id: str
    switch_role: str  # LR1 or LR2
    command_id: str


class SiteResponse(BaseModel):
    """Site information for API response."""

    site_id: str
    name: str
    display_name: str
    switches: list[str]


class CommandResponse(BaseModel):
    """Command execution response."""

    success: bool
    output: str
    command: str
    switch_name: str
    switch_host: str
    error: str = ""


# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main looking glass page."""
    inventory = get_inventory()
    sites = inventory.get_sites()
    commands = get_available_commands()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "sites": sites,
            "commands": commands,
        },
    )


@app.get("/api/sites")
async def get_sites() -> list[SiteResponse]:
    """Get list of all sites."""
    inventory = get_inventory()
    sites = inventory.get_sites()

    return [
        SiteResponse(
            site_id=site.site_id,
            name=site.name,
            display_name=site.display_name,
            switches=list(site.switches.keys()),
        )
        for site in sites
    ]


@app.get("/api/sites/{site_id}")
async def get_site(site_id: str) -> SiteResponse:
    """Get site details by ID."""
    inventory = get_inventory()
    site = inventory.get_site(site_id)

    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found")

    return SiteResponse(
        site_id=site.site_id,
        name=site.name,
        display_name=site.display_name,
        switches=list(site.switches.keys()),
    )


@app.get("/api/sites/{site_id}/switches/{role}")
async def get_switch_info(site_id: str, role: str) -> dict[str, Any]:
    """Get switch information by site and role."""
    inventory = get_inventory()
    switch = inventory.get_switch(site_id, role.upper())

    if not switch:
        raise HTTPException(
            status_code=404,
            detail=f"Switch '{role}' not found in site '{site_id}'",
        )

    return {
        "name": switch.name,
        "host": switch.host,
        "vendor": switch.vendor,
        "device_type": switch.device_type,
        "role": switch.role,
        "display_name": switch.display_name,
    }


@app.get("/api/commands")
async def get_commands() -> list[dict[str, str]]:
    """Get list of available commands."""
    return get_available_commands()


@app.post("/api/execute")
async def execute_command(request: ExecuteCommandRequest) -> CommandResponse:
    """Execute a command on a switch."""
    inventory = get_inventory()
    network = get_network_manager()

    # Get the switch
    switch = inventory.get_switch(request.site_id, request.switch_role.upper())
    if not switch:
        raise HTTPException(
            status_code=404,
            detail=f"Switch '{request.switch_role}' not found in site '{request.site_id}'",
        )

    # Execute the command
    logger.info(f"Executing '{request.command_id}' on {switch.name} ({switch.host})")
    result = network.execute_command(switch, request.command_id)

    return CommandResponse(
        success=result.success,
        output=result.output,
        command=result.command,
        switch_name=result.switch_name,
        switch_host=result.switch_host,
        error=result.error,
    )


@app.post("/api/inventory/reload")
async def api_reload_inventory() -> dict[str, Any]:
    """Reload the inventory from file."""
    try:
        inventory = reload_inventory()
        sites = inventory.get_sites()
        return {
            "success": True,
            "message": f"Reloaded {len(sites)} sites",
            "site_count": len(sites),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# HTMX partial endpoints
@app.get("/partials/switches/{site_id}", response_class=HTMLResponse)
async def get_switches_partial(request: Request, site_id: str) -> HTMLResponse:
    """Get switches dropdown options for a site (HTMX partial)."""
    inventory = get_inventory()
    site = inventory.get_site(site_id)

    if not site:
        return HTMLResponse("")

    switches_html = ""
    for role in ["LR1", "LR2"]:
        switch = site.switches.get(role)
        if switch:
            switches_html += f'<option value="{role}">{role} - {switch.host}</option>'

    return HTMLResponse(switches_html)


@app.post("/partials/execute", response_class=HTMLResponse)
async def execute_partial(request: Request) -> HTMLResponse:
    """Execute command and return HTML result (HTMX partial)."""
    form_data = await request.form()
    site_id = form_data.get("site_id", "")
    switch_role = form_data.get("switch_role", "")
    command_id = form_data.get("command_id", "")

    if not all([site_id, switch_role, command_id]):
        return HTMLResponse(
            '<div class="alert alert-warning">Please select site, switch, and command</div>'
        )

    inventory = get_inventory()
    network = get_network_manager()

    switch = inventory.get_switch(str(site_id), str(switch_role).upper())
    if not switch:
        return HTMLResponse(
            f'<div class="alert alert-danger">Switch not found: {switch_role} in site {site_id}</div>'
        )

    result = network.execute_command(switch, str(command_id))

    if result.success:
        return HTMLResponse(f"""
            <div class="card">
                <div class="card-header bg-success text-white">
                    <strong>{result.switch_name}</strong> ({result.switch_host}) - {result.command}
                </div>
                <div class="card-body">
                    <pre class="bg-dark text-light p-3 rounded" style="max-height: 600px; overflow-y: auto;">{result.output}</pre>
                </div>
            </div>
        """)
    else:
        return HTMLResponse(f"""
            <div class="card">
                <div class="card-header bg-danger text-white">
                    <strong>Error:</strong> {result.switch_name} ({result.switch_host})
                </div>
                <div class="card-body">
                    <div class="alert alert-danger">{result.error}</div>
                </div>
            </div>
        """)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
