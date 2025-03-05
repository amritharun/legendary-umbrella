from enum import Enum
import re
import sqlite3
from .scraper import SECNPortScraper
from .sec_api import SecApiSession


class QUERY_TYPE(Enum):
    LATEST = 1
    HISTORICAL = 2
    REAL = 3

scraper = SECNPortScraper()
sec_api = SecApiSession()

class DatabaseConnection:
    _instance = None
    _connection = None
    _db_name = "db/database.db"

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._connection = None
        return cls._instance

    def dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def get_connection(self):
        if self._connection is None:
            self._connection = sqlite3.connect(self._db_name)
            self._connection.row_factory = self.dict_factory
        return self._connection

    def close_connection(self):
        if self._connection:
            self._connection.close()
            self._connection = None

    def __del__(self):
        self.close_connection()

    def __enter__(self):
        return self.get_connection()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()


def get_search(search_term: str, query_type: QUERY_TYPE) -> tuple | None:
    if QUERY_TYPE.HISTORICAL == query_type:
        return query_table(search_term, "n_port_historical")
    elif QUERY_TYPE.LATEST == query_type:
        return query_table(search_term, "n_port_latest", "value")
    elif QUERY_TYPE.REAL == query_type:
        ciks =query_cik(search_term)
        if not ciks:
            return None
        return request_cik_data(ciks)
    else:
        return None

def request_cik_data(ciks: list) -> list:
    hits = []
    for cik in ciks[:5]:
        result = sec_api.get_recent_filing(cik["cik"])
        if result:
            hits.extend(result)
    return hits

def query_cik(search_term: str) -> tuple | None:
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT DISTINCT cik
            FROM valid_cik
            WHERE UPPER(cik) LIKE UPPER('%{search_term}%')
            """
        )
        return cursor.fetchall()
    return None

def query_table(search_term: str, table: str, order_by: str = "date") -> tuple | None:
    # Limits to the first 50 distinct cik matches to search_term
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            WITH companies AS (
            SELECT cik, cusip, company, date, balance, value 
            FROM {table}
            WHERE UPPER(cik) LIKE UPPER('%{search_term}%')
            OR UPPER(company) LIKE UPPER('%{search_term}%')
            )
            SELECT c.cik as cik,c.cusip as cusip,c.company as company, strftime('%m/%d/%Y', c.date) as date, c.balance as balance, c.value as value
            FROM companies as c
            INNER JOIN (SELECT DISTINCT cik FROM companies LIMIT 20) AS cik_table
            ON c.cik = cik_table.cik
            ORDER BY {order_by} ASC
            """
        )
        return cursor.fetchall()
    return None
