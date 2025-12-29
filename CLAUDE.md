# BGP Looking Glass

Network BGP Looking Glass API for multi-vendor switches using FastAPI.

## Tech Stack
- **Language**: Python 3.10+
- **Framework**: FastAPI with Uvicorn
- **Network**: Netmiko, Paramiko for device communication
- **Validation**: Pydantic v2
- **CI/CD**: GitLab CI

## Development Commands

```bash
# Setup virtual environment
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest

# Code quality
ruff check .
ruff format .
mypy app/

# Docker
docker-compose up -d
```

## Project Structure
- `app/` - FastAPI application code
- `tests/` - Test suite
- `inventory/` - Network device inventory

## Suggested Claude Code Plugins

### MCP Servers
- **filesystem** - For editing configuration files
- **docker** - Container management during development

### Skills
- **nsx-avi-reference** - For VMware networking context
- **python-to-golang** - If migrating to Go

### Recommended Workflow
1. Use `ruff check` before committing
2. Run `pytest` to validate changes
3. Use `mypy` for type checking
