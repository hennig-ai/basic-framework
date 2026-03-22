"""
Extended filesystem operations module.

This module provides enhanced file and directory operations with path replacement
functionality and comprehensive error checking.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .utils.basic_utils import is_hyperlink
from .proc_frame import log_and_raise, log_msg

# Constants
C_DIR_SEPARATOR = "\\"

# Module-level variables for path replacement functionality
_replace_this = ""
_replace_by = ""


def remember_replacement(hint: str) -> None:
    """
    Remember path replacement rule for URL to local path mapping.
    
    Args:
        hint: String in format "http://url=local_path"
        
    Raises:
        ValueError: If replacement hint doesn't start with 'http'
    """
    global _replace_this, _replace_by
    
    parts = hint.split("=", 1)
    if len(parts) != 2:
        log_and_raise(f"Invalid replacement hint format: {hint}")
        return
    
    _replace_this = parts[0]
    if not _replace_this.startswith("http"):
        log_and_raise(f"Unzulässiges Replacement für {_replace_this}")
        return
    
    _replace_by = parts[1]


def replace_path(file_path: str) -> str:
    """
    Replace path according to remembered replacement rule.
    
    Args:
        file_path: Original file path
        
    Returns:
        Replaced file path or original if no replacement applies
    """
    if not _replace_this:
        return file_path
    
    if file_path.startswith(_replace_this):
        return _replace_by + file_path[len(_replace_this):]
    
    return file_path


def ext_file_copy(source_file_in: str, target_file_in: str, overwrite: bool = False) -> None:
    """
    Copy file with comprehensive validation.
    
    Args:
        source_file_in: Source file path
        target_file_in: Target file path  
        overwrite: Whether to overwrite existing target file
        
    Raises:
        FileNotFoundError: If source file doesn't exist
        FileExistsError: If target exists and overwrite=False
        OSError: If target directory doesn't exist or copy fails
    """
    source_file = replace_path(source_file_in)
    target_file = replace_path(target_file_in)
    
    # Check if source file exists
    if not os.path.exists(source_file):
        log_and_raise(f"Zu kopierende Datei '{source_file}' existiert nicht. Abbruch.")
        return
    
    # Check if target file already exists
    if os.path.exists(target_file) and not overwrite:
        log_and_raise(f"Zu kopierende Zieldatei '{target_file}' existiert schon. Abbruch.")
        return
    
    # Check if target directory exists
    target_dir = os.path.dirname(target_file)
    if not os.path.exists(target_dir):
        log_and_raise(f"Zielpfad '{target_dir}' existiert nicht. Abbruch.")
        return
    
    try:
        log_msg(f"Kopiere {source_file} nach {target_file}...")
        shutil.copy2(source_file, target_file)
    except Exception as e:
        log_and_raise(f"Fehler beim Kopieren: {e}")


def ext_get_folder(folder_in: str) -> Optional[Path]:
    """
    Get folder as Path object with validation.
    
    Args:
        folder_in: Folder path
        
    Returns:
        Path object if folder exists, None otherwise
    """
    folder = replace_path(folder_in)
    if not os.path.exists(folder) or not os.path.isdir(folder):
        log_and_raise(f"Verzeichnis '{folder}' existiert nicht. Abbruch.")
        return None
    
    return Path(folder)


def directory_exists(pattern_in: str) -> bool:
    """
    Check if directory exists.
    
    Args:
        pattern_in: Directory path to check
        
    Returns:
        True if directory exists, False otherwise
    """
    pattern = replace_path(pattern_in)
    
    # Skip validation for hyperlinks
    if is_hyperlink(pattern):
        return False
    
    return os.path.exists(pattern) and os.path.isdir(pattern)


def file_must_exist(pattern_in: str) -> None:
    """
    Assert that file exists, log error if not.
    
    Args:
        pattern_in: File path to check
    """
    pattern = replace_path(pattern_in)
    
    # Skip validation for hyperlinks
    if is_hyperlink(pattern):
        return
    
    if not file_exists(pattern):
        log_and_raise(f"MustExist: Datei '{pattern}' nicht gefunden.")


def directory_must_exist(pattern_in: str) -> None:
    """
    Assert that directory exists, log error if not.
    
    Args:
        pattern_in: Directory path to check
    """
    pattern = replace_path(pattern_in)
    
    # Skip validation for hyperlinks
    if is_hyperlink(pattern):
        return
    
    if not directory_exists(pattern):
        log_and_raise(f"MustExist: Verzeichnis '{pattern}' nicht gefunden.")


def ext_file_delete(file_in: str) -> None:
    """
    Delete file with validation.
    
    Args:
        file_in: File path to delete
    """
    file_path = replace_path(file_in)
    
    file_must_exist(file_path)
    
    try:
        os.remove(file_path)
    except PermissionError:
        log_and_raise(f"ExtFileDelete: Das Löschen der Datei '{file_path}' war nicht möglich, wahrscheinlich ist sie noch geöffnet.")
    except Exception as e:
        log_and_raise(f"ExtFileDelete: Unerwarteter Fehler: {e}")


def file_last_modified(file_in: str) -> Optional[datetime]:
    """
    Get file's last modification time.
    
    Args:
        file_in: File path
        
    Returns:
        Modification time as datetime, None if file doesn't exist
    """
    file_path = replace_path(file_in)
    
    file_must_exist(file_path)
    
    try:
        timestamp = os.path.getmtime(file_path)
        return datetime.fromtimestamp(timestamp)
    except OSError:
        return None


def file_exists(pattern_in: str) -> bool:
    """
    Check if file exists.
    
    Args:
        pattern_in: File path to check
        
    Returns:
        True if file exists, False otherwise
    """
    pattern = replace_path(pattern_in)
    
    # Skip validation for hyperlinks
    if is_hyperlink(pattern):
        return False
    
    return os.path.exists(pattern) and os.path.isfile(pattern)



def get_files_in_directory(path: str) -> Dict[str, str]:
    """
    Get all files in a directory as dictionary.
    
    Args:
        path: Directory path
        
    Returns:
        Dictionary with file paths as both keys and values
    """
    files_dict: Dict[str, str] = {}
    
    # Check if directory exists
    directory_must_exist(path)
    
    try:
        folder_path = ext_get_folder(path)
        if folder_path is None:
            return files_dict
        
        # Iterate through all files in directory
        for file_path in folder_path.iterdir():
            if file_path.is_file():
                full_path = str(file_path)
                # Use full path as both key and value
                if full_path not in files_dict:
                    files_dict[full_path] = full_path
        
        log_msg(f"Es wurden {len(files_dict)} Dateien im Verzeichnis '{path}' gefunden.")
        
    except Exception as e:
        log_and_raise(f"Fehler beim Lesen des Verzeichnisses: {e}")
    
    return files_dict


# Export directory separator constant
__all__ = [
    'C_DIR_SEPARATOR',
    'remember_replacement', 
    'replace_path',
    'ext_file_copy',
    'ext_get_folder', 
    'directory_exists',
    'file_must_exist',
    'directory_must_exist', 
    'ext_file_delete',
    'file_last_modified',
    'file_exists',
    'get_files_in_directory'
]