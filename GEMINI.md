# GEMINI Project Profile: BGP Looking Glass

## Project Overview
- **Name**: BGP Looking Glass
- **Primary Language**: Python (FastAPI)
- **Purpose**: Web-based network looking glass for multi-vendor switches (Arista, Dell, Juniper) in a leaf-spine topology.
- **Key Features**: Multi-vendor support, Ansible inventory integration, Web UI (Bootstrap/HTMX), and REST API.

## Project Structure
```
bgp-looking-glass/
├── app/                     # Application source
│   ├── main.py              # FastAPI application
│   ├── inventory.py         # Ansible inventory parser
│   ├── network.py           # Netmiko network operations
│   ├── templates/           # HTML templates
│   └── static/              # Static assets
├── inventory/               # Ansible inventory
├── tests/                   # Tests
├── .gitlab-ci.yml           # CI/CD pipeline
├── docker-compose.yml       # Docker orchestration
└── pyproject.toml           # Project config
```

## Build & Deployment
- **Build System**: `pyproject.toml`.
- **Containerization**: Docker & Docker Compose.
- **CI/CD**: GitLab CI (Lint, Test, Security, Build, Deploy).

## Suggested Development Tools
- **VSCode Extensions**:
  - `ms-python.python`: Python language support.
  - `charliermarsh.ruff`: Fast Python linter.
  - `tamasfe.even-better-toml`: TOML support.
- **CLI Tools**:
  - `ruff`: Linting.
  - `mypy`: Type checking.
  - `pytest`: Testing.
- **MCP Servers**:
  - `filesystem`: For file access.
