# Design Document: Quip Folder Mirror

## Overview

The Quip Folder Mirror is a command-line Python application that recursively traverses Quip folder structures and creates a mirrored local filesystem structure, converting each Quip document to Word format. The application uses the official `quipclient` package to access Quip's API directly for reliable folder traversal and document export.

## Architecture

The application follows a modular architecture with clear separation of concerns:

```
CLI Application
├── Command Line Parser
├── Quip Client (via quipclient API)
├── Folder Traverser
├── Document Converter (direct DOCX export)
├── File System Manager
└── Progress Reporter
```

### High-Level Flow

1. Parse command line arguments (Quip folder URL, target path)
2. Extract folder ID from Quip URL and validate
3. Authenticate with Quip API using access token
4. Discover folder structure recursively using API
5. Create local directory structure
6. Export documents directly to DOCX with progress reporting

## Components and Interfaces

### CLI Application (`QuipMirrorCLI`)

**Responsibilities:**
- Parse command line arguments including optional token
- Coordinate all components
- Handle authentication token discovery and validation
- Handle top-level error handling and reporting

**Interface:**
```python
class QuipMirrorCLI:
    def main(self, args: List[str]) -> int
    def parse_arguments(self, args: List[str]) -> MirrorConfig
    def get_access_token(self, config: MirrorConfig) -> str
    def validate_config(self, config: MirrorConfig) -> bool
    def execute_mirror(self, config: MirrorConfig) -> MirrorResult
```

**Token Discovery Priority:**
1. Command line `--token` argument
2. Environment variable `QUIP_ACCESS_TOKEN`
3. Configuration file `~/.quip_token`
4. Interactive prompt with hidden input

### Quip Client (`QuipAPIClient`)

**Responsibilities:**
- Interface with Quip API using `quipclient` package
- Handle Quip authentication via access token
- Retrieve folder contents and document data
- Export documents directly to DOCX format

**Interface:**
```python
class QuipAPIClient:
    def __init__(self, access_token: str):
        self.client = quipclient.QuipClient(access_token=access_token)
    
    def get_folder_contents(self, folder_id: str) -> FolderContents
    def get_document_metadata(self, thread_id: str) -> DocumentContent
    def export_document_to_docx(self, thread_id: str, file_path: str) -> bool
    def is_folder(self, item: Dict) -> bool
    def is_document(self, item: Dict) -> bool
```

### Folder Traverser (`FolderTraverser`)

**Responsibilities:**
- Recursively discover Quip folder structure using API
- Build complete hierarchy map
- Handle nested folder relationships

**Interface:**
```python
class FolderTraverser:
    def traverse(self, root_folder_id: str, client: QuipAPIClient) -> FolderHierarchy
    def build_hierarchy(self, folder_contents: FolderContents) -> FolderHierarchy
    def get_all_documents(self, hierarchy: FolderHierarchy) -> List[DocumentInfo]
```

### Document Converter (`DocumentConverter`)

**Responsibilities:**
- Export Quip documents directly to Word format using API
- Handle file naming and path management
- Manage existing files and conflicts

**Interface:**
```python
class DocumentConverter:
    def export_to_word(self, thread_id: str, output_path: str, client: QuipAPIClient) -> bool
    def sanitize_filename(self, title: str) -> str
    def handle_file_conflict(self, file_path: str, overwrite: bool) -> bool
```

### File System Manager (`FileSystemManager`)

**Responsibilities:**
- Create local directory structure
- Handle file operations and permissions
- Manage existing files and conflicts

**Interface:**
```python
class FileSystemManager:
    def create_directory_structure(self, hierarchy: FolderHierarchy, base_path: str) -> bool
    def ensure_directory_exists(self, path: str) -> bool
    def get_document_path(self, doc_info: DocumentInfo, base_path: str) -> str
    def file_exists(self, path: str) -> bool
```

### Progress Reporter (`ProgressReporter`)

**Responsibilities:**
- Track and display progress information
- Provide user feedback during long operations
- Generate completion summaries

**Interface:**
```python
class ProgressReporter:
    def start_progress(self, total_items: int) -> None
    def update_progress(self, current_item: str, completed: int) -> None
    def report_error(self, item: str, error: str) -> None
    def finish_progress(self, summary: ProcessingSummary) -> None
```

## Data Models

### Core Data Structures

```python
@dataclass
class MirrorConfig:
    quip_folder_url: str
    target_path: str
    access_token: Optional[str] = None  # Will be resolved during execution
    overwrite_existing: bool = True

@dataclass
class QuipItem:
    id: str
    name: str
    type: str  # 'folder' or 'document'
    url: str

@dataclass
class FolderContents:
    folders: List[QuipItem]
    documents: List[QuipItem]

@dataclass
class FolderHierarchy:
    root_folder: QuipItem
    subfolders: Dict[str, 'FolderHierarchy']
    documents: List[QuipItem]

@dataclass
class DocumentInfo:
    item: QuipItem
    relative_path: str
    local_file_path: str

@dataclass
class DocumentContent:
    title: str
    content: str
    format: str  # 'html', 'markdown', etc.

@dataclass
class ProcessingSummary:
    total_folders: int
    total_documents: int
    successful_conversions: int
    failed_conversions: int
    errors: List[str]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*
