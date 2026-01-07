# Technology Stack

## Language & Runtime
- **Python** (planned implementation language)
- Command-line interface application

## Key Dependencies (Updated)
- `requests` - HTTP client for direct Quip API calls
- **No longer needed**: `python-docx` (direct DOCX export available via API)
- **No longer needed**: `quip-api` package (using direct HTTP requests)
- **No longer needed**: `ent-support-genai-mcp` server integration

## Architecture Components
- **QuipMirrorCLI** - Main CLI application coordinator
- **QuipAPIClient** - Interface with Quip API using quipclient package
- **FolderTraverser** - Recursive folder discovery
- **DocumentConverter** - Direct DOCX export via API
- **FileSystemManager** - Local directory/file operations
- **ProgressReporter** - User feedback and progress tracking

## Build System
**Not yet implemented** - Standard Python packaging expected:
- `requirements.txt` or `pyproject.toml` for dependencies
- `setup.py` or `pyproject.toml` for package configuration

## Testing Framework
- **pytest** - Primary testing framework
- **pytest-mock** - Mocking and patching for unit tests
- **pytest-cov** - Code coverage reporting
- **pytest-asyncio** - If async operations are needed
- **responses** - HTTP request mocking for MCP client testing

## Common Commands (Future)
```bash
# Installation (when implemented)
pip install requests  # Only dependency needed!
pip install -e .

# Usage (planned)
python -m quip_mirror <quip_folder_url> <target_path>

# With explicit token
python -m quip_mirror --token YOUR_TOKEN <quip_folder_url> <target_path>

# With environment variable
export QUIP_ACCESS_TOKEN=YOUR_TOKEN
python -m quip_mirror <quip_folder_url> <target_path>

# With config file
echo "YOUR_TOKEN" > ~/.quip_token
python -m quip_mirror <quip_folder_url> <target_path>

# Testing
pytest tests/                           # Run all tests
pytest tests/unit/                      # Run unit tests only
pytest tests/functional/                # Run functional tests only
pytest --cov=quip_mirror tests/         # Run with coverage
pytest -v --tb=short                    # Verbose output with short traceback
pytest -k "test_api"                    # Run API-related tests
pytest --maxfail=1                      # Stop on first failure

# Test Quality
pytest --cov=quip_mirror --cov-report=html tests/  # HTML coverage report
pytest --cov=quip_mirror --cov-fail-under=90 tests/ # Enforce 90% coverage

# Build/Package (to be defined)
python setup.py sdist bdist_wheel
```

## Development Notes
- Uses Model Context Protocol (MCP) for Quip integration
- Targets Amazon's internal Quip instance only
- Designed for resilient processing with error handling