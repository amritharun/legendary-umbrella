import unittest
import locale
from enum import Enum
import json
from db.db import QUERY_TYPE
import uuid
from lib.html_gen import (
    get_html_table,
    get_html_visualization,
    get_visual_body,
    error_dialog,
)
from html.parser import HTMLParser


class TestHTMLGenerationFunctions(unittest.TestCase):
    def setUp(self):
        self.sample_data = [
            {
                "cik": "cik1",
                "company": "ACME Corp",
                "cusip": str(uuid.uuid4()),
                "date": "2024-01-01",
                "balance": 1000,
                "value": 1000000.00,
            },
            {
                "cik": "cik2",
                "company": "ACME Two Corp",
                "cusip": str(uuid.uuid4()),
                "date": "2023-01-01",
                "balance": 500,
                "value": 500000.00,
            },
        ]

        # Set locale for currency formatting
        locale.setlocale(locale.LC_ALL, "")

    def test_get_html_table_with_valid_data(self):
        result = get_html_table(self.sample_data, QUERY_TYPE.LATEST)
        self.assertTrue(HTMLValidator().check_valid(result))

        self.assertIn('<div class="table-container">', result)
        self.assertIn("<thead>", result)
        self.assertIn("<tbody>", result)

        self.assertIn("ACME Corp", result)
        self.assertIn("ACME Two Corp", result)

        self.assertIn("</tbody></table></div>", result)
        self.assertEqual(result.count("<tr>"), 3)

    def test_get_html_table_with_empty_data(self):
        result = get_html_table([], QUERY_TYPE.LATEST)
        self.assertTrue(HTMLValidator().check_valid(result))

        self.assertIn('<div class="table-container">', result)
        self.assertIn("<thead>", result)
        self.assertIn("<tbody>", result)
        self.assertIn("</tbody></table></div>", result)

        # should only be the header row
        self.assertEqual(result.count("<tr>"), 1)

    def test_get_html_table_with_special_characters(self):
        special_data = [
            {
                "cik": str(uuid.uuid4()),
                "company": "Acme & Corp",
                "cusip": "cusip<>",
                "date": "2023-01-01",
                "balance": 1000,
                "value": 1000000.00,
            }
        ]

        result = get_html_table(special_data, QUERY_TYPE.LATEST)
        self.assertTrue(HTMLValidator().check_valid(result))

        # special characters in html
        self.assertIn("Acme &amp; Corp", result)
        self.assertIn("cusip&lt;&gt;", result)
        self.assertNotIn("Acme & Corp", result)
        self.assertNotIn("cusip<>", result)

    def test_get_html_visualization_empty_result(self):
        result = get_html_visualization([], QUERY_TYPE.LATEST)
        self.assertTrue(HTMLValidator().check_valid(result))

        result = get_html_visualization([self.sample_data[0]], QUERY_TYPE.LATEST)
        self.assertTrue(HTMLValidator().check_valid(result))

    def test_get_html_visualization_latest_query(self):
        result = get_html_visualization(self.sample_data, QUERY_TYPE.LATEST)
        self.assertTrue(HTMLValidator().check_valid(result))

        self.assertIn('<div class="visualization-container">', result)
        self.assertIn('<div id="chart"></div>', result)
        self.assertIn("</div>", result)

        self.assertIn(json.dumps(self.sample_data), result)
        self.assertIn(json.dumps("latest"), result)
        self.assertIn(json.dumps("Latest Company Filings"), result)
        # should only make 1 chart
        self.assertEqual(result.count("<script>"), 1)

    def test_get_html_visualization_historical_query(self):
        historical_data = self.sample_data + [
            {
                "cik": "cik1",
                "company": "ACME Corp",
                "cusip": str(uuid.uuid4()),
                "date": "2025-01-01",
                "balance": 900,
                "value": 900000.00,
            }
        ]

        result = get_html_visualization(historical_data, QUERY_TYPE.HISTORICAL)
        self.assertTrue(HTMLValidator().check_valid(result))

        self.assertIn('<div class="visualization-container">', result)
        self.assertIn('<div id="chart"></div>', result)
        self.assertIn("</div>", result)

        self.assertIn("ACME Corp", result)
        # Only 1 entry for ACME Two Corp so no visualization
        self.assertNotIn("ACME Two Corp", result)

        self.assertIn("historical", result)

        # should make 1 chart since there's only 1 cik with multiple records
        self.assertEqual(result.count("<script>"), 1)

    def test_get_visual_body(self):
        result = get_visual_body(self.sample_data, QUERY_TYPE.LATEST, "Test Title")
        self.assertTrue(HTMLValidator().check_valid(result))

        # Check structure
        self.assertIn('<div id="chart"></div>', result)
        self.assertIn("<script>", result)
        self.assertIn("document.body.dispatchEvent", result)

        # Check that data is included
        self.assertIn(json.dumps(self.sample_data), result)
        self.assertIn(json.dumps("latest"), result)
        self.assertIn(json.dumps("Test Title"), result)

    def test_error_dialog(self):
        error_message = "Something went wrong!"
        result = error_dialog(error_message)
        self.assertTrue(HTMLValidator().check_valid(result))

        self.assertIn('<table class="table">', result)
        self.assertIn('<div class="alert alert-danger', result)

        self.assertIn("<strong>Error!</strong>", result)
        self.assertIn(error_message, result)

    def test_assert_exceptions(self):
        class FAKE_ENUM(Enum):
            FAKE = 1

        with self.assertRaises(AssertionError):
            get_html_visualization(None, QUERY_TYPE.LATEST)

        with self.assertRaises(AssertionError):
            get_html_table(None, QUERY_TYPE.LATEST)

        with self.assertRaises(AssertionError):
            get_html_visualization(self.sample_data, FAKE_ENUM.FAKE)

        with self.assertRaises(AssertionError):
            get_visual_body(self.sample_data, FAKE_ENUM.FAKE, "Title")


class TestHTMLValidator(unittest.TestCase):
    def test_valid_html(self):
        self.assertTrue(
            HTMLValidator().check_valid(
                "<html><head><title>My Webpage</title></head><body><h1>Hello, world!</h1></body></html>"
            )
        )
        self.assertTrue(HTMLValidator().check_valid("<head></head><body></body>"))
        self.assertTrue(HTMLValidator().check_valid("<tr><td>Test</td></tr>"))
        self.assertTrue(HTMLValidator().check_valid("<div><span></span></div>"))

    def test_invalid_html(self):
        self.assertFalse(
            HTMLValidator().check_valid(
                "<html><head><title>My Webpage</title></head><body><h1>Hello, world!</h1></body>"
            )
        )
        self.assertFalse(HTMLValidator().check_valid("<head><body></body>"))
        self.assertFalse(HTMLValidator().check_valid("<tr><td>Test</tr>"))
        self.assertFalse(HTMLValidator().check_valid("<div><span></div>"))


class HTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.is_valid = True
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)

    def handle_endtag(self, tag):
        if self.tags:
            last_tag = self.tags.pop()
            if tag != last_tag:
                self.is_valid = False

    def handle_data(self, data):
        pass

    def check_valid(self, html_string) -> bool:
        self.feed(html_string)
        if self.tags:
            self.is_valid = False
        return self.is_valid


if __name__ == "__main__":
    unittest.main()
