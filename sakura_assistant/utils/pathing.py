import os
import sys

def normalize_path(path: str) -> str:
    """
    Normalizes a file path to be absolute and OS-compliant.
    - Expands ~ to user home directory.
    - Converts backslashes/forward slashes to OS default.
    - Resolves relative paths against the current working directory.
    """
    if not path:
        return ""
        
    # Expand user home (e.g. ~/Documents -> C:/Users/Name/Documents)
    path = os.path.expanduser(path)
    
    # Expand environment variables (e.g. %APPDATA%)
    path = os.path.expandvars(path)
    
    # Make absolute
    path = os.path.abspath(path)
    
    # Normalize slashes
    path = os.path.normpath(path)
    
    return path

def get_project_root() -> str:
    """Returns the root directory of the project."""
    # Assuming this file is in sakura_assistant/utils/pathing.py
    # Root is two levels up
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))
