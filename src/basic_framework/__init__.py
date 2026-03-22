"""
Basic Framework Package

A Python framework providing:
- Abstract containers and iterators
- Condition handling (equals, not, and operations)
- File system extensions
- Configuration file handling
- Text file processing as tables
- Logging and process frame management

Originally part of the Krefeld Prototype project.
"""

from importlib.metadata import version

__version__ = version("basic-framework")

# Core abstract classes
from .container_utils.abstract_container import AbstractContainer
from .container_utils.abstract_iterator import AbstractIterator

# Condition classes
from .conditions.condition import Condition
from .conditions.condition_and import ConditionAnd
from .conditions.condition_equals import ConditionEquals
from .conditions.condition_not import ConditionNot
from .conditions.condition_or import ConditionOr


# Core utilities
from .utils.basic_utils import (
    get_format_now_stamp,
    is_hyperlink,
    escape_access_sql_string,
    unescape_access_sql_string,
    convert_to_mapping,
    is_effectively_null
)

from .utils.filename_utils import (
    get_name_from_full_reference,
    remove_file_postfix,
    get_path_from_full_reference,
    C_DIR_SEPARATOR
)

# File system extensions
from .ext_filesystem import (
    file_exists,
    file_must_exist,
    directory_must_exist,
    replace_path
)

# Configuration
from .ini_config_file import IniConfigFile

# Logging Object
from .logging_object import LoggingObject

# Process framework and logging
from .proc_frame import (
    proc_frame_start,
    proc_frame_end,
    log_msg,
    log_and_raise,
    get_global_par,
    get_global_par_int,
    get_global_par_float,
    get_global_par_bool,
    get_ini_config_file,
    get_log_filename,
    get_app_name,
    get_app_version,
    get_default_logger,
    global_ini_par_exists,
    get_config_dir,
    resolve_config_path,
    # Environment Variable Support
    env_par_exists,
    get_env_value,
    get_env_int_value,
    get_env_float_value,
    get_env_bool_value,
)

# Container utilities
from .container_utils.static_container_basics import create_new_iterator
from .container_utils.text_file_as_table import TextFileAsTable
from .container_utils.markdown_file_as_table import MarkdownFileAsTable

# Markdown utilities
from .utils.markdown_document import (
    MarkdownDocument,
    MarkdownLineType,
    MarkdownParserState,
)

# Database classes
from .database.abstract_database import AbstractDatabase, DatabaseCursor
from .database.sqlite_db import SQLiteDB
from .database.ms_access_db import MSAccessDB
from .database.database_container import DatabaseContainer

__all__ = [
    # Abstract classes
    'AbstractContainer',
    'AbstractIterator',
    
    # Conditions
    'Condition',
    'ConditionAnd',
    'ConditionEquals',
    'ConditionNot',
    'ConditionOr',
    
    
    # Basic utilities
    'get_format_now_stamp',
    'is_hyperlink',
    'escape_access_sql_string',
    'unescape_access_sql_string',
    'convert_to_mapping',
    'is_effectively_null',
    
    # Filename utilities
    'get_name_from_full_reference',
    'remove_file_postfix', 
    'get_path_from_full_reference',
    'C_DIR_SEPARATOR',
    
    # File system
    'file_exists',
    'file_must_exist',
    'directory_must_exist',
    'replace_path',
    
    # Configuration
    'IniConfigFile',

    # Logging
    'LoggingObject',

    # Process framework
    'proc_frame_start',
    'proc_frame_end',
    'log_msg',
    'log_and_raise',
    'get_global_par',
    'get_global_par_int',
    'get_global_par_float',
    'get_global_par_bool',
    'get_ini_config_file',
    'get_log_filename',
    'get_app_name',
    'get_app_version',
    'get_default_logger',
    'global_ini_par_exists',
    'get_config_dir',
    'resolve_config_path',

    # Environment Variable Support
    'env_par_exists',
    'get_env_value',
    'get_env_int_value',
    'get_env_float_value',
    'get_env_bool_value',

    # Containers
    'create_new_iterator',
    'TextFileAsTable',
    'MarkdownFileAsTable',

    # Markdown
    'MarkdownDocument',
    'MarkdownLineType',
    'MarkdownParserState',

    # Database
    'AbstractDatabase',
    'DatabaseCursor',
    'SQLiteDB',
    'MSAccessDB',
    'DatabaseContainer',
]