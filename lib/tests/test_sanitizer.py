import unittest
from lib.sanitizer import sanitize_string


class TestSanitizeString(unittest.TestCase):

    def test_none_equivalents(self):
        self.assertEqual(sanitize_string(""), "")
        self.assertEqual(sanitize_string(None), "")

    def test_basic_sanitization(self):
        self.assertEqual(sanitize_string("Hello, World! 123"), "Hello, World 123")
        self.assertEqual(
            sanitize_string("testcase@legendary_umbrella.com"),
            "testcaselegendaryumbrellacom",
        )
        self.assertEqual(sanitize_string("a b c!@#$%^&*()"), "a b c")

    def test_whitespace_trimming(self):
        self.assertEqual(sanitize_string("  abc  "), "abc")
        self.assertEqual(sanitize_string("\n\tabc\n\t"), "abc")

    def test_length_truncation(self):
        long_string = "abcdefghij" * 10
        self.assertEqual(len(sanitize_string(long_string)), 50)
        self.assertEqual(sanitize_string(long_string), "abcdefghij" * 5)

        exact_50 = "x" * 50
        self.assertEqual(sanitize_string(exact_50), exact_50)

        just_over_50 = "y" * 51
        self.assertEqual(sanitize_string(just_over_50), "y" * 50)

    def test_mixed_character_types(self):
        mixed_string = "a-b-c-" + "!@#$%^&*()" + "1-2-3-" * 20
        sanitized = sanitize_string(mixed_string)
        self.assertTrue(all(c.isalnum() or c in {"-", " ", ","} for c in sanitized))
        self.assertLessEqual(len(sanitized), 50)


if __name__ == "__main__":
    unittest.main()
