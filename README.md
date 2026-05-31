# BGP Looking Glass

A web-based network looking glass application for multi-vendor switches in a leaf-spine topology. Execute show commands on Arista EOS, Dell OS10, Juniper Junos, and SONiC devices through a simple web interface.

## Features

- **Multi-vendor support**: Arista EOS, Dell OS10, Juniper Junos, SONiC
- **Ansible inventory integration**: Uses YAML inventory files for device management
- **Leaf-spine topology**: Supports LR1/LR2 switch pairs per site
- **Web UI**: Bootstrap-based responsive interface with HTMX for dynamic updates
- **REST API**: Full API for programmatic access
- **Docker ready**: Containerized deployment
- **Per-device throttling**: Limits concurrent commands per switch

## Quick Start

### Local Development

```bash
# Clone the repository
git clone https://gitlab.com/your-org/bgp-looking-glass.git
cd bgp-looking-glass

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure inventory
cp inventory/hosts.yml inventory/hosts.local.yml
# Edit inventory/hosts.local.yml with your devices

# Create .env file
cp .env.example .env
# Edit .env with your settings

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

### Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f looking-glass
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LG_APP_NAME` | BGP Looking Glass | Application title |
| `LG_DEBUG` | false | Enable debug mode |
| `LG_INVENTORY_PATH` | inventory/hosts.yml | Path to Ansible inventory |
| `LG_CONNECTION_TIMEOUT` | 30 | SSH connection timeout (seconds) |
| `LG_COMMAND_TIMEOUT` | 60 | Command execution timeout (seconds) |
| `LG_MAX_CONCURRENT_COMMANDS_PER_SWITCH` | 2 | Maximum concurrent commands per switch |
| `LG_DEFAULT_USERNAME` | admin | Default SSH username |
| `LG_DEFAULT_PASSWORD` | | Default SSH password |

### Ansible Inventory Format

```yaml
all:
  children:
    sites:
      children:
        site_001:
          vars:
            site_id: "001"
            vendor: arista
            ansible_user: admin
            ansible_password: secret
          hosts:
            dc1-leaf-lr1:
              ansible_host: 10.74.1.245
              role: LR1
            dc1-leaf-lr2:
              ansible_host: 10.74.1.246
              role: LR2
```

### Supported Vendors

| Vendor | Device Type | Notes |
|--------|-------------|-------|
| Arista | arista_eos | EOS switches |
| Dell | dell_os10 | OS10 switches |
| Juniper | juniper_junos | Junos devices |
| SONiC | sonic_os | SONiC switches |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/sites` | List all sites |
| GET | `/api/sites/{id}` | Get site details |
| GET | `/api/sites/{id}/switches/{role}` | Get switch info |
| GET | `/api/commands` | List available commands |
| POST | `/api/execute` | Execute command |
| POST | `/api/inventory/reload` | Reload inventory |

### Execute Command Example

```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "001",
    "switch_role": "LR1",
    "command_id": "show_bgp_summary"
  }'
```

## Available Commands

- Show Version
- Show VLAN
- Show IP Route
- Show BGP Summary
- Show BGP Neighbors
- Show Interfaces
- Show IP Interface Brief
- Show LLDP Neighbors
- Show MAC Address Table
- Show ARP Table

## Production-readiness Notes

- Blocking inventory parsing and SSH command execution are offloaded from the async request loop.
- Inventory reloads replace the parsed site map atomically, avoiding partially cleared reads.
- HTMX command responses escape device output before rendering it into HTML.

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html
```

### Code Quality

```bash
# Lint code
ruff check app/ tests/

# Format code
ruff format app/ tests/

# Type checking
mypy app/
```

## CI/CD

The project includes a GitLab CI/CD pipeline (`.gitlab-ci.yml`) with:

- **Lint stage**: Ruff linting and formatting checks, mypy type checking
- **Test stage**: Unit and integration tests with coverage
- **Security stage**: Bandit security scan, Safety dependency check, Trivy vulnerability scan
- **Build stage**: Docker image build and push to registry
- **Deploy stage**: Staging and production deployment (manual approval for production)

## Project Structure

```
bgp-looking-glass/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration and constants
│   ├── inventory.py     # Ansible inventory parser
│   ├── network.py       # Netmiko network operations
│   ├── templates/
│   │   └── index.html   # Web UI template
│   └── static/
│       └── style.css    # Custom styles
├── inventory/
│   └── hosts.yml        # Sample Ansible inventory
├── tests/
│   ├── conftest.py      # Pytest fixtures
│   ├── test_api.py      # API endpoint tests
│   ├── test_inventory.py # Inventory parser tests
│   └── test_network.py  # Network module tests
├── .gitlab-ci.yml       # GitLab CI/CD pipeline
├── Dockerfile           # Container build
├── docker-compose.yml   # Container orchestration
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Project configuration
└── README.md
```

## Security Considerations

- Store credentials securely (use Ansible Vault, environment variables, or secrets management)
- Run the container as non-root user
- Use HTTPS in production (configure nginx reverse proxy)
- Restrict network access to the looking glass service
- Audit command execution logs

## License

MIT License
