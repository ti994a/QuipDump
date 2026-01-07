# Project Structure

## Current Organization
```
QuipDump/
└── .kiro/
    ├── specs/
    │   └── quip-folder-mirror/
    │       ├── design.md
    │       └── requirements.md
    └── steering/
        ├── product.md
        ├── tech.md
        └── structure.md
```

## Specification Framework
- **`.kiro/specs/`** - Contains formal specification documents
- **`.kiro/steering/`** - AI assistant guidance documents
- Uses formal requirements specification with "WHEN...SHALL" structure
- Separates requirements from design documentation

## Planned Implementation Structure
When code is implemented, follow this organization:

```
QuipDump/
├── src/
│   └── quip_mirror/
│       ├── __init__.py
│       ├── cli.py              # QuipMirrorCLI
│       ├── quip_client.py      # QuipAPIClient
│       ├── traverser.py        # FolderTraverser
│       ├── converter.py        # DocumentConverter
│       ├── filesystem.py       # FileSystemManager
│       ├── progress.py         # ProgressReporter
│       └── models.py           # Data classes
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Shared fixtures and test configuration
│   ├── unit/                   # Unit tests (isolated component testing)
│   │   ├── __init__.py
│   │   ├── test_cli.py
│   │   ├── test_quip_client.py
│   │   ├── test_traverser.py
│   │   ├── test_converter.py
│   │   ├── test_filesystem.py
│   │   ├── test_progress.py
│   │   └── test_models.py
│   ├── functional/             # End-to-end integration tests
│   │   ├── __init__.py
│   │   ├── test_full_mirror.py
│   │   ├── test_error_scenarios.py
│   │   └── test_cli_integration.py
│   └── fixtures/               # Test data and mock responses
│       ├── sample_quip_responses.json
│       ├── mock_documents/
│       └── expected_outputs/
├── requirements.txt
├── requirements-dev.txt        # Development dependencies
├── setup.py or pyproject.toml
└── README.md
```

## Data Models (Planned)
- `MirrorConfig` - Configuration settings
- `QuipItem` - Generic Quip resource (folder or document)
- `FolderContents` - Folder contents representation
- `FolderHierarchy` - Recursive hierarchy structure
- `DocumentInfo` - Document with path information
- `DocumentContent` - Document content with metadata
- `ProcessingSummary` - Operation results and statistics

## Design Patterns
- **Modular Architecture** - Single responsibility components
- **Dependency Injection** - Components receive dependencies
- **Data Classes** - Heavy use of `@dataclass` for modeling
- **Error Resilience** - Continue processing on individual failures

## File Naming Conventions
- Use snake_case for Python modules and functions
- Use PascalCase for class names
- Use descriptive names that match component responsibilities

## Testing Strategy

### Unit Testing Requirements
Each component must have comprehensive unit tests covering:

**QuipAPIClient (`test_quip_client.py`)**
- Quip API authentication and connection
- Folder listing via `get_folder()` method
- Document metadata retrieval via `get_thread()`
- Direct DOCX export via `get_docx()`
- Error handling for API failures and invalid responses
- Rate limiting and retry logic

**FolderTraverser (`test_traverser.py`)**
- Recursive folder discovery algorithms
- Handling of nested folder structures
- Circular reference detection
- Empty folder handling
- Progress tracking during traversal

**DocumentConverter (`test_converter.py`)**
- Direct DOCX export functionality
- File naming and sanitization
- Metadata preservation during export
- Error handling for export failures
- File overwrite behavior and conflict resolution

**FileSystemManager (`test_filesystem.py`)**
- Directory creation and path validation
- File overwrite behavior
- Permission handling
- Disk space validation
- Path sanitization for cross-platform compatibility

**CLI (`test_cli.py`)**
- Argument parsing and validation
- URL validation for Quip endpoints
- Configuration loading and validation
- Error message formatting
- Exit code handling

### Functional Testing Requirements

**End-to-End Integration (`test_full_mirror.py`)**
- Complete folder mirroring workflow
- Multi-level folder hierarchies
- Mixed content types (documents and subfolders)
- Large folder structures (performance testing)
- Resume functionality after interruption

**Error Scenario Testing (`test_error_scenarios.py`)**
- Network connectivity issues
- Invalid Quip URLs
- Permission denied scenarios
- Disk space exhaustion
- Corrupted document content
- MCP server unavailability

**CLI Integration (`test_cli_integration.py`)**
- Command-line argument combinations
- Configuration file loading
- Progress reporting accuracy
- Logging output validation
- Signal handling (Ctrl+C interruption)

### Test Data Management
- **Mock Responses**: JSON fixtures for Quip API responses
- **Sample Documents**: Representative Quip content for conversion testing
- **Expected Outputs**: Reference Word documents for comparison
- **Test Isolation**: Each test should be independent and repeatable

### Coverage Requirements
- **Minimum 90% code coverage** across all modules
- **100% coverage** for critical paths (data conversion, file operations)
- **Branch coverage** for all conditional logic
- **Exception path coverage** for error handling

### Test Execution Standards
- All tests must pass before code merge
- Tests should run in under 30 seconds for unit tests
- Functional tests should complete within 2 minutes
- No external dependencies (use mocks for MCP server)
- Deterministic results (no flaky tests)