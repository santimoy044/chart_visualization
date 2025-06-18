import mysql.connector
from mysql.connector import Error
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DB configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'root'),
    'database': os.getenv('DB_NAME', 'employeeinfo'),
    'port': int(os.getenv('DB_PORT', 3306))
}

# Get DB connection
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