"""
Progress reporting functionality for the Quip Folder Mirror application.

This module provides the ProgressReporter class that handles displaying
progress information and user feedback during mirroring operations.
"""

import sys
import time
import logging
from typing import Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import ProcessingSummary


logger = logging.getLogger(__name__)


@dataclass
class ProgressState:
    """Current state of progress tracking."""
    total_items: int = 0
    completed_items: int = 0
    current_item: str = ""
    start_time: Optional[datetime] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ProgressReporter:
    """Handles progress reporting and user feedback during operations."""
    
    def __init__(self, verbose: bool = True, use_colors: bool = True):
        """
        Initialize the progress reporter.
        
        Args:
            verbose: Whether to show detailed progress information
            use_colors: Whether to use colored output (if supported)
        """
        self.verbose = verbose
        self.use_colors = use_colors and self._supports_color()
        self.state = ProgressState()
        self._last_update_time = 0
        self._update_interval = 0.5  # Update every 500ms
        
        # Color codes
        self.colors = {
            'green': '\033[92m' if self.use_colors else '',
            'red': '\033[91m' if self.use_colors else '',
            'yellow': '\033[93m' if self.use_colors else '',
            'blue': '\033[94m' if self.use_colors else '',
            'reset': '\033[0m' if self.use_colors else '',
            'bold': '\033[1m' if self.use_colors else '',
        }
    
    def start_progress(self, total_items: int, operation_name: str = "Processing") -> None:
        """
        Start progress tracking.
        
        Args:
            total_items: Total number of items to process
            operation_name: Name of the operation being performed
        """
        self.state = ProgressState(
            total_items=total_items,
            completed_items=0,
            current_item="",
            start_time=datetime.now(),
            errors=[]
        )
        
        if self.verbose:
            print(f"\n{self.colors['bold']}{operation_name}{self.colors['reset']}")
            print(f"Total items to process: {self.colors['blue']}{total_items}{self.colors['reset']}")
            print("-" * 50)
    
    def update_progress(self, current_item: str, completed: Optional[int] = None) -> None:
        """
        Update progress with current item information.
        
        Args:
            current_item: Name/description of current item being processed
            completed: Optional explicit completed count (auto-increments if None)
        """
        current_time = time.time()
        
        # Update state
        if completed is not None:
            self.state.completed_items = completed
        else:
            self.state.completed_items += 1
        
        self.state.current_item = current_item
        
        # Throttle updates to avoid overwhelming the console
        if current_time - self._last_update_time < self._update_interval:
            return
        
        self._last_update_time = current_time
        
        if self.verbose:
            self._display_progress()
    
    def report_error(self, item: str, error: str) -> None:
        """
        Report an error for a specific item.
        
        Args:
            item: Name of the item that failed
            error: Error message
        """
        error_msg = f"{item}: {error}"
        self.state.errors.append(error_msg)
        
        if self.verbose:
            print(f"\n{self.colors['red']}ERROR:{self.colors['reset']} {error_msg}")
            # Redisplay progress after error
            self._display_progress()
    
    def report_warning(self, item: str, warning: str) -> None:
        """
        Report a warning for a specific item.
        
        Args:
            item: Name of the item with warning
            warning: Warning message
        """
        if self.verbose:
            print(f"\n{self.colors['yellow']}WARNING:{self.colors['reset']} {item}: {warning}")
            # Redisplay progress after warning
            self._display_progress()
    
    def report_success(self, item: str, message: str = "") -> None:
        """
        Report successful processing of an item.
        
        Args:
            item: Name of the successfully processed item
            message: Optional success message
        """
        if self.verbose and message:
            success_msg = f"{self.colors['green']}✓{self.colors['reset']} {item}"
            if message:
                success_msg += f": {message}"
            print(f"\n{success_msg}")
            # Redisplay progress after success message
            self._display_progress()
    
    def finish_progress(self, summary: ProcessingSummary) -> None:
        """
        Finish progress tracking and display final summary.
        
        Args:
            summary: ProcessingSummary with final results
        """
        if not self.verbose:
            return
        
        # Calculate elapsed time
        elapsed_time = datetime.now() - self.state.start_time if self.state.start_time else timedelta(0)
        
        print("\n" + "=" * 60)
        print(f"{self.colors['bold']}MIRRORING COMPLETE{self.colors['reset']}")
        print("=" * 60)
        
        # Display summary statistics
        print(f"Total folders processed: {self.colors['blue']}{summary.total_folders}{self.colors['reset']}")
        print(f"Total documents found: {self.colors['blue']}{summary.total_documents}{self.colors['reset']}")
        print(f"Successful conversions: {self.colors['green']}{summary.successful_conversions}{self.colors['reset']}")
        print(f"Failed conversions: {self.colors['red']}{summary.failed_conversions}{self.colors['reset']}")
        print(f"Success rate: {self.colors['green']}{summary.success_rate:.1f}%{self.colors['reset']}")
        print(f"Total time: {self.colors['blue']}{self._format_duration(elapsed_time)}{self.colors['reset']}")
        
        # Display errors if any
        if summary.errors:
            print(f"\n{self.colors['red']}Errors encountered:{self.colors['reset']}")
            for i, error in enumerate(summary.errors[:10], 1):  # Show first 10 errors
                print(f"  {i}. {error}")
            
            if len(summary.errors) > 10:
                print(f"  ... and {len(summary.errors) - 10} more errors")
        
        print("=" * 60)
    
    def _display_progress(self) -> None:
        """Display current progress information."""
        if self.state.total_items == 0:
            return
        
        percentage = (self.state.completed_items / self.state.total_items) * 100
        
        # Create progress bar
        bar_width = 30
        filled_width = int(bar_width * percentage / 100)
        bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        # Calculate ETA
        eta_str = self._calculate_eta()
        
        # Format current item (truncate if too long)
        current_item = self.state.current_item
        if len(current_item) > 40:
            current_item = current_item[:37] + "..."
        
        # Display progress line
        progress_line = (
            f"\r{self.colors['blue']}[{bar}]{self.colors['reset']} "
            f"{percentage:5.1f}% "
            f"({self.state.completed_items}/{self.state.total_items}) "
            f"{eta_str} "
            f"| {current_item}"
        )
        
        # Clear the line and print progress
        print(" " * 100, end="\r")  # Clear line
        print(progress_line, end="", flush=True)
    
    def _calculate_eta(self) -> str:
        """Calculate estimated time of arrival."""
        if not self.state.start_time or self.state.completed_items == 0:
            return "ETA: --:--"
        
        elapsed = datetime.now() - self.state.start_time
        rate = self.state.completed_items / elapsed.total_seconds()
        
        if rate > 0:
            remaining_items = self.state.total_items - self.state.completed_items
            eta_seconds = remaining_items / rate
            eta = timedelta(seconds=int(eta_seconds))
            return f"ETA: {self._format_duration(eta)}"
        else:
            return "ETA: --:--"
    
    def _format_duration(self, duration: timedelta) -> str:
        """Format a duration for display."""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def _supports_color(self) -> bool:
        """Check if the terminal supports color output."""
        # Simple check for color support
        return (
            hasattr(sys.stdout, 'isatty') and 
            sys.stdout.isatty() and 
            'TERM' in os.environ and 
            os.environ['TERM'] != 'dumb'
        )
    
    def set_verbosity(self, verbose: bool) -> None:
        """Set verbosity level."""
        self.verbose = verbose
    
    def get_progress_percentage(self) -> float:
        """Get current progress as percentage."""
        if self.state.total_items == 0:
            return 0.0
        return (self.state.completed_items / self.state.total_items) * 100
    
    def get_elapsed_time(self) -> timedelta:
        """Get elapsed time since progress started."""
        if self.state.start_time:
            return datetime.now() - self.state.start_time
        return timedelta(0)
    
    def create_callback(self) -> Callable:
        """
        Create a callback function for use with other components.
        
        Returns:
            Callback function that can be passed to batch operations
        """
        def progress_callback(current: int, total: int, item_name: str):
            self.update_progress(item_name, current)
        
        return progress_callback


# Import os for environment variable check
import os