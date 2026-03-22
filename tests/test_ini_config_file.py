"""
Unit tests for IniConfigFile class.

Tests for:
- Basic configuration loading
- Section inheritance (parent_section)
- Circular reference detection
- Type conversion (int, float, bool)
- Error handling
"""

import os
from pathlib import Path

import pytest

os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"

from basic_framework.ini_config_file import IniConfigFile


class TestIniConfigFileInit:
    """Tests for IniConfigFile initialization."""

    def test_load_valid_config(self, sample_ini_file: Path) -> None:
        """Test loading a valid INI file."""
        config = IniConfigFile(sample_ini_file)
        assert config is not None
        assert config.has_section("default")
        assert config.has_section("production")

    def test_file_not_found_raises_error(self, temp_dir: Path) -> None:
        """Test that non-existent file raises FileNotFoundError."""
        nonexistent = temp_dir / "nonexistent.ini"
        with pytest.raises(FileNotFoundError) as exc_info:
            IniConfigFile(nonexistent)
        assert "nicht gefunden" in str(exc_info.value)

    def test_accepts_string_path(self, sample_ini_file: Path) -> None:
        """Test that string path is accepted."""
        config = IniConfigFile(str(sample_ini_file))
        assert config.has_section("default")

    def test_accepts_path_object(self, sample_ini_file: Path) -> None:
        """Test that Path object is accepted."""
        config = IniConfigFile(sample_ini_file)
        assert config.has_section("default")


class TestIniConfigFileSections:
    """Tests for section-related methods."""

    def test_get_sections(self, sample_ini_file: Path) -> None:
        """Test getting all sections."""
        config = IniConfigFile(sample_ini_file)
        sections = config.get_sections()
        assert "default" in sections
        assert "logging" in sections
        assert "production" in sections
        assert "development" in sections

    def test_has_section_existing(self, sample_ini_file: Path) -> None:
        """Test has_section for existing section."""
        config = IniConfigFile(sample_ini_file)
        assert config.has_section("default") is True
        assert config.has_section("production") is True

    def test_has_section_nonexistent(self, sample_ini_file: Path) -> None:
        """Test has_section for non-existent section."""
        config = IniConfigFile(sample_ini_file)
        assert config.has_section("nonexistent") is False

    def test_get_options(self, sample_ini_file: Path) -> None:
        """Test getting options from a section."""
        config = IniConfigFile(sample_ini_file)
        options = config.get_options("default")
        assert "single_instance" in options
        assert "timeout" in options


class TestIniConfigFileGetValue:
    """Tests for get_value method."""

    def test_get_existing_value(self, sample_ini_file: Path) -> None:
        """Test getting an existing value."""
        config = IniConfigFile(sample_ini_file)
        value = config.get_value("timeout", "default")
        assert value == "30"

    def test_get_value_from_parent_section(self, sample_ini_file: Path) -> None:
        """Test value inheritance from parent_section."""
        config = IniConfigFile(sample_ini_file)
        # production inherits from default, but overrides timeout
        timeout = config.get_value("timeout", "production")
        assert timeout == "60"  # Overridden in production

        # debug should be inherited from default
        debug = config.get_value("debug", "production")
        assert debug == "true"  # Inherited from default

    def test_get_value_deep_inheritance(self, sample_ini_file: Path) -> None:
        """Test deep inheritance chain (development -> production -> default)."""
        config = IniConfigFile(sample_ini_file)
        # development -> production -> default
        debug = config.get_value("debug", "development")
        assert debug == "true"  # From default (via production)

        # database_host is overridden in development
        host = config.get_value("database_host", "development")
        assert host == "localhost"

    def test_get_value_must_exist_raises(self, sample_ini_file: Path) -> None:
        """Test that must_exist=True raises for missing option."""
        config = IniConfigFile(sample_ini_file)
        with pytest.raises(ValueError):
            config.get_value("nonexistent_option", "default", must_exist=True)

    def test_get_value_optional_returns_none(self, sample_ini_file: Path) -> None:
        """Test that must_exist=False returns None for missing option."""
        config = IniConfigFile(sample_ini_file)
        value = config.get_value("nonexistent_option", "default", must_exist=False)
        assert value is None

    def test_has_option(self, sample_ini_file: Path) -> None:
        """Test has_option method."""
        config = IniConfigFile(sample_ini_file)
        assert config.has_option("timeout", "default") is True
        assert config.has_option("nonexistent", "default") is False


class TestIniConfigFileTypeConversion:
    """Tests for type conversion methods."""

    def test_get_int_value(self, sample_ini_file: Path) -> None:
        """Test getting integer value."""
        config = IniConfigFile(sample_ini_file)
        value = config.get_int_value("timeout", "default")
        assert value == 30
        assert isinstance(value, int)

    def test_get_int_value_inherited(self, sample_ini_file: Path) -> None:
        """Test getting inherited integer value."""
        config = IniConfigFile(sample_ini_file)
        # development inherits timeout from production (60)
        value = config.get_int_value("timeout", "development")
        assert value == 60

    def test_get_int_value_optional_none(self, sample_ini_file: Path) -> None:
        """Test get_int_value returns None for missing optional."""
        config = IniConfigFile(sample_ini_file)
        value = config.get_int_value("nonexistent", "default", must_exist=False)
        assert value is None

    def test_get_float_value(self, temp_dir: Path) -> None:
        """Test getting float value."""
        ini_path = temp_dir / "float_test.ini"
        ini_path.write_text(
            """[default]
single_instance = false
rate = 3.14
""",
            encoding="utf-8",
        )
        config = IniConfigFile(ini_path)
        value = config.get_float_value("rate", "default")
        assert value == 3.14
        assert isinstance(value, float)

    def test_get_float_value_invalid_raises(self, temp_dir: Path) -> None:
        """Test that invalid float raises ValueError."""
        ini_path = temp_dir / "invalid_float.ini"
        ini_path.write_text(
            """[default]
single_instance = false
rate = not_a_number
""",
            encoding="utf-8",
        )
        config = IniConfigFile(ini_path)
        with pytest.raises(ValueError) as exc_info:
            config.get_float_value("rate", "default")
        assert "Float" in str(exc_info.value) or "float" in str(exc_info.value)

    def test_get_bool_value_true_variants(self, temp_dir: Path) -> None:
        """Test boolean true values."""
        ini_path = temp_dir / "bool_test.ini"
        ini_path.write_text(
            """[default]
single_instance = false
flag1 = true
flag2 = True
flag3 = yes
flag4 = ja
flag5 = wahr
flag6 = 1
""",
            encoding="utf-8",
        )
        config = IniConfigFile(ini_path)
        assert config.get_bool_value("flag1", "default") is True
        assert config.get_bool_value("flag2", "default") is True
        assert config.get_bool_value("flag3", "default") is True
        assert config.get_bool_value("flag4", "default") is True
        assert config.get_bool_value("flag5", "default") is True
        assert config.get_bool_value("flag6", "default") is True

    def test_get_bool_value_false_variants(self, temp_dir: Path) -> None:
        """Test boolean false values."""
        ini_path = temp_dir / "bool_false.ini"
        ini_path.write_text(
            """[default]
single_instance = false
flag1 = false
flag2 = False
flag3 = no
flag4 = nein
flag5 = falsch
flag6 = 0
""",
            encoding="utf-8",
        )
        config = IniConfigFile(ini_path)
        assert config.get_bool_value("flag1", "default") is False
        assert config.get_bool_value("flag2", "default") is False
        assert config.get_bool_value("flag3", "default") is False
        assert config.get_bool_value("flag4", "default") is False
        assert config.get_bool_value("flag5", "default") is False
        assert config.get_bool_value("flag6", "default") is False

    def test_get_bool_value_invalid_raises(self, temp_dir: Path) -> None:
        """Test that invalid boolean raises ValueError."""
        ini_path = temp_dir / "invalid_bool.ini"
        ini_path.write_text(
            """[default]
single_instance = false
flag = maybe
""",
            encoding="utf-8",
        )
        config = IniConfigFile(ini_path)
        with pytest.raises(ValueError) as exc_info:
            config.get_bool_value("flag", "default")
        assert "boolsch" in str(exc_info.value)


class TestIniConfigFileParentSectionValidation:
    """Tests for parent_section validation."""

    def test_circular_reference_raises_error(self, circular_ini_file: Path) -> None:
        """Test that circular parent_section references raise error."""
        with pytest.raises(ValueError) as exc_info:
            IniConfigFile(circular_ini_file)
        assert "Zirkuläre" in str(exc_info.value) or "zirkulär" in str(exc_info.value).lower()

    def test_invalid_parent_raises_error(self, invalid_parent_ini_file: Path) -> None:
        """Test that non-existent parent_section raises error."""
        with pytest.raises(ValueError) as exc_info:
            IniConfigFile(invalid_parent_ini_file)
        assert "existiert nicht" in str(exc_info.value)


class TestIniConfigFileUtilityMethods:
    """Tests for utility methods."""

    def test_get_section_dict(self, sample_ini_file: Path) -> None:
        """Test getting section as dictionary."""
        config = IniConfigFile(sample_ini_file)
        section_dict = config.get_section_dict("default")
        assert "timeout" in section_dict
        assert section_dict["timeout"] == "30"

    def test_get_all_config(self, sample_ini_file: Path) -> None:
        """Test getting complete configuration."""
        config = IniConfigFile(sample_ini_file)
        all_config = config.get_all_config()
        assert "default" in all_config
        assert "production" in all_config
        assert all_config["default"]["timeout"] == "30"

    def test_reload(self, temp_dir: Path) -> None:
        """Test reloading configuration."""
        ini_path = temp_dir / "reload_test.ini"
        ini_path.write_text(
            """[default]
single_instance = false
value = original
""",
            encoding="utf-8",
        )

        config = IniConfigFile(ini_path)
        assert config.get_value("value", "default") == "original"

        # Modify file
        ini_path.write_text(
            """[default]
single_instance = false
value = modified
""",
            encoding="utf-8",
        )

        # Reload and check
        config.reload()
        assert config.get_value("value", "default") == "modified"

    def test_str_representation(self, sample_ini_file: Path) -> None:
        """Test string representation."""
        config = IniConfigFile(sample_ini_file)
        str_repr = str(config)
        assert "IniConfigFile" in str_repr
        assert "sections=" in str_repr

    def test_repr_representation(self, sample_ini_file: Path) -> None:
        """Test repr representation."""
        config = IniConfigFile(sample_ini_file)
        repr_str = repr(config)
        assert "IniConfigFile" in repr_str
        assert "file_path" in repr_str
