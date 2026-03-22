

from .basic_utils import is_hyperlink

# Directory separator constant (will be used by other modules)
C_DIR_SEPARATOR = "\\"

def get_name_from_full_reference(fullname: str, remove_postfix: bool = True) -> str:
    """Extracts filename from full path/URL."""
    if is_hyperlink(fullname):
        separator = "/"
    else:
        # Support both Windows (\) and Unix (/) path separators
        if "\\" in fullname:
            separator = "\\"
        elif "/" in fullname:
            separator = "/"
        else:
            raise ValueError(f"GetNameFromFullReference: '{fullname}' ist keine Dateireferenz.")

    parts = fullname.split(separator)
    length = len(parts)
    if length == 0:
        raise ValueError("GetNameFromFullReference: Behandlung der Länge 0 nicht möglich.")

    # Get the last element (filename)
    name = parts[length - 1]

    if remove_postfix:
        return remove_file_postfix(name)
    else:
        return name


def remove_file_postfix(name: str) -> str:
    """Removes file extension from filename."""
    parts = name.split(".")
    length = len(parts)
    if length == 0:
        raise ValueError("RemoveFilePostfix: Behandlung der Länge 0 nicht möglich.")
    
    if length == 1:
        return parts[0]
    
    # Remove the extension
    postfix = parts[length - 1]
    return name[:-(len(postfix) + 1)]  # +1 for the dot


def get_path_from_full_reference(fullname: str) -> str:
    """Extracts path from full filename."""
    if is_hyperlink(fullname):
        separator = "/"
    else:
        # Support both Windows (\) and Unix (/) path separators
        if "\\" in fullname:
            separator = "\\"
        elif "/" in fullname:
            separator = "/"
        else:
            raise ValueError(f"GetPathFromFullReference: '{fullname}' ist keine Dateireferenz.")

    parts = fullname.split(separator)
    length = len(parts)
    if length == 0:
        raise ValueError("GetPathFromFullReference: Behandlung der Länge 0 nicht möglich.")

    # Return everything except the last part (filename)
    filename = parts[length - 1]
    return fullname[:-(len(filename) + 1)]  # +1 for separator
