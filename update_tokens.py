# update_tokens.py - Place this in your project root folder (salon_connect_fastapi/)
import os
import sys

# Add the current directory to Python path
sys.path.append(os.getcwd())

from app.database import engine
from sqlalchemy import text

def update_token_columns():
    """Update token columns from VARCHAR(255) to TEXT"""
    
    # SQL statements to alter the columns
    alter_statements = [
        "ALTER TABLE password_resets ALTER COLUMN token TYPE TEXT",
        "ALTER TABLE pending_users ALTER COLUMN verification_token TYPE TEXT"
    ]
    
    try:
        with engine.connect() as connection:
            for statement in alter_statements:
                print(f"Executing: {statement}")
                connection.execute(text(statement))
            connection.commit()
        print(" Successfully updated token columns to TEXT")
    except Exception as e:
        print(f"Error updating token columns: {str(e)}")

if __name__ == "__main__":
    update_token_columns()