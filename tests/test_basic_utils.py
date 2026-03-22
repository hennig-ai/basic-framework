"""
Unit tests for basic_utils module.

Tests for:
- get_format_now_stamp()
- is_hyperlink()
- escape_access_sql_string()
- unescape_access_sql_string()
- is_effectively_null()
- convert_to_mapping()
"""

import os
import re
from datetime import datetime

import pytest

os.environ["BASIC_FRAMEWORK_DISABLE_BEEP"] = "1"

from basic_framework.utils.basic_utils import (
    get_format_now_stamp,
    is_hyperlink,
    escape_access_sql_string,
    unescape_access_sql_string,
    is_effectively_null,
    convert_to_mapping,
)


# =============================================================================
# get_format_now_stamp Tests
# =============================================================================


class TestGetFormatNowStamp:
    """Tests for get_format_now_stamp() function."""

    def test_returns_string(self) -> None:
        """Test that function returns a string."""
        result = get_format_now_stamp()
        assert isinstance(result, str)

    def test_format_without_seconds(self) -> None:
        """Test format without seconds: YYYYMMDD_HHMM."""
        result = get_format_now_stamp(with_seconds=False)
        # Should match pattern like 20240115_1430
        assert re.match(r"^\d{8}_\d{4}$", result) is not None

    def test_format_with_seconds(self) -> None:
        """Test format with seconds: YYYYMMDD_HHMM_SS."""
        result = get_format_now_stamp(with_seconds=True)
        # Should match pattern like 20240115_1430_25
        assert re.match(r"^\d{8}_\d{4}_\d{2}$", result) is not None

    def test_with_seconds_longer(self) -> None:
        """Test that with_seconds produces longer string."""
        without = get_format_now_stamp(with_seconds=False)
        with_sec = get_format_now_stamp(with_seconds=True)
        assert len(with_sec) > len(without)

    def test_contains_current_date(self) -> None:
        """Test that result contains current date."""
        result = get_format_now_stamp()
        today = datetime.now().strftime("%Y%m%d")
        assert result.startswith(today)


# =============================================================================
# is_hyperlink Tests
# =============================================================================


class TestIsHyperlink:
    """Tests for is_hyperlink() function."""

    def test_http_url_returns_true(self) -> None:
        """Test that http:// URLs return True."""
        assert is_hyperlink("http://example.com") is True
        assert is_hyperlink("http://example.com/path/file.txt") is True

    def test_https_url_returns_true(self) -> None:
        """Test that https:// URLs return True."""
        assert is_hyperlink("https://example.com") is True
        assert is_hyperlink("https://secure.example.com/api") is True

    def test_local_path_returns_false(self) -> None:
        """Test that local paths return False."""
        assert is_hyperlink("C:\\path\\file.txt") is False
        assert is_hyperlink("/usr/local/bin") is False

    def test_relative_path_returns_false(self) -> None:
        """Test that relative paths return False."""
        assert is_hyperlink("./file.txt") is False
        assert is_hyperlink("../parent/file.txt") is False

    def test_plain_text_returns_false(self) -> None:
        """Test that plain text returns False."""
        assert is_hyperlink("simple_text") is False
        assert is_hyperlink("not a url") is False

    def test_short_string_returns_false(self) -> None:
        """Test that strings <= 4 chars return False."""
        assert is_hyperlink("http") is False
        assert is_hyperlink("htt") is False
        assert is_hyperlink("") is False

    def test_case_sensitivity(self) -> None:
        """Test that check is case-sensitive (http only lowercase)."""
        # Current implementation checks lowercase only
        assert is_hyperlink("HTTP://example.com") is False
        assert is_hyperlink("Http://example.com") is False


# =============================================================================
# escape_access_sql_string Tests
# =============================================================================


class TestEscapeAccessSqlString:
    """Tests for escape_access_sql_string() function."""

    def test_escapes_single_quotes(self) -> None:
        """Test that single quotes are doubled."""
        result = escape_access_sql_string("test's value")
        assert result == "test''s value"

    def test_escapes_multiple_quotes(self) -> None:
        """Test multiple single quotes."""
        result = escape_access_sql_string("it's a test's example")
        assert result == "it''s a test''s example"

    def test_escapes_square_brackets(self) -> None:
        """Test that square brackets are doubled."""
        result = escape_access_sql_string("field[0]")
        assert result == "field[[0]]"

    def test_escapes_asterisk(self) -> None:
        """Test that asterisk is bracketed."""
        result = escape_access_sql_string("test*value")
        assert result == "test[*]value"

    def test_escapes_percent(self) -> None:
        """Test that percent is bracketed."""
        result = escape_access_sql_string("100%")
        assert result == "100[%]"

    def test_escapes_question_mark(self) -> None:
        """Test that question mark is bracketed."""
        result = escape_access_sql_string("what?")
        assert result == "what[?]"

    def test_plain_string_unchanged(self) -> None:
        """Test that plain strings are unchanged."""
        result = escape_access_sql_string("plain string 123")
        assert result == "plain string 123"

    def test_empty_string(self) -> None:
        """Test empty string handling."""
        result = escape_access_sql_string("")
        assert result == ""

    def test_combined_escaping(self) -> None:
        """Test multiple special characters together."""
        result = escape_access_sql_string("test's [field]* 100%?")
        assert "''" in result
        assert "[[" in result
        assert "[*]" in result
        assert "[%]" in result
        assert "[?]" in result


# =============================================================================
# unescape_access_sql_string Tests
# =============================================================================


class TestUnescapeAccessSqlString:
    """Tests for unescape_access_sql_string() function."""

    def test_unescapes_double_quotes(self) -> None:
        """Test that doubled quotes become single."""
        result = unescape_access_sql_string("test''s value")
        assert result == "test's value"

    def test_unescapes_square_brackets(self) -> None:
        """Test that doubled brackets become single."""
        result = unescape_access_sql_string("field[[0]]")
        assert result == "field[0]"

    def test_unescapes_asterisk(self) -> None:
        """Test that bracketed asterisk is unbracketed."""
        result = unescape_access_sql_string("test[*]value")
        assert result == "test*value"

    def test_unescapes_percent(self) -> None:
        """Test that bracketed percent is unbracketed."""
        result = unescape_access_sql_string("100[%]")
        assert result == "100%"

    def test_unescapes_question_mark(self) -> None:
        """Test that bracketed question mark is unbracketed."""
        result = unescape_access_sql_string("what[?]")
        assert result == "what?"

    def test_removes_surrounding_quotes(self) -> None:
        """Test that surrounding single quotes are removed."""
        result = unescape_access_sql_string("'quoted string'")
        assert result == "quoted string"

    def test_plain_string_unchanged(self) -> None:
        """Test that plain strings are unchanged."""
        result = unescape_access_sql_string("plain string")
        assert result == "plain string"

    def test_roundtrip(self) -> None:
        """Test that escape then unescape returns original."""
        original = "test's [field]* 100%?"
        escaped = escape_access_sql_string(original)
        unescaped = unescape_access_sql_string(escaped)
        assert unescaped == original


# =============================================================================
# is_effectively_null Tests
# =============================================================================


class TestIsEffectivelyNull:
    """Tests for is_effectively_null() function."""

    def test_none_is_null(self) -> None:
        """Test that None is effectively null."""
        assert is_effectively_null(None) is True

    def test_empty_string_is_null(self) -> None:
        """Test that empty string is effectively null."""
        assert is_effectively_null("") is True

    def test_empty_marker_is_null(self) -> None:
        """Test that special empty marker is null."""
        assert is_effectively_null("##!empty!##") is True

    def test_null_string_is_null(self) -> None:
        """Test that 'null' string (case-insensitive) is null."""
        assert is_effectively_null("null") is True
        assert is_effectively_null("NULL") is True
        assert is_effectively_null("Null") is True

    def test_non_empty_string_is_not_null(self) -> None:
        """Test that non-empty strings are not null."""
        assert is_effectively_null("test") is False
        assert is_effectively_null("value") is False

    def test_whitespace_is_not_null(self) -> None:
        """Test that whitespace-only strings are not null."""
        # Current implementation does not treat whitespace as null
        assert is_effectively_null(" ") is False
        assert is_effectively_null("  ") is False

    def test_zero_is_not_null(self) -> None:
        """Test that zero is not null."""
        assert is_effectively_null(0) is False
        assert is_effectively_null(0.0) is False

    def test_false_is_not_null(self) -> None:
        """Test that False is not null."""
        assert is_effectively_null(False) is False

    def test_empty_list_is_not_null(self) -> None:
        """Test that empty list is not null (converts to string)."""
        # str([]) = "[]" which is not empty
        assert is_effectively_null([]) is False


# =============================================================================
# convert_to_mapping Tests
# =============================================================================


class TestConvertToMapping:
    """Tests for convert_to_mapping() function."""

    def test_list_to_mapping(self) -> None:
        """Test converting list to mapping."""
        fields = ["name", "value", "status"]
        result = convert_to_mapping(fields)
        assert result == {"name": "name", "value": "value", "status": "status"}

    def test_tuple_to_mapping(self) -> None:
        """Test converting tuple to mapping."""
        fields = ("a", "b", "c")
        result = convert_to_mapping(fields)
        assert result == {"a": "a", "b": "b", "c": "c"}

    def test_set_to_mapping(self) -> None:
        """Test converting set to mapping."""
        fields = {"x", "y"}
        result = convert_to_mapping(fields)
        assert "x" in result
        assert "y" in result
        assert result["x"] == "x"
        assert result["y"] == "y"

    def test_empty_collection(self) -> None:
        """Test converting empty collection."""
        result = convert_to_mapping([])
        assert result == {}

    def test_single_element(self) -> None:
        """Test converting single element collection."""
        result = convert_to_mapping(["only"])
        assert result == {"only": "only"}
