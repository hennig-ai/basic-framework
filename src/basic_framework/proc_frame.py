"""
Process framework, logging functionality and global INI parameters.
"""

import os
import sys
from typing import Optional, Any, Dict, NoReturn, Union

from .ini_config_file import IniConfigFile
from .logging_object import LoggingObject

# Platform-specific imports
if sys.platform == 'win32':
    import msvcrt
    import winsound
else:
    import fcntl
    winsound = None

# Constants for INI parameters
C_TMP_DIR = "tmp_dir"
C_SINGLE_INSTANCE = "single_instance"

# Module-level variables for logging
_default_logger: Optional[LoggingObject] = None
_initialized = False

# Module-level variables for INI parameters
_ini_pars: Optional[Dict[str, str]] = None

# Global singleton instance of IniConfigFile
_ini_config_file: Optional[IniConfigFile] = None

# Module-level variables for process lock
_lock_file_handle: Optional[Any] = None
_lock_file_path: Optional[str] = None
_is_child_of_lock_holder: bool = False  # True if parent process holds the lock


def _is_process_alive(pid: int) -> bool:
    """Check if a process with given PID exists.

    Uses platform-specific methods to check process existence without
    sending any signals or affecting the target process.

    Args:
        pid: The process ID to check.

    Returns:
        True if the process exists, False otherwise.
    """
    if sys.platform == 'win32':
        # Windows: Use ctypes to call OpenProcess
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        # Unix/Linux/macOS: Use signal 0 to check existence
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

# Module-level variable for config directory (base for relative paths)
_config_dir: Optional[str] = None


def _read_bool_config(name: str, section: str, default: bool) -> bool:
    """Read a boolean configuration value with default.

    Args:
        name: Parameter name.
        section: Section name.
        default: Default value if not found.

    Returns:
        The boolean value or default.
    """
    if _ini_config_file is None:
        return default
    if not _ini_config_file.has_option(name, section):
        return default
    value = _ini_config_file.get_value(name, section)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "wahr", "ja")


def _read_string_config(name: str, section: str, default: Optional[str]) -> Optional[str]:
    """Read a string configuration value with default.

    Args:
        name: Parameter name.
        section: Section name.
        default: Default value if not found.

    Returns:
        The string value or default.
    """
    if _ini_config_file is None:
        return default
    if not _ini_config_file.has_option(name, section):
        return default
    value = _ini_config_file.get_value(name, section, must_exist=False)
    if value is None or value == "":
        return default
    return value

# Environment variable to disable beeps (useful for unit tests)
_BEEP_DISABLED: bool = os.environ.get("BASIC_FRAMEWORK_DISABLE_BEEP", "").lower() in ("1", "true", "yes")

# Configuration for beep on process end (read from INI during proc_frame_start)
_beep_on_end: bool = False


def beep_tone_proc_frame_end():
    """Play end of process beep sequence."""
    if _BEEP_DISABLED:
        return
    if winsound is None:
        print('\a')  # Fallback beep on non-Windows
        return
    try:
        winsound.Beep(700, 500)
        winsound.Beep(795, 500)
        winsound.Beep(700, 500)
    except Exception:
        print('\a')  # Fallback beep


def beep_tone_error():
    """Play error beep sequence."""
    if _BEEP_DISABLED:
        return
    if winsound is None:
        print('\a\a\a')  # Fallback beep on non-Windows
        return
    try:
        winsound.Beep(750, 200)
        winsound.Beep(750, 200)
    except Exception:
        print('\a\a\a')  # Fallback beep


def beep_attention():
    """Play attention beep sequence."""
    if _BEEP_DISABLED:
        return
    if winsound is None:
        print('\a\a')  # Fallback beep on non-Windows
        return
    try:
        winsound.Beep(600, 300)
        winsound.Beep(800, 300)
    except Exception:
        print('\a\a')  # Fallback beep

def get_ini_config_file() -> Optional[IniConfigFile]:
    """Get the global singleton IniConfigFile instance.

    Returns:
        Optional[IniConfigFile]: The global config file instance or None if not initialized.
    """
    return _ini_config_file


def get_config_dir() -> str:
    """Get the config directory (directory containing the config.ini file).

    This is the base directory for resolving relative paths in the config file.

    Returns:
        str: Absolute path to the config directory.

    Raises:
        RuntimeError: If proc_frame_start() has not been called yet.
    """
    if _config_dir is None:
        raise RuntimeError("Config directory not set. Call proc_frame_start() first.")
    return _config_dir


def resolve_config_path(path_str: str) -> str:
    """Resolve a path relative to the config directory.

    Absolute paths are returned unchanged.
    Relative paths are resolved relative to the config directory.

    Args:
        path_str: The path to resolve (absolute or relative).

    Returns:
        str: The resolved absolute path.

    Raises:
        RuntimeError: If proc_frame_start() has not been called yet.
    """
    if _config_dir is None:
        raise RuntimeError("Config directory not set. Call proc_frame_start() first.")

    path = os.path.expandvars(path_str)  # Expand %TEMP% etc.

    if os.path.isabs(path):
        return path

    # Resolve relative to config directory
    return os.path.normpath(os.path.join(_config_dir, path))


def _acquire_process_lock(app_name: str) -> None:
    """Acquire an exclusive filesystem lock to prevent multiple instances.

    Creates a lock file in the directory specified by tmp_dir config parameter.
    Uses platform-specific locking mechanisms (msvcrt on Windows, fcntl on Unix).

    If the lock is held by the parent process (e.g., Uvicorn reloader spawning
    a worker), this is considered valid and no lock is acquired. This allows
    subprocess-based reload mechanisms to work correctly.

    Args:
        app_name: The application name used for the lock file name.

    Raises:
        ValueError: If tmp_dir is not configured or another instance is already running.
    """
    global _lock_file_handle, _lock_file_path, _is_child_of_lock_holder

    # _ini_config_file must be set before calling this function
    assert _ini_config_file is not None

    # Read tmp_dir from config - optional, defaults to ./tmp
    if _ini_config_file.has_option(C_TMP_DIR, "default"):
        tmp_dir_raw = _ini_config_file.get_value(C_TMP_DIR, "default")
        if not tmp_dir_raw:
            tmp_dir_raw = "./tmp"
    else:
        tmp_dir_raw = "./tmp"

    # Resolve path relative to config directory (also expands env vars)
    tmp_dir = resolve_config_path(tmp_dir_raw)

    # Create tmp_dir if it doesn't exist
    if not os.path.isdir(tmp_dir):
        os.makedirs(tmp_dir, exist_ok=True)

    # Create lock file path
    _lock_file_path = os.path.join(tmp_dir, f"{app_name}.lock")

    log_msg(f"Checking lock file: {_lock_file_path}, exists: {os.path.exists(_lock_file_path)}, my PID: {os.getpid()}, parent PID: {os.getppid()}")

    # Check if lock is held by parent process (e.g., Uvicorn reloader)
    # or if lock is stale (process that held it is dead)
    if os.path.exists(_lock_file_path):
        try:
            with open(_lock_file_path, 'r', encoding='utf-8') as f:
                lock_content = f.read().strip()
                log_msg(f"Lock file content: '{lock_content}' (length: {len(lock_content)})")
                if lock_content:
                    locked_pid = int(lock_content)
                    parent_pid = os.getppid()

                    log_msg(f"Lock file contains PID {locked_pid}, my PID is {os.getpid()}, my parent PID is {parent_pid}")

                    if locked_pid == parent_pid:
                        # Lock is held by our parent process - this is OK
                        # We are a child process (e.g., Uvicorn reload worker)
                        _is_child_of_lock_holder = True
                        log_msg(f"Lock held by parent process (PID {locked_pid}), continuing as child process")
                        return

                    # Check if the process that holds the lock is still alive
                    if not _is_process_alive(locked_pid):
                        # Stale lock - process is dead, we can take over
                        log_msg(f"Stale lock detected (PID {locked_pid} is dead), taking over lock")
                        # Continue to acquire lock normally
                    else:
                        log_msg(f"Process {locked_pid} is still alive, will try to acquire lock")
        except (ValueError, FileNotFoundError, PermissionError) as e:
            # Lock file corrupt, gone, or unreadable - proceed with normal lock acquisition
            log_msg(f"Could not read lock file: {type(e).__name__}: {e}")

    # Try to acquire exclusive lock
    try:
        # Open file for writing (create if not exists)
        _lock_file_handle = open(_lock_file_path, 'w', encoding='utf-8')

        if sys.platform == 'win32':
            # Windows: use msvcrt.locking with LK_NBLCK (non-blocking exclusive lock)
            msvcrt.locking(_lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            # Unix/Linux/macOS: use fcntl.flock with LOCK_EX | LOCK_NB
            fcntl.flock(_lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        # Write PID to lock file for debugging purposes
        _lock_file_handle.write(str(os.getpid()))
        _lock_file_handle.flush()

    except (IOError, OSError):
        # Lock acquisition failed - another instance is running
        if _lock_file_handle:
            _lock_file_handle.close()
            _lock_file_handle = None

        # Check if parent process is running - could be Uvicorn reload case
        # On Windows, we can't read the lock file content because it's exclusively locked
        parent_pid = os.getppid()
        if _is_process_alive(parent_pid):
            # Parent is running and holds the lock - we're likely a child process
            # (e.g., Uvicorn reload worker spawned by Reloader)
            _is_child_of_lock_holder = True
            log_msg(f"Parent process (PID {parent_pid}) is running, assuming it holds the lock - continuing as child process")
            return

        _lock_file_path = None
        log_and_raise(f"Another instance of '{app_name}' is already running. Lock file: {tmp_dir}/{app_name}.lock")


def _release_process_lock() -> None:
    """Release the filesystem lock and clean up the lock file.

    Called during proc_frame_end() to release the exclusive lock and
    delete the lock file.

    If this process is a child of the lock holder (e.g., Uvicorn worker),
    the lock is NOT released - the parent process maintains ownership.
    """
    global _lock_file_handle, _lock_file_path, _is_child_of_lock_holder

    # Child processes don't own the lock - parent process does
    if _is_child_of_lock_holder:
        _is_child_of_lock_holder = False
        return

    if _lock_file_handle is None:
        return

    try:
        if sys.platform == 'win32':
            # Windows: unlock before closing
            try:
                msvcrt.locking(_lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            except (IOError, OSError):
                pass  # Ignore unlock errors during cleanup
        else:
            # Unix: flock is automatically released on close, but explicit unlock is cleaner
            try:
                fcntl.flock(_lock_file_handle.fileno(), fcntl.LOCK_UN)
            except (IOError, OSError):
                pass  # Ignore unlock errors during cleanup

        _lock_file_handle.close()
    except (IOError, OSError):
        pass  # Ignore close errors during cleanup
    finally:
        _lock_file_handle = None

    # Delete lock file
    if _lock_file_path and os.path.exists(_lock_file_path):
        try:
            os.remove(_lock_file_path)
        except (IOError, OSError):
            pass  # Ignore delete errors during cleanup
        finally:
            _lock_file_path = None


def proc_frame_start(app_name: str, app_version: str, config_file_path: str, dir_hint_for_http: str = ""):
    """Initialize the process framework with logging and configuration.

    Sets up global logging, loads INI configuration file, and initializes
    the application environment. Creates log directory and file automatically.
    Optionally acquires an exclusive filesystem lock to prevent multiple instances.

    The directory containing the config file becomes the base directory for:
    - Log files (created in {config_dir}/logs/)
    - Resolving relative paths in config (via resolve_config_path())

    Args:
        app_name (str): Name of the application for logging purposes.
        app_version (str): Version of the application (e.g., "1.2.3").
        config_file_path (str): Path to the INI configuration file.
        dir_hint_for_http (str, optional): Directory hint for HTTP operations. Defaults to "".

    Required config parameters in [default] section:
        single_instance: true/false - Enable single instance mode with filesystem lock.

    Optional config parameters in [default] section:
        tmp_dir: Directory for lock file (default: ./tmp, relative to config file).

    Raises:
        ValueError: If app_name is empty, single_instance is not configured,
                   or another instance is already running (when single_instance=true).
        FileNotFoundError: If config file cannot be found or opened.
    """
    global _default_logger, _initialized, _ini_config_file, _lock_file_handle, _lock_file_path, _config_dir, _beep_on_end

    # Validate app_name - must not be empty
    if not app_name:
        log_and_raise("app_name is required and cannot be empty")

    # Validate app_version - must not be empty
    if not app_version:
        log_and_raise("app_version is required and cannot be empty")

    # Set config directory (base for all relative paths)
    _config_dir = os.path.dirname(os.path.abspath(config_file_path))

    # Initialize global singleton IniConfigFile - central config management
    try:
        _ini_config_file = IniConfigFile(config_file_path)
    except (FileNotFoundError, Exception):
        log_and_raise(f"Fehler beim Lesen der Configdatei: {config_file_path}")

    # Read logging configuration from INI (with defaults)
    console_output = _read_bool_config("console_output", "logging", True)
    include_stacktrace = _read_bool_config("include_stacktrace", "logging", True)
    copy_on_error = _read_bool_config("copy_on_error", "logging", True)
    error_log_dir = _read_string_config("error_log_dir", "logging", "errors")
    error_log_auto_copy_dir = _read_string_config("error_log_auto_copy_dir", "logging", None)
    _beep_on_end = _read_bool_config("beep_on_end", "logging", False)

    # Validate error_log_auto_copy_dir if specified
    if error_log_auto_copy_dir and not os.path.isdir(error_log_auto_copy_dir):
        log_and_raise(f"error_log_auto_copy_dir '{error_log_auto_copy_dir}' does not exist or is not a directory")

    # Read single_instance configuration - required parameter
    assert _ini_config_file is not None
    if not _ini_config_file.has_option(C_SINGLE_INSTANCE, "default"):
        log_and_raise(f"Config parameter '{C_SINGLE_INSTANCE}' is required in section [default]")

    single_instance_value = _ini_config_file.get_value(C_SINGLE_INSTANCE, "default")
    if single_instance_value is None or single_instance_value == "":
        log_and_raise(f"Config parameter '{C_SINGLE_INSTANCE}' cannot be empty")

    single_instance_lower: str = single_instance_value.lower()
    if single_instance_lower not in ("true", "false", "1", "0", "yes", "no"):
        log_and_raise(
            f"Config parameter '{C_SINGLE_INSTANCE}' has invalid value '{single_instance_value}'. "
            f"Expected: true/false, yes/no, 1/0"
        )

    single_instance: bool = single_instance_lower in ("true", "1", "yes")

    # Acquire exclusive filesystem lock only if single_instance is enabled
    if single_instance:
        _acquire_process_lock(app_name)

    # Create LoggingObject with all configuration
    log_dir = os.path.join(_config_dir, "logs")
    _default_logger = LoggingObject(
        app_name=app_name,
        app_version=app_version,
        log_dir=log_dir,
        console_output=console_output,
        include_stacktrace=include_stacktrace,
        copy_on_error=copy_on_error,
        error_log_dir=error_log_dir if error_log_dir else "errors",
        error_log_auto_copy_dir=error_log_auto_copy_dir,
    )

    _initialized = True
    log_msg("Prozess gestartet.")


def get_log_filename() -> str:
    """Get the current log filename without path.

    Returns:
        str: The log filename (without directory path) or empty string if not set.
    """
    if _default_logger is not None:
        return _default_logger.log_filename
    return ""


def get_app_version() -> str:
    """Get the application version.

    Returns:
        str: The application version set during proc_frame_start() or empty string if not set.
    """
    if _default_logger is not None:
        return _default_logger.app_version
    return ""


def get_app_name() -> str:
    """Get the application name.

    Returns:
        str: The application name set during proc_frame_start() or empty string if not set.
    """
    if _default_logger is not None:
        return _default_logger.app_name
    return ""


def get_default_logger() -> Optional[LoggingObject]:
    """Get the default LoggingObject instance.

    Returns:
        The default LoggingObject or None if not initialized.
    """
    return _default_logger


def log_msg(msg: str, obj: Any = None) -> None:
    """Log a message with timestamp and caller information.

    Delegates to the default LoggingObject if initialized, otherwise falls back
    to simple console logging.

    Args:
        msg (str): The message to log.
        obj (Any, optional): Legacy parameter for object context. Not currently used.

    Note:
        Uses frame inspection to automatically determine the calling method and class.
        Format: "timestamp;app_name;app_version;pid;thread_id;thread_name;class;method;message"
    """
    if _default_logger is not None:
        # caller_frame_offset=2: log_msg -> LoggingObject.log_msg -> actual caller
        _default_logger.log_msg(msg, caller_frame_offset=2)
    else:
        # Fallback to simple logging if not initialized
        from .logging import log_msg as simple_log_msg
        simple_log_msg(msg)


def log_and_raise(error: Union[str, Exception]) -> NoReturn:
    """
    Log an error message and raise an exception.

    Delegates to the default LoggingObject if initialized, otherwise falls back
    to simple logging.

    Args:
        error: Either an error message string or an Exception object.
               - str: Logs the message and raises ValueError with it.
               - Exception: Logs exception details with stacktrace and re-raises it.

    Raises:
        The original exception if Exception provided, otherwise ValueError with msg.

    Note:
        This function never returns (NoReturn type).
        Stack traces are always included for Exception objects.
        Error messages are printed in red color for visibility.
    """
    if _default_logger is not None:
        # caller_frame_offset=2: log_and_raise -> LoggingObject.log_and_raise -> actual caller
        _default_logger.log_and_raise(error, caller_frame_offset=2)
    else:
        # Fallback to simple logging if not initialized
        from .logging import log_and_raise as simple_log_and_raise
        if isinstance(error, Exception):
            simple_log_and_raise(str(error), error)
        else:
            simple_log_and_raise(error, None)
        # Unreachable - simple_log_and_raise always raises
        raise SystemExit("Unreachable")


def close_log() -> None:
    """Close the log file.

    Safely closes the log file handle.
    Handles exceptions gracefully to prevent issues during shutdown.
    """
    if _default_logger is not None:
        _default_logger.close()


def proc_frame_end(beep: Optional[bool] = None, close_log_flag: bool = True):
    """Gracefully terminate the process framework.

    Logs completion message, optionally plays completion beep, closes log file,
    releases the process lock, and optionally opens the log file in the default
    text editor before exiting.

    Args:
        beep (bool, optional): Whether to play completion beep. If None (default),
            uses the INI config value [logging] beep_on_end (default: false).
            Explicit True/False overrides the INI config.
        close_log_flag (bool, optional): Whether to close and optionally open log file. Defaults to True.

    Note:
        Releases the filesystem lock acquired during proc_frame_start().
        Calls sys.exit(0) to terminate the application.
    """
    # Determine whether to beep: explicit parameter overrides INI config
    should_beep = beep if beep is not None else _beep_on_end
    if should_beep:
        beep_tone_proc_frame_end()

    log_msg("Prozess beendet.")

    if close_log_flag:
        close_log()
    elif _default_logger is not None:
        # Preserve log file path before closing handle
        log_file_path = _default_logger.log_filepath
        close_log()

        # Attempt to open log file in default text editor for review
        if log_file_path:
            try:
                if hasattr(os, 'startfile'):  # Windows
                    os.startfile(log_file_path)
                else:  # Unix/Linux/Mac - use open command
                    os.system(f'open "{log_file_path}"')
            except Exception as e:
                log_msg(f"Could not open log file: {e}")
                log_msg(f"Log file location: {log_file_path}")

    # Release process lock before exiting
    _release_process_lock()

    # Terminate application
    # Clean exit with code 0 indicates successful completion
    sys.exit(0)


# =============================================================================
# Global INI Parameter Functions (merged from global_ini_parameter.py)
# =============================================================================

def get_global_par(name: str, section: str = "default") -> str:
    """Retrieve a parameter value from the global INI configuration.

    Args:
        name (str): The parameter name to retrieve.
        section (str, optional): The INI section name. Defaults to "default".

    Returns:
        str: The parameter value or empty string if not found.

    Raises:
        ValueError: If IniConfigFile is not initialized or parameter not found.
    """
    if _ini_config_file is None:
        log_and_raise("IniConfigFile nicht initialisiert. Bitte proc_frame_start() aufrufen.")
        return ""
    
    try:
        result: Optional[str] = _ini_config_file.get_value(name, section)
        return result if result is not None else ""
    except Exception as e:
        log_and_raise(f"GetInitParameter: Parameter '{name}' in Sektion '{section}' nicht gefunden. Fehler: {e}")
        return ""


def global_ini_par_exists(name: str, section: str = "default") -> bool:
    """Check if a parameter exists in the global INI configuration.

    Args:
        name (str): The parameter name to check.
        section (str, optional): The INI section name. Defaults to "default".

    Returns:
        bool: True if parameter exists, False otherwise.
    """
    if _ini_config_file is None:
        return False

    return _ini_config_file.has_option(name, section)


def get_global_par_int(name: str, section: str = "default") -> int:
    """Retrieve an integer parameter from the global INI configuration.

    Args:
        name: The parameter name to retrieve.
        section: The INI section name. Defaults to "default".

    Returns:
        int: The parameter value as integer.

    Raises:
        ValueError: If not initialized, not found, or not a valid integer.
    """
    if _ini_config_file is None:
        log_and_raise("IniConfigFile nicht initialisiert. Bitte proc_frame_start() aufrufen.")

    result = _ini_config_file.get_int_value(name, section)
    if result is None:
        log_and_raise(f"Parameter '{name}' in Sektion '{section}' nicht gefunden.")
    return result


def get_global_par_float(name: str, section: str = "default") -> float:
    """Retrieve a float parameter from the global INI configuration.

    Args:
        name: The parameter name to retrieve.
        section: The INI section name. Defaults to "default".

    Returns:
        float: The parameter value as float.

    Raises:
        ValueError: If not initialized, not found, or not a valid float.
    """
    if _ini_config_file is None:
        log_and_raise("IniConfigFile nicht initialisiert. Bitte proc_frame_start() aufrufen.")

    result = _ini_config_file.get_float_value(name, section)
    if result is None:
        log_and_raise(f"Parameter '{name}' in Sektion '{section}' nicht gefunden.")
    return result


def get_global_par_bool(name: str, section: str = "default") -> bool:
    """Retrieve a boolean parameter from the global INI configuration.

    Args:
        name: The parameter name to retrieve.
        section: The INI section name. Defaults to "default".

    Returns:
        bool: The parameter value as boolean.
        Accepts: true/false, yes/no, 1/0, wahr/falsch (case-insensitive)

    Raises:
        ValueError: If not initialized, not found, or not a valid boolean.
    """
    if _ini_config_file is None:
        log_and_raise("IniConfigFile nicht initialisiert. Bitte proc_frame_start() aufrufen.")

    result = _ini_config_file.get_bool_value(name, section)
    if result is None:
        log_and_raise(f"Parameter '{name}' in Sektion '{section}' nicht gefunden.")
    return result


# =============================================================================
# Environment Variable Functions
# =============================================================================

def env_par_exists(name: str) -> bool:
    """Check if an environment variable exists.

    Args:
        name: The environment variable name to check.

    Returns:
        bool: True if the environment variable exists, False otherwise.

    Note:
        Does NOT log the variable value for security reasons.
    """
    return name in os.environ


def get_env_value(name: str) -> str:
    """Retrieve an environment variable value.

    Args:
        name: The environment variable name to retrieve.

    Returns:
        str: The environment variable value. Empty string is a valid value.

    Raises:
        ValueError: If the environment variable does not exist.

    Note:
        - Does NOT log the variable value for security reasons (may contain secrets).
        - Empty string is ALLOWED (different from INI parameters).
        - Use env_par_exists() to check existence before calling if needed.
    """
    log_msg(f"Reading environment variable: {name}")

    try:
        return os.environ[name]
    except KeyError:
        log_and_raise(f"Environment variable '{name}' is not set")


def get_env_int_value(name: str) -> int:
    """Retrieve an environment variable value as integer.

    Args:
        name: The environment variable name to retrieve.

    Returns:
        int: The environment variable value converted to integer.

    Raises:
        ValueError: If the environment variable does not exist or cannot be
                   converted to integer.

    Note:
        Does NOT log the variable value for security reasons.
    """
    value: str = get_env_value(name)

    try:
        return int(value)
    except ValueError:
        log_and_raise(
            f"Environment variable '{name}' value cannot be converted to integer"
        )


def get_env_float_value(name: str) -> float:
    """Retrieve an environment variable value as float.

    Args:
        name: The environment variable name to retrieve.

    Returns:
        float: The environment variable value converted to float.

    Raises:
        ValueError: If the environment variable does not exist or cannot be
                   converted to float.

    Note:
        Does NOT log the variable value for security reasons.
    """
    value: str = get_env_value(name)

    try:
        return float(value)
    except ValueError:
        log_and_raise(
            f"Environment variable '{name}' value cannot be converted to float"
        )


def get_env_bool_value(name: str) -> bool:
    """Retrieve an environment variable value as boolean.

    Args:
        name: The environment variable name to retrieve.

    Returns:
        bool: The environment variable value converted to boolean.

    Raises:
        ValueError: If the environment variable does not exist or has an
                   unrecognized boolean value.

    Note:
        - Does NOT log the variable value for security reasons.
        - Recognized true values (case-insensitive): 'true', 'wahr', 'yes', 'ja', '1'
        - Recognized false values (case-insensitive): 'false', 'falsch', 'no', 'nein', '0'
        - Consistent with IniConfigFile.get_bool_value() behavior.
    """
    value: str = get_env_value(name)
    lower_value: str = value.lower()

    if lower_value in ('true', 'wahr', 'yes', 'ja', '1'):
        return True

    if lower_value in ('false', 'falsch', 'no', 'nein', '0'):
        return False

    log_and_raise(
        f"Environment variable '{name}' has unrecognized boolean value. "
        f"Expected: true/false, yes/no, 1/0, wahr/falsch, ja/nein"
    )

