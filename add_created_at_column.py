"""Run this script to add `created_at` DATETIME column to the `posts` table.

Usage (PowerShell):
    python "d:\\Python\\Personal Blog\\my_blog\\add_created_at_column.py"

It will attempt to run an ALTER TABLE and handle the case where the column already exists.
"""
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
import sys

try:
    # import engine from your project's database module
    from database import engine
except Exception as e:
    print('Failed to import engine from database.py:', e)
    sys.exit(1)


ALTER_SQL = "ALTER TABLE posts ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;"


def main():
    print('Connecting to database using engine...')
    try:
        with engine.connect() as conn:
            print('Executing ALTER TABLE to add created_at...')
            try:
                conn.execute(text(ALTER_SQL))
                print('ALTER TABLE executed successfully. Column created_at should now exist.')
            except (OperationalError, ProgrammingError) as err:
                # MySQL duplicate column error is typically errno 1060. Check message.
                msg = str(err)
                if 'Duplicate column name' in msg or '1060' in msg:
                    print('Column already exists. No changes were made.')
                else:
                    print('Database error while adding column:')
                    print(msg)
                    print('\nYou can inspect the table with: SHOW COLUMNS FROM posts;')
                    sys.exit(2)
    except Exception as e:
        print('Unexpected error when connecting/executing:', e)
        sys.exit(3)


if __name__ == '__main__':
    main()

