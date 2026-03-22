"""
Core logging functions separated to avoid circular imports.
Contains log_and_raise and log_msg functions that can be used by all modules.
"""


import sys
from datetime import datetime
from typing import Optional, NoReturn


def _print_red(text: str) -> None:
    """Print text in red color to console.

    Uses ANSI escape codes for coloring. On Windows, enables VT processing
    if not already enabled.

    Args:
        text: The text to print in red.
    """
    # ANSI escape codes for red text
    RED = "\033[91m"
    RESET = "\033[0m"

    # On Windows, ensure VT processing is enabled for ANSI codes
    if sys.platform == 'win32':
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11, ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)

    print(f"{RED}{text}{RESET}", file=sys.stderr)


def log_and_raise(msg: str, exception: Optional[Exception] = None) -> NoReturn:
    """
    Log an error message and raise an exception.
    Simple version without proc_frame dependencies to avoid circular imports.

    Args:
        msg: Error message to log
        exception: Optional exception to preserve and re-raise

    Raises:
        The original exception if provided, otherwise ValueError with msg
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    # Build complete message with exception details if provided
    complete_msg: str = msg

    if exception is not None:
        exc_msg: str = str(exception)
        if exc_msg and exc_msg not in msg:
            complete_msg = f"{msg}: {exc_msg}"

    formatted_msg = f"{timestamp} [LOGGING_FALLBACK] ERROR: {complete_msg}"

    # Print to console in red for immediate feedback
    _print_red(formatted_msg)

    # Raise the appropriate exception
    if exception is not None:
        raise exception
    else:
        raise ValueError(complete_msg)


def log_msg(msg: str):
    """
    Log a message.
    Simple version without proc_frame dependencies to avoid circular imports.

    Args:
        msg (str): The message to log.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    formatted_msg = f"{timestamp} [LOGGING_FALLBACK] INFO: {msg}"

    print(formatted_msg)