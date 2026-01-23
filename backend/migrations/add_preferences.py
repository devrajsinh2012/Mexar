
from core.database import engine, Base
from sqlalchemy import text, inspect

def run_migration():
    print("Running migration: Add preferences to users table...")
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'preferences' not in columns:
        try:
            with engine.connect() as conn:
                # Add JSON column for preferences
                conn.execute(text("ALTER TABLE users ADD COLUMN preferences JSON DEFAULT '{}'"))
                conn.commit()
            print("✅ Successfully added 'preferences' column to 'users' table.")
        except Exception as e:
            print(f"❌ Error adding column: {e}")
    else:
        print("ℹ️ Column 'preferences' already exists in 'users' table.")

if __name__ == "__main__":
    run_migration()
