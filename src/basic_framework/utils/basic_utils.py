"""
Basic module with core utility functions.
"""

from datetime import datetime
from typing import Collection, Dict, Any


def get_format_now_stamp(with_seconds: bool = False) -> str:
    """Returns a formatted timestamp string."""
    if with_seconds:
        return datetime.now().strftime("%Y%m%d_%H%M_%S")
    else:
        return datetime.now().strftime("%Y%m%d_%H%M")


def is_hyperlink(text: str) -> bool:
    """Checks if text is a hyperlink (starts with 'http')."""
    return len(text) > 4 and text[:4] == "http"



def convert_to_mapping(fields: Collection[str]) -> Dict[str, str]:
    """
    Convert a collection to a dictionary mapping.
    
    Maps each value to itself as key-value pairs.
    
    Args:
        fields: Collection of field names
        
    Returns:
        Dictionary mapping field names to themselves
    """
    mapping: Dict[str, str] = {}
    for field in fields:
        mapping[field] = field
    return mapping


def is_effectively_null(value: Any) -> bool:
    """
    Check if a value is effectively null.
    
    Treats None, empty string, "##!empty!##", and "null" (case-insensitive) as null.
    
    Args:
        value: Value to check
        
    Returns:
        True if value is effectively null
    """
    if value is None:
        return True
    
    str_value = str(value)
    return (str_value == "" or 
            str_value == "##!empty!##" or 
            str_value.lower() == "null")


def escape_access_sql_string(input_str: str) -> str:
    """Escapes special characters for Access SQL queries."""
    output = input_str
    
    # Replace single quotes with double single quotes
    output = output.replace("'", "''")
    
    # Replace square brackets with double square brackets
    output = output.replace("[", "[[")
    output = output.replace("]", "]]")
    
    # Replace wildcards with bracketed versions
    output = output.replace("*", "[*]")
    output = output.replace("%", "[%]")
    output = output.replace("?", "[?]")
    
    return output


def unescape_access_sql_string(input_str: str) -> str:
    """Unescapes Access SQL string."""
    output = input_str
    
    # Remove surrounding quotes if present
    if len(output) >= 2 and output[0] == "'" and output[-1] == "'":
        output = output[1:-1]
    
    # Replace double single quotes with single
    output = output.replace("''", "'")
    
    # Replace double square brackets with single
    output = output.replace("[[", "[")
    output = output.replace("]]", "]")
    
    # Remove brackets around special characters
    output = output.replace("[*]", "*")
    output = output.replace("[%]", "%")
    output = output.replace("[?]", "?")
    
    return output