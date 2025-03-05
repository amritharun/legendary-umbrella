from enum import Enum
import unittest
import tempfile
import sqlite3
import os
from unittest.mock import patch

from db.db import QUERY_TYPE, DatabaseConnection, get_search


class TestDatabaseFunctions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_db_fd, cls.test_db_path = tempfile.mkstemp()

        conn = sqlite3.connect(cls.test_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE n_port_latest (
                cik TEXT,
                cusip TEXT,
                company TEXT,
                date TEXT,
                balance INT,
                value REAL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE n_port_historical (
                cik TEXT,
                cusip TEXT,
                company TEXT,
                date TEXT,
                balance INT,
                value REAL
            )
        """
        )

        latest_data = [
            ("1234567890", "ABC123", "Acme Corp", "2023-01-15", 1000, 5000.25),
            ("9876543210", "XYZ789", "Sample Corp", "2023-01-20", 2500, 10000.00),
            ("1234567890", "DEF456", "Acme Corp", "2023-01-25", 1500, 7500.50),
        ]
        cursor.executemany(
            "INSERT INTO n_port_latest VALUES (?, ?, ?, ?, ?, ?)", latest_data
        )

        historical_data = [
            ("1234567890", "ABC123", "Acme Corp", "2022-01-15", 900, 4500.00),
            ("9876543210", "XYZ789", "Sample Corp", "2022-01-20", 2400, 9500.00),
            ("1234567890", "DEF456", "Acme Corp", "2022-01-25", 1400, 7000.00),
            ("5555555555", "GHI789", "Acme Two Corp", "2022-02-10", 3000, 15000.00),
        ]
        cursor.executemany(
            "INSERT INTO n_port_historical VALUES (?, ?, ?, ?, ?, ?)", historical_data
        )

        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        os.close(cls.test_db_fd)
        os.unlink(cls.test_db_path)

    def setUp(self):
        self.db_patcher = patch.object(
            DatabaseConnection,
            "_db_name",
            new_callable=lambda: self.test_db_path,
        )
        self.db_patcher.start()

        DatabaseConnection._instance = None
        DatabaseConnection._connection = None

    def tearDown(self):
        self.db_patcher.stop()

    def test_singleton_pattern(self):
        db1 = DatabaseConnection()
        db2 = DatabaseConnection()

        self.assertIs(db1, db2)
        self.assertEqual(db1._db_name, self.test_db_path)

    def test_context_manager(self):
        with DatabaseConnection() as conn:
            self.assertIsNotNone(conn)

            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            table_names = [table["name"] for table in tables]
            self.assertIn("n_port_latest", table_names)
            self.assertIn("n_port_historical", table_names)

        self.assertIsNone(DatabaseConnection()._connection)

    def test_query_latest_data(self):
        results = get_search("Acme Corp", QUERY_TYPE.LATEST)

        self.assertIsNotNone(results)
        self.assertEqual(len(results), 2)

        for result in results:
            self.assertEqual(result["cik"], "1234567890")
            self.assertEqual(result["company"], "Acme Corp")

    def test_query_historical_data(self):
        results = get_search("5555", QUERY_TYPE.HISTORICAL)

        self.assertIsNotNone(results)
        self.assertEqual(len(results), 1)

        self.assertEqual(results[0]["cik"], "5555555555")
        self.assertEqual(results[0]["company"], "Acme Two Corp")

    def test_invalid_query_type(self):
        """Test behavior with an invalid query type."""

        class MockEnum(Enum):
            INVALID = 3

        result = get_search("Test", MockEnum.INVALID)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
