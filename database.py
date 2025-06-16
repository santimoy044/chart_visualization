import mysql.connector
from mysql.connector import Error
import os, logging
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT', 3306))
}


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Connect to DB
def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            logger.info("Connected to database")
            return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        return None


# Close DB connection
def close_db_connection(connection):
    if connection and connection.is_connected():
        connection.close()
        logger.info("Database connection closed")


# Query execution
def execute_query(query, params=None):
    db_connection = get_db_connection()

    if not db_connection:
        return None, "Database connection failed"

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        result = cursor.fetchall()
        return result, None

    except Error as e:
        logger.error(f"MySQL query error: {e}")
        return None, str(e)
    finally:
        if db_connection.is_connected():
            cursor.close()
            db_connection.close()
