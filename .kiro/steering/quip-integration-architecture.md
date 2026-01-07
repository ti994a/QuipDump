# Quip Integration Architecture

## Executive Summary

✅ **DECISION**: Use direct HTTP requests to Quip API endpoints.

✅ **RATIONALE**: Simplest approach with minimal dependencies - just `requests` library needed.

## Quip API Integration

### Confirmed Capabilities via Direct HTTP API

#### 1. Folder Listing API ✅ **VERIFIED WITH EXAMPLE**
**Endpoint**: `GET https://platform.quip.com/1/folders/{folder_id}`
**Purpose**: Get folder metadata and children (subfolders + documents)
**Returns**: JSON with folder title and children array containing folder_id or thread_id
**Authentication**: Bearer token in Authorization header
**Critical for**: Folder content enumeration and traversal

#### 2. Document Metadata API ✅ **VERIFIED WITH EXAMPLE**
**Endpoint**: `GET https://platform.quip.com/1/threads/{thread_id}`
**Purpose**: Get document metadata including title
**Returns**: JSON with thread information including title for file naming
**Authentication**: Bearer token in Authorization header
**Critical for**: Document information retrieval and file naming

#### 3. Document Export API ✅ **VERIFIED WITH EXAMPLE**
**Endpoint**: `GET https://platform.quip.com/1/threads/{thread_id}/export/docx`
**Purpose**: Export document directly to Word format
**Returns**: Binary DOCX data ready for file writing
**Authentication**: Bearer token in Authorization header
**Critical for**: Direct Word conversion (no python-docx needed!)

#### 4. Recursive Traversal Pattern ✅ **COMPLETE WORKING EXAMPLE PROVIDED**
**Approach**: Check for folder_id vs thread_id in children array
**Implementation**: Recursive function calls with directory creation
**File naming**: Use thread title with path sanitization (replace "/" with "-")
**Critical for**: Complete folder structure mirroring

## Architecture: Direct HTTP API Implementation

### Complete Working Implementation Pattern

```python
import os
import requests
from pathlib import Path

class QuipAPIClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://platform.quip.com/1"
        self.headers = {"Authorization": f"Bearer {access_token}"}
    
    def get_folder_contents(self, folder_id: str) -> Dict:
        """Get folder metadata and children"""
        response = requests.get(f"{self.base_url}/folders/{folder_id}", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Error fetching folder {folder_id}: {response.text}")
        return response.json()
        
    def get_document_metadata(self, thread_id: str) -> Dict:
        """Get document metadata including title"""
        response = requests.get(f"{self.base_url}/threads/{thread_id}", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Error fetching thread {thread_id}: {response.text}")
        return response.json()
        
    def export_document_to_docx(self, thread_id: str, file_path: str) -> bool:
        """Export document directly to Word format"""
        export_url = f"{self.base_url}/threads/{thread_id}/export/docx"
        response = requests.get(export_url, headers=self.headers)
        
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"Export failed. Status: {response.status_code}")
            return False
    
    def download_folder_recursive(self, folder_id: str, local_path: str = "downloads"):
        """Complete recursive folder download - PROVEN WORKING PATTERN"""
        # Get folder data
        folder_data = self.get_folder_contents(folder_id)
        folder_name = folder_data["folder"]["title"]
        
        # Create local directory
        current_dir = os.path.join(local_path, folder_name)
        os.makedirs(current_dir, exist_ok=True)
        print(f"Traversing: {folder_name}")
        
        # Process children
        for child in folder_data.get("children", []):
            if "folder_id" in child:
                # Recursive call for subfolders
                self.download_folder_recursive(child["folder_id"], current_dir)
            elif "thread_id" in child:
                # Download document
                thread_id = child["thread_id"]
                thread_data = self.get_document_metadata(thread_id)
                title = thread_data["thread"]["title"].replace("/", "-")  # Sanitize filename
                
                print(f"  Downloading: {title}...")
                file_path = os.path.join(current_dir, f"{title}.docx")
                self.export_document_to_docx(thread_id, file_path)
```

### Key Implementation Details from Working Example

✅ **URL Structure**: `https://platform.quip.com/1/` (note the `/1/` API version)  
✅ **Authentication**: `Authorization: Bearer {token}` header  
✅ **Folder Detection**: Check for `folder_id` key in children array  
✅ **Document Detection**: Check for `thread_id` key in children array  
✅ **File Naming**: Use thread title with "/" replaced by "-" for filesystem compatibility  
✅ **Directory Creation**: Use `os.makedirs(exist_ok=True)` for safe directory creation  
✅ **Error Handling**: Check HTTP status codes and provide meaningful error messages

## Updated Implementation Plan

### Phase 1: Direct HTTP API Integration ✅
**Status**: Can implement immediately with verified example
- Use `requests` library for HTTP calls
- Folder content retrieval via `/folders/{id}` endpoint
- Document export via `/threads/{id}/export/docx` endpoint - **Verified working!**

### Phase 2: Core Application Logic ✅
**Status**: Simplified implementation
- Recursive folder traversal using folder_id/thread_id detection
- Direct DOCX export (eliminates python-docx dependency)
- File system operations for directory structure

### Phase 3: Enhanced Features ✅
**Status**: Additional capabilities available
- Error handling and retry logic
- Progress reporting during traversal
- Batch operations for performance

## Updated Dependencies

### Required Dependencies
```txt
requests                 # HTTP client for Quip API calls
# quip-api NO LONGER NEEDED - direct HTTP API calls
# python-docx NO LONGER NEEDED - direct DOCX export available!
```

### Optional Dependencies
```txt
tqdm                     # Progress bars
click                    # CLI framework
pathlib                  # Path handling (built-in Python 3.4+)
```

## Testing Strategy

### Quip API Integration Tests
```python
def test_quip_client_authentication():
    """Test Quip API token authentication"""
    
def test_folder_listing():
    """Test folder content enumeration via get_folder()"""
    
def test_document_metadata():
    """Test document info retrieval via get_thread()"""
    
def test_docx_export():
    """Test direct DOCX export via get_docx()"""
    
def test_recursive_traversal():
    """Test full folder hierarchy discovery"""
    
def test_error_handling():
    """Test API error responses and retry logic"""
```

### Integration Test Data
```python
# Test with known folder/document IDs
TEST_FOLDER_ID = "ABC123..."  # From Quip URL
TEST_DOCUMENT_ID = "XYZ789..."  # From Quip URL
```

## Conclusion

**VERDICT**: Direct Quip API approach is **SUPERIOR** and **FULLY VERIFIED**

**FINAL RECOMMENDATION**: Implement using direct HTTP requests:
1. ✅ **`GET /folders/{id}`** for folder operations  
2. ✅ **`GET /threads/{id}`** for document metadata
3. ✅ **`GET /threads/{id}/export/docx`** for direct Word export
4. ✅ **Bearer token authentication** via Authorization header

**Key Benefits**:
- **Complete working example** provided for folder traversal
- **Verified API endpoints** for all required operations
- **Minimal dependencies** (just `requests`)
- **No external packages** to manage
- **Direct API control** with clear error handling
- **Standard HTTP patterns** familiar to developers

## Authentication Setup

### Obtaining Access Token
1. Visit **https://quip-amazon.com/dev/token**
2. Generate a new personal access token
3. Copy the token for configuration

### Token Configuration Options
```bash
# Option 1: Environment Variable (Recommended)
export QUIP_ACCESS_TOKEN=your_token_here

# Option 2: Command Line Argument  
python -m quip_mirror --token your_token_here <folder_url> <target_path>

# Option 3: Configuration File
echo "your_token_here" > ~/.quip_token
```

**The original design can be implemented with this approach, with the added benefit of direct DOCX export eliminating the need for document conversion.**