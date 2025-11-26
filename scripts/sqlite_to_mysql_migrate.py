#!/usr/bin/env python3
"""Migrate SQLite DB file to a MySQL database using SQLAlchemy.

Usage:
  python scripts/sqlite_to_mysql_migrate.py --sqlite ./data/data.db --mysql "mysql+pymysql://user:pass@host:3306/dbname"

Notes:
 - Install requirements: `pip install sqlalchemy pymysql python-dotenv`
 - Stop the `mcp` service while migrating to avoid concurrent writes.
 - Always back up the SQLite file before running.
"""
import argparse
import sys
from sqlalchemy import create_engine, MetaData, Table, select
from sqlalchemy.orm import sessionmaker


def copy_table(sqlite_engine, mysql_engine, table_name):
    s_meta = MetaData()
    s_meta.reflect(bind=sqlite_engine, only=[table_name])
    table = s_meta.tables.get(table_name)
    if table is None:
        print(f"Table {table_name} not found in sqlite")
        return

    # Ensure table exists in MySQL
    t_meta = MetaData()
    t_meta.reflect(bind=mysql_engine)
    if table_name not in t_meta.tables:
        # create table in mysql using sqlite table's schema
        table.schema = None
        table.metadata.create_all(bind=mysql_engine, tables=[table])
        print(f"Created table {table_name} in MySQL")

    # Copy rows
    src_conn = sqlite_engine.connect()
    dst_conn = mysql_engine.connect()
    sel = select(table)
    results = src_conn.execute(sel)
    rows = [dict(r) for r in results]
    if not rows:
        print(f"No rows in {table_name}")
        return

    # Insert in batches
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        try:
            dst_conn.execute(table.insert(), batch)
        except Exception as e:
            print(f"Error inserting batch into {table_name}: {e}")
            raise
    print(f"Copied {len(rows)} rows into {table_name}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sqlite', required=True, help='Path to sqlite file, e.g. ./data/data.db')
    p.add_argument('--mysql', required=True, help='SQLAlchemy MySQL URL, e.g. mysql+pymysql://user:pass@host:3306/db')
    args = p.parse_args()

    sqlite_url = f"sqlite:///{args.sqlite}"
    mysql_url = args.mysql

    print(f"Connecting to sqlite: {sqlite_url}")
    print(f"Connecting to mysql: {mysql_url}")

    s_engine = create_engine(sqlite_url)
    d_engine = create_engine(mysql_url)

    # Reflect sqlite metadata and copy tables in order
    s_meta = MetaData()
    s_meta.reflect(bind=s_engine)
    table_names = list(s_meta.tables.keys())
    print(f"Found tables: {table_names}")

    # Simple copy: create tables if missing and copy rows
    for tn in table_names:
        print(f"Copying table {tn}...")
        copy_table(s_engine, d_engine, tn)

    print("Migration complete")


if __name__ == '__main__':
    main()
