"""
Command-line interface for the Quip Folder Mirror application.

This module provides the main CLI application that coordinates all components
to perform the folder mirroring operation.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional

from .models import MirrorConfig, ProcessingSummary
from .quip_client import QuipAPIClient, QuipAPIError
from .auth import TokenManager, AuthenticationError
from .traverser import FolderTraverser, TraversalError
from .filesystem import FileSystemManager, FileSystemError
from .converter import DocumentConverter, ConversionError
from .progress import ProgressReporter


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


class QuipMirrorCLI:
    """Main CLI application for Quip Folder Mirror."""
    
    def __init__(self):
        """Initialize the CLI application."""
        self.token_manager = TokenManager()
        self.progress_reporter = ProgressReporter()
    
    def main(self, args: Optional[List[str]] = None) -> int:
        """
        Main entry point for the CLI application.
        
        Args:
            args: Command line arguments (defaults to sys.argv)
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Parse command line arguments
            config = self.parse_arguments(args)
            
            # Discover and validate access token
            token = self.get_access_token(config)
            config.access_token = token
            
            # Validate configuration
            if not self.validate_config(config):
                return 1
            
            # Execute the mirroring operation
            result = self.execute_mirror(config)
            
            # Return appropriate exit code
            return 0 if result.successful_conversions > 0 or result.total_documents == 0 else 1
            
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            return 130  # Standard exit code for Ctrl+C
        except AuthenticationError as e:
            print(f"\nAuthentication Error: {str(e)}")
            return 2
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            print(f"\nUnexpected error: {str(e)}")
            return 1
    
    def parse_arguments(self, args: Optional[List[str]] = None) -> MirrorConfig:
        """
        Parse command line arguments.
        
        Args:
            args: Command line arguments (defaults to sys.argv)
            
        Returns:
            MirrorConfig object with parsed arguments
        """
        parser = argparse.ArgumentParser(
            description="Mirror Quip folders to local filesystem with Word document export",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s https://quip-amazon.com/folder/ABC123 ./local-mirror
  %(prog)s --token YOUR_TOKEN https://quip-amazon.com/folder/ABC123 ./docs
  
Authentication:
  The tool looks for your Quip access token in this order:
  1. --token command line argument
  2. QUIP_ACCESS_TOKEN environment variable  
  3. ~/.quip_token configuration file
  4. Interactive prompt
  
  Get your token at: https://quip-amazon.com/dev/token
            """
        )
        
        # Positional arguments
        parser.add_argument(
            "quip_folder_url",
            help="URL of the Quip folder to mirror (must start with https://quip-amazon.com/)"
        )
        
        parser.add_argument(
            "target_path",
            help="Local directory where the mirrored structure will be created"
        )
        
        # Optional arguments
        parser.add_argument(
            "--token",
            help="Quip personal access token (overrides environment and config file)"
        )
        
        parser.add_argument(
            "--overwrite",
            action="store_true",
            default=True,
            help="Overwrite existing files (default: True)"
        )
        
        parser.add_argument(
            "--no-overwrite",
            action="store_false",
            dest="overwrite",
            help="Do not overwrite existing files"
        )
        
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose output"
        )
        
        parser.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="Suppress progress output"
        )
        
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without actually doing it"
        )
        
        parser.add_argument(
            "--max-depth",
            type=int,
            default=50,
            help="Maximum folder traversal depth (default: 50)"
        )
        
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="API request timeout in seconds (default: 30)"
        )
        
        parser.add_argument(
            "--version",
            action="version",
            version="%(prog)s 0.1.0"
        )
        
        # Parse arguments
        parsed_args = parser.parse_args(args)
        
        # Set up logging level based on verbosity
        if parsed_args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        elif parsed_args.quiet:
            logging.getLogger().setLevel(logging.ERROR)
        
        # Create and return config
        return MirrorConfig(
            quip_folder_url=parsed_args.quip_folder_url,
            target_path=parsed_args.target_path,
            access_token=parsed_args.token,  # Will be resolved later
            overwrite_existing=parsed_args.overwrite
        )
    
    def get_access_token(self, config: MirrorConfig) -> str:
        """
        Discover and validate access token.
        
        Args:
            config: MirrorConfig with potential token
            
        Returns:
            Valid access token
            
        Raises:
            AuthenticationError: If token cannot be discovered or validated
        """
        # Discover token from various sources
        token, source = self.token_manager.discover_token(config.access_token)
        
        if not token:
            raise AuthenticationError("No access token could be discovered")
        
        # Validate the token
        is_valid, message = self.token_manager.validate_token(token)
        
        if not is_valid:
            raise AuthenticationError(f"Token validation failed: {message}")
        
        logger.info(f"Using access token from: {source}")
        return token
    
    def validate_config(self, config: MirrorConfig) -> bool:
        """
        Validate the configuration.
        
        Args:
            config: MirrorConfig to validate
            
        Returns:
            True if configuration is valid
        """
        try:
            config.validate()
            
            # Additional validation
            target_path = Path(config.target_path)
            
            # Check if target path is writable
            if target_path.exists():
                if not target_path.is_dir():
                    print(f"Error: Target path exists but is not a directory: {config.target_path}")
                    return False
                
                # Test write permissions
                test_file = target_path / ".quip_mirror_test"
                try:
                    test_file.touch()
                    test_file.unlink()
                except OSError:
                    print(f"Error: No write permission to target directory: {config.target_path}")
                    return False
            else:
                # Try to create the directory
                try:
                    target_path.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    print(f"Error: Cannot create target directory {config.target_path}: {str(e)}")
                    return False
            
            return True
            
        except ValueError as e:
            print(f"Configuration error: {str(e)}")
            return False
    
    def execute_mirror(self, config: MirrorConfig) -> ProcessingSummary:
        """
        Execute the main mirroring operation.
        
        Args:
            config: Validated MirrorConfig
            
        Returns:
            ProcessingSummary with operation results
        """
        summary = ProcessingSummary()
        
        try:
            # Initialize components
            client = QuipAPIClient(config.access_token)
            filesystem_manager = FileSystemManager(config.target_path, config.overwrite_existing)
            traverser = FolderTraverser(client)
            converter = DocumentConverter(client, filesystem_manager)
            
            # Extract folder ID from URL
            folder_id = client.extract_folder_id_from_url(config.quip_folder_url)
            logger.info(f"Starting mirror operation for folder: {folder_id}")
            
            # Phase 1: Discover folder structure
            print("Discovering folder structure...")
            hierarchy = traverser.traverse(folder_id)
            
            summary.total_folders = hierarchy.total_folders
            summary.total_documents = hierarchy.total_documents
            
            logger.info(f"Discovered {summary.total_folders} folders and {summary.total_documents} documents")
            
            if summary.total_documents == 0:
                print("No documents found in the specified folder.")
                return summary
            
            # Phase 2: Create directory structure
            print("Creating local directory structure...")
            filesystem_manager.create_directory_structure(hierarchy)
            
            # Phase 3: Get all documents with path information
            documents = traverser.build_document_list(hierarchy)
            
            # Update document paths
            for doc_info in documents:
                doc_info.local_file_path = filesystem_manager.get_document_path(doc_info)
            
            # Phase 4: Export documents
            print(f"Exporting {len(documents)} documents...")
            
            # Set up progress reporting
            self.progress_reporter.start_progress(len(documents), "Exporting Documents")
            
            # Create progress callback
            def progress_callback(current: int, total: int, item_name: str):
                self.progress_reporter.update_progress(item_name, current)
            
            # Export documents in batch
            export_results = converter.batch_export(documents, progress_callback)
            
            # Update summary with results
            summary.successful_conversions = len(export_results["successful"])
            summary.failed_conversions = len(export_results["failed"])
            
            # Add errors to summary
            for failed_item in export_results["failed"]:
                summary.add_error(f"{failed_item['document']}: {failed_item['error']}")
            
            # Finish progress reporting
            self.progress_reporter.finish_progress(summary)
            
            # Display additional information
            if export_results["skipped"]:
                print(f"\nSkipped {len(export_results['skipped'])} documents (already exist, overwrite disabled)")
            
            # Clean up empty directories
            removed_dirs = filesystem_manager.cleanup_empty_directories()
            if removed_dirs > 0:
                print(f"Cleaned up {removed_dirs} empty directories")
            
            return summary
            
        except QuipAPIError as e:
            error_msg = f"Quip API error: {str(e)}"
            logger.error(error_msg)
            summary.add_error(error_msg)
            print(f"\nError: {error_msg}")
            return summary
            
        except TraversalError as e:
            error_msg = f"Folder traversal error: {str(e)}"
            logger.error(error_msg)
            summary.add_error(error_msg)
            print(f"\nError: {error_msg}")
            return summary
            
        except FileSystemError as e:
            error_msg = f"File system error: {str(e)}"
            logger.error(error_msg)
            summary.add_error(error_msg)
            print(f"\nError: {error_msg}")
            return summary
            
        except Exception as e:
            error_msg = f"Unexpected error during mirroring: {str(e)}"
            logger.error(error_msg)
            summary.add_error(error_msg)
            print(f"\nError: {error_msg}")
            return summary


def main():
    """Entry point for the command-line interface."""
    cli = QuipMirrorCLI()
    exit_code = cli.main()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()