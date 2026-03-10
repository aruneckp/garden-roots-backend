"""
Utility script to run oracle_schema.sql and seed_data.sql directly via python-oracledb.
Usage: python run_sql.py
"""
import oracledb
import os
import sys
import re

DB_USER = os.getenv("DB_USER", "system")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Oracle123")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "1521"))
DB_SERVICE = os.getenv("DB_SERVICE", "XEPDB1")


def split_sql(sql_text: str):
    """
    Split a SQL file into individual statements, stripping comments.
    Handles Oracle-style semicolon terminators.
    """
    # Remove single-line comments
    sql_text = re.sub(r"--[^\n]*", "", sql_text)
    # Split on semicolons
    statements = [s.strip() for s in sql_text.split(";")]
    # Filter empty and COMMIT (handled manually)
    return [s for s in statements if s and s.upper() != "COMMIT"]


def run_file(cursor, filepath: str, ignore_errors: bool = False):
    print(f"\n{'='*60}")
    print(f"Running: {filepath}")
    print(f"{'='*60}")
    with open(filepath, "r") as f:
        sql_text = f.read()

    statements = split_sql(sql_text)
    success = 0
    skipped = 0

    for stmt in statements:
        preview = stmt[:80].replace("\n", " ")
        try:
            cursor.execute(stmt)
            print(f"  OK  → {preview}…")
            success += 1
        except oracledb.DatabaseError as e:
            error_obj = e.args[0]
            # ORA-00955: name is already used by an existing object (table/index exists)
            # ORA-02260: only one primary key allowed
            # ORA-01408: such column list already indexed
            if ignore_errors or error_obj.code in (955, 2260, 1408, 2275):
                print(f"  SKIP (already exists) → {preview}…")
                skipped += 1
            else:
                print(f"  ERROR → {preview}…")
                print(f"         {e}")
                if not ignore_errors:
                    raise

    print(f"\nDone: {success} OK, {skipped} skipped")
    return success


def main():
    print("Connecting to Oracle …")
    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"
    try:
        conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)
        print(f"Connected to Oracle {conn.version} at {dsn}")
    except oracledb.DatabaseError as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))

    with conn.cursor() as cursor:
        # 1. Schema (ignore "already exists" errors so re-runs are safe)
        run_file(cursor, os.path.join(script_dir, "oracle_schema.sql"), ignore_errors=True)
        conn.commit()

        # 2. Seed data (ignore duplicate inserts)
        run_file(cursor, os.path.join(script_dir, "seed_data.sql"), ignore_errors=True)
        conn.commit()

    conn.close()
    print("\nAll scripts completed successfully.")


if __name__ == "__main__":
    main()
