import polars as pl
import os
import uuid
import random
from faker import Faker
import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
import sqlite3
import requests
import json

fake = Faker()

db_path = "database.db"
if os.path.exists(db_path):
    os.remove(db_path)

data = []
num_companies = 100
for _ in range(num_companies):
    cik = str(uuid.uuid4())
    company = fake.company()
    num_records = random.randint(1, 10)
    balance_mu = random.randint(300, 500)
    balance_sigma = 100
    value_mu = random.randint(2_500_000, 5_000_000)
    value_sigma = 800_000

    current_date = datetime.datetime(2024, 1, 1)

    for _ in range(num_records):
        current_date = current_date + relativedelta(months=1)
        cusip = str(uuid.uuid4())
        balance = round(np.random.normal(balance_mu, balance_sigma))
        value = round(np.random.normal(value_mu, value_sigma), 2)
        data.append(
            {
                "cik": cik,
                "company": company,
                "cusip": cusip,
                "date": current_date,
                "balance": balance,
                "value": value,
            }
        )
df = pl.DataFrame(data)
print(df.filter(df["value"] < 0))
assert df.n_unique("cik") == num_companies
assert (df["value"] > 0).all()
assert (df["balance"] > 0).all()

print(df)


df.write_database(
    "n_port_historical",
    connection="sqlite:///database.db",
    if_table_exists="replace",
)

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute(
    """
CREATE VIEW n_port_latest as
SELECT t1.cik, t1.company, t1.cusip, t1.date, t1.balance, t1.value
FROM n_port_historical t1
INNER JOIN (
    SELECT cik, MAX(date) as max_date
    FROM n_port_historical
    GROUP BY cik
) t2 ON t1.cik = t2.cik AND t1.date = t2.max_date
ORDER BY t1.cik
"""
)

conn.commit()
conn.close()


df = pl.read_csv("REGISTRANT.tsv", separator="\t", infer_schema_length=0)
df = df.filter(df["CIK"].is_not_null()).with_columns(pl.col("CIK").alias("cik")).select("cik")
print(df)
df.write_database(
    "valid_cik",
    connection="sqlite:///database.db",
    if_table_exists="replace",
)