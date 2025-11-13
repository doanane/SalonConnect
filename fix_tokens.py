# fix_tokens.py - Place this in your project root
import os
import sys

# Add the current directory to Python path
sys.path.append(os.getcwd())

from app.database import engine
from sqlalchemy import text

def fix_token_columns():
    """Fix token columns by altering them to TEXT type"""
    
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
        return True
    except Exception as e:
        print(f"Error updating token columns: {str(e)}")
        return False

if __name__ == "__main__":
    fix_token_columns()