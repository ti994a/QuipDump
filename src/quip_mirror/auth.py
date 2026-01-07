"""
Authentication management for Quip API access.

This module provides functionality for discovering and validating Quip access tokens
from various sources including command line, environment variables, and config files.
"""

import os
import getpass
import logging
from pathlib import Path
from typing import Optional, Tuple

from .quip_client import QuipAPIClient


logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Exception raised for authentication-related errors."""
    pass


class TokenManager:
    """Manages Quip access token discovery and validation."""
    
    TOKEN_ENV_VAR = "QUIP_ACCESS_TOKEN"
    TOKEN_CONFIG_FILE = "~/.quip_token"
    TOKEN_URL = "https://quip-amazon.com/dev/token"
    
    def __init__(self):
        """Initialize the token manager."""
        self.discovered_token: Optional[str] = None
        self.token_source: Optional[str] = None
    
    def discover_token(self, cli_token: Optional[str] = None) -> Tuple[Optional[str], str]:
        """
        Discover access token from various sources in priority order.
        
        Priority order:
        1. Command line argument
        2. Environment variable
        3. Configuration file
        4. Interactive prompt
        
        Args:
            cli_token: Token provided via command line argument
            
        Returns:
            Tuple of (token, source_description)
            
        Raises:
            AuthenticationError: If no token can be discovered
        """
        # 1. Check command line argument (highest priority)
        if cli_token:
            logger.debug("Using token from command line argument")
            self.discovered_token = cli_token
            self.token_source = "command line argument"
            return cli_token, "command line argument"
        
        # 2. Check environment variable
        env_token = os.environ.get(self.TOKEN_ENV_VAR)
        if env_token:
            logger.debug("Using token from environment variable")
            self.discovered_token = env_token
            self.token_source = f"environment variable ({self.TOKEN_ENV_VAR})"
            return env_token, f"environment variable ({self.TOKEN_ENV_VAR})"
        
        # 3. Check configuration file
        config_token = self._read_config_file()
        if config_token:
            logger.debug("Using token from configuration file")
            self.discovered_token = config_token
            self.token_source = f"configuration file ({self.TOKEN_CONFIG_FILE})"
            return config_token, f"configuration file ({self.TOKEN_CONFIG_FILE})"
        
        # 4. Interactive prompt (lowest priority)
        interactive_token = self._prompt_for_token()
        if interactive_token:
            logger.debug("Using token from interactive prompt")
            self.discovered_token = interactive_token
            self.token_source = "interactive prompt"
            return interactive_token, "interactive prompt"
        
        # No token found
        raise AuthenticationError(
            "No Quip access token found. Please provide a token using one of these methods:\n"
            f"  1. Command line: --token YOUR_TOKEN\n"
            f"  2. Environment variable: export {self.TOKEN_ENV_VAR}=YOUR_TOKEN\n"
            f"  3. Configuration file: echo 'YOUR_TOKEN' > {self.TOKEN_CONFIG_FILE}\n"
            f"  4. Interactive prompt (will be shown automatically)\n\n"
            f"Get your token at: {self.TOKEN_URL}"
        )
    
    def validate_token(self, token: str) -> Tuple[bool, str]:
        """
        Validate a Quip access token by testing API access.
        
        Args:
            token: Access token to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not token or not token.strip():
            return False, "Token is empty or invalid"
        
        # Basic format validation
        token = token.strip()
        if len(token) < 10:
            return False, "Token appears to be too short"
        
        try:
            # Test the token by creating a client and testing connection
            client = QuipAPIClient(token)
            is_valid, message = client.test_connection()
            
            if is_valid:
                logger.debug("Token validation successful")
                return True, "Token is valid and authenticated successfully"
            else:
                logger.warning(f"Token validation failed: {message}")
                return False, f"Token validation failed: {message}"
                
        except Exception as e:
            error_msg = f"Error validating token: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _read_config_file(self) -> Optional[str]:
        """
        Read token from configuration file.
        
        Returns:
            Token string if found, None otherwise
        """
        try:
            config_path = Path(self.TOKEN_CONFIG_FILE).expanduser()
            
            if not config_path.exists():
                logger.debug(f"Configuration file not found: {config_path}")
                return None
            
            if not config_path.is_file():
                logger.warning(f"Configuration path exists but is not a file: {config_path}")
                return None
            
            # Read token from file
            token = config_path.read_text().strip()
            
            if not token:
                logger.warning(f"Configuration file is empty: {config_path}")
                return None
            
            # Take only the first line in case there are multiple lines
            token = token.split('\n')[0].strip()
            
            logger.debug(f"Read token from configuration file: {config_path}")
            return token
            
        except Exception as e:
            logger.warning(f"Error reading configuration file {self.TOKEN_CONFIG_FILE}: {str(e)}")
            return None
    
    def _prompt_for_token(self) -> Optional[str]:
        """
        Prompt user interactively for access token.
        
        Returns:
            Token string if provided, None if cancelled
        """
        try:
            print("\n" + "=" * 60)
            print("Quip Access Token Required")
            print("=" * 60)
            print(f"No access token found in environment or configuration.")
            print(f"Please obtain a token from: {self.TOKEN_URL}")
            print("\nInstructions:")
            print("1. Visit the URL above in your browser")
            print("2. Click 'Generate' to create a new personal access token")
            print("3. Copy the generated token")
            print("4. Paste it below (input will be hidden for security)")
            print("\nPress Ctrl+C to cancel.")
            print("-" * 60)
            
            # Prompt for token with hidden input
            token = getpass.getpass("Enter your Quip access token: ")
            
            if not token or not token.strip():
                print("No token provided.")
                return None
            
            token = token.strip()
            
            # Ask if user wants to save the token
            save_choice = input("\nSave token to configuration file for future use? (y/N): ").strip().lower()
            if save_choice in ('y', 'yes'):
                if self._save_token_to_config(token):
                    print(f"Token saved to {self.TOKEN_CONFIG_FILE}")
                else:
                    print("Failed to save token to configuration file")
            
            return token
            
        except KeyboardInterrupt:
            print("\n\nToken input cancelled by user.")
            return None
        except Exception as e:
            logger.error(f"Error during interactive token prompt: {str(e)}")
            print(f"\nError during token input: {str(e)}")
            return None
    
    def _save_token_to_config(self, token: str) -> bool:
        """
        Save token to configuration file.
        
        Args:
            token: Token to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            config_path = Path(self.TOKEN_CONFIG_FILE).expanduser()
            
            # Create parent directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write token to file with restricted permissions
            config_path.write_text(token)
            
            # Set restrictive permissions (owner read/write only)
            config_path.chmod(0o600)
            
            logger.debug(f"Saved token to configuration file: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving token to configuration file: {str(e)}")
            return False
    
    def get_token_guidance(self) -> str:
        """
        Get guidance text for obtaining a Quip access token.
        
        Returns:
            Formatted guidance text
        """
        return f"""
Quip Access Token Setup Guide
============================

To use this tool, you need a Quip personal access token.

Step 1: Get Your Token
---------------------
Visit: {self.TOKEN_URL}
Click "Generate" to create a new personal access token
Copy the generated token

Step 2: Configure Your Token
----------------------------
Choose one of these methods:

Method 1 - Environment Variable (Recommended):
  export {self.TOKEN_ENV_VAR}=YOUR_TOKEN_HERE

Method 2 - Configuration File:
  echo "YOUR_TOKEN_HERE" > {self.TOKEN_CONFIG_FILE}

Method 3 - Command Line Argument:
  quip-mirror --token YOUR_TOKEN_HERE <folder_url> <target_path>

Method 4 - Interactive Prompt:
  The tool will prompt you automatically if no token is found

Security Notes:
--------------
- Keep your token secure and don't share it
- The token provides access to all your Quip content
- Configuration file permissions are automatically set to owner-only
- Tokens can be regenerated if compromised

Troubleshooting:
---------------
- Ensure the token hasn't expired
- Verify you have access to the Quip folder you're trying to mirror
- Check your network connection to quip-amazon.com
"""
    
    def clear_cached_token(self) -> None:
        """Clear any cached token information."""
        self.discovered_token = None
        self.token_source = None
    
    def get_current_token_info(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get information about the currently discovered token.
        
        Returns:
            Tuple of (token, source) or (None, None) if no token discovered
        """
        return self.discovered_token, self.token_source