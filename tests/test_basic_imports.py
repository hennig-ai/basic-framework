"""
Basic import test to ensure all modules can be imported correctly.
"""

import unittest


class TestBasicImports(unittest.TestCase):
    """Test that all basic_framework modules can be imported."""
    
    def test_basic_module_imports(self):
        """Test importing basic utilities."""
        try:
            from basic_framework.utils.basic_utils import (
                get_format_now_stamp,
                is_hyperlink,
            )
            from basic_framework.utils.filename_utils import (
                get_name_from_full_reference,
                remove_file_postfix,
            )
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import utils modules: {e}")
    
    def test_condition_imports(self):
        """Test importing condition classes."""
        try:
            from basic_framework.conditions.condition import Condition
            from basic_framework.conditions.condition_and import ConditionAnd
            from basic_framework.conditions.condition_equals import ConditionEquals
            from basic_framework.conditions.condition_not import ConditionNot
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import condition modules: {e}")
    
    
    def test_proc_frame_imports(self):
        """Test importing process framework."""
        try:
            from basic_framework.proc_frame import (
                proc_frame_start,
                log_msg,
                log_and_raise
            )
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import proc_frame: {e}")
    
    def test_config_imports(self):
        """Test importing configuration handling."""
        try:
            from basic_framework.ini_config_file import IniConfigFile
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import ini_config_file: {e}")
    
    def test_package_level_imports(self):
        """Test importing from package level."""
        try:
            from basic_framework import (
                IniConfigFile,
                log_msg,
                get_format_now_stamp,
                ConditionEquals
            )
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import from package level: {e}")


class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality of key modules."""
    
    def test_timestamp_generation(self):
        """Test timestamp generation."""
        from basic_framework import get_format_now_stamp

        timestamp = get_format_now_stamp()
        self.assertIsInstance(timestamp, str)
        self.assertGreater(len(timestamp), 10)

        timestamp_with_seconds = get_format_now_stamp(with_seconds=True)
        self.assertGreater(len(timestamp_with_seconds), len(timestamp))
    
    def test_hyperlink_detection(self):
        """Test hyperlink detection."""
        from basic_framework import is_hyperlink

        self.assertTrue(is_hyperlink("https://example.com"))
        self.assertTrue(is_hyperlink("http://test.org"))
        self.assertFalse(is_hyperlink("C:\\path\\file.txt"))
        self.assertFalse(is_hyperlink("simple_text"))
    
    def test_filename_extraction(self):
        """Test filename extraction utilities."""
        from basic_framework import (
            get_name_from_full_reference,
            remove_file_postfix,
        )

        # Windows path
        name = get_name_from_full_reference("C:\\path\\to\\file.xlsx")
        self.assertEqual(name, "file")

        # URL
        name = get_name_from_full_reference("https://example.com/file.pdf")
        self.assertEqual(name, "file")

        # File extension removal
        name_without_ext = remove_file_postfix("document.xlsx")
        self.assertEqual(name_without_ext, "document")


if __name__ == '__main__':
    unittest.main()