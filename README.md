# Quip Folder Mirror

A command-line Python application that recursively traverses Quip folder structures and creates a mirrored local filesystem structure, converting each Quip document to Word format.

## Features

- **Recursive folder traversal**: Mirrors complete Quip folder hierarchies
- **Direct Word export**: Converts Quip documents to .docx format using Quip's native export API
- **Authentication support**: Multiple token configuration methods
- **Error resilience**: Continues processing even if individual documents fail
- **Progress reporting**: Real-time feedback during mirroring operations
- **Cross-platform**: Works on Windows, macOS, and Linux

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd quip-folder-mirror

# Install in development mode
pip install -e .

# Or install with CLI enhancements
pip install -e ".[cli]"
```

### Requirements

- Python 3.7 or higher
- Access to Amazon's internal Quip instance (quip-amazon.com)
- Valid Quip personal access token

## Authentication Setup

### Obtaining a Quip Access Token

1. Visit [https://quip-amazon.com/dev/token](https://quip-amazon.com/dev/token)
2. Click "Generate" to create a new personal access token
3. Copy the generated token for configuration

### Token Configuration

The application checks for your access token in the following order:

1. **Command line argument** (highest priority):
   ```bash
   quip-mirror --token YOUR_TOKEN <folder_url> <target_path>
   ```

2. **Environment variable**:
   ```bash
   export QUIP_ACCESS_TOKEN=YOUR_TOKEN
   quip-mirror <folder_url> <target_path>
   ```

3. **Configuration file**:
   ```bash
   echo "YOUR_TOKEN" > ~/.quip_token
   quip-mirror <folder_url> <target_path>
   ```

4. **Interactive prompt** (lowest priority):
   The application will prompt you to enter the token if none is found.

## Usage

### Basic Usage

```bash
# Mirror a Quip folder to local directory
quip-mirror https://quip-amazon.com/folder/ABC123 ./local-mirror

# With explicit token
quip-mirror --token YOUR_TOKEN https://quip-amazon.com/folder/ABC123 ./local-mirror
```

### Command Line Options

```bash
quip-mirror [OPTIONS] QUIP_FOLDER_URL TARGET_PATH

Arguments:
  QUIP_FOLDER_URL  URL of the Quip folder to mirror (must start with https://quip-amazon.com/)
  TARGET_PATH      Local directory where the mirrored structure will be created

Options:
  --token TEXT     Quip personal access token
  --overwrite      Overwrite existing files (default: True)
  --help           Show this message and exit
```

### Examples

```bash
# Mirror a project folder
quip-mirror https://quip-amazon.com/folder/PROJECT123 ./project-docs

# Mirror with environment variable authentication
export QUIP_ACCESS_TOKEN=your_token_here
quip-mirror https://quip-amazon.com/folder/TEAM456 ./team-docs

# Mirror with explicit token
quip-mirror --token ABC123... https://quip-amazon.com/folder/DOCS789 ./documentation
```

## How It Works

1. **URL Parsing**: Extracts the folder ID from the Quip URL
2. **Authentication**: Discovers and validates your access token
3. **Folder Discovery**: Recursively traverses the folder structure using Quip's API
4. **Directory Creation**: Creates matching local directory structure
5. **Document Export**: Downloads each document as a .docx file using Quip's export API
6. **Progress Reporting**: Shows real-time progress and completion summary

## Output Structure

The application creates a local directory structure that mirrors your Quip folder:

```
target-directory/
├── Root Folder Name/
│   ├── Document 1.docx
│   ├── Document 2.docx
│   ├── Subfolder A/
│   │   ├── Document 3.docx
│   │   └── Document 4.docx
│   └── Subfolder B/
│       └── Document 5.docx
```

## Error Handling

- **Individual failures**: If a single document fails to export, the process continues with other documents
- **Network issues**: Automatic retry logic for temporary network problems
- **Permission errors**: Clear error messages for access-related issues
- **Invalid URLs**: Validation and helpful error messages for malformed URLs

## Development

### Setting Up Development Environment

```bash
# Clone and install in development mode
git clone <repository-url>
cd quip-folder-mirror
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=quip_mirror

# Format code
black src/ tests/

# Type checking
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run functional tests only
pytest tests/functional/

# Run with coverage report
pytest --cov=quip_mirror --cov-report=html
```

## Troubleshooting

### Common Issues

1. **"Invalid Quip URL"**: Ensure the URL starts with `https://quip-amazon.com/`
2. **"Authentication failed"**: Verify your access token is valid and not expired
3. **"Permission denied"**: Check that you have access to the Quip folder
4. **"Network timeout"**: Try again later or check your network connection

### Getting Help

1. Check the error message for specific guidance
2. Verify your access token at [https://quip-amazon.com/dev/token](https://quip-amazon.com/dev/token)
3. Ensure you have read access to the Quip folder you're trying to mirror

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Limitations

- Only works with Amazon's internal Quip instance (quip-amazon.com)
- Requires valid Quip personal access token
- Documents are exported as .docx files (original formatting may vary)
- Large folders may take significant time to process