import sqlite3
from var.config import DatabaseConfig

config = DatabaseConfig.config

class DatabaseManager:
    def __init__(self):
        """Initialize the DatabaseManager with a connection string from DATABASE_CONFIG."""
        self.validate_config()
        self.connection_string = config['connection_string']

    # Errors & Debug
    def validate_config(self):
        """Validates the DATABASE_CONFIG."""
        if 'connection_string' not in config:
            raise ValueError("Database configuration must include a connection string.")

    def create_connection(self):
        """Create and return a new database connection."""
        try:
            return sqlite3.connect(self.connection_string)
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            raise

    #Database Functions
    def table_exists(self, table_name):
        """
        Check if a table exists in the database.

        Args:
            table_name (str): The name of the table to check.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        with sqlite3.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
            return cursor.fetchone() is not None

    def create_table(self, table_name, columns):
        """
        Create a new table in the database.

        Args:
            table_name (str): The name of the table to create.
            columns (str): SQL string defining the columns and types.
        """
        with self.create_connection() as conn:
            try:
                conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")
            except sqlite3.Error as e:
                print(f"Error creating table {table_name}: {e}")
                raise

    def delete_table(self, table_name):
        """
        Delete a table from the database.

        Args:
            table_name (str): The name of the table to delete.
        """
        with self.create_connection() as conn:
            try:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            except sqlite3.Error as e:
                print(f"Error deleting table {table_name}: {e}")
                raise