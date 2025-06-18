from flask import Blueprint, make_response, jsonify, request
from mysql.connector import Error
from datetime import datetime
import re, csv, io, logging
from database import get_db_connection, close_db_connection

# Create a Flask Blueprint named 'export' without URL prefix
export_bp = Blueprint('export', __name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Execute SELECT/INSERT/UPDATE queries
def execute_query(query, params=None):
    db_connection = get_db_connection()
    if not db_connection:
        logger.error("Failed to get database connection")
        return None, "Database connection failed"

    cursor = None
    try:
        # Create cursor with buffered=True to fetch all results immediately
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        cursor.execute(query, params or ())
        
        # For SELECT queries and SHOW commands
        query_lower = query.strip().lower()
        if query_lower.startswith(('select', 'show', 'describe', 'explain')):
            result = cursor.fetchall()
        else:
            result = cursor.rowcount
            if not db_connection.autocommit:
                db_connection.commit()

        return result, None

    except Error as e:
        logger.error(f"MySQL query error: {e}")
        return None, str(e)
    except Exception as e:
        logger.error(f"General error in execute_query: {e}")
        return None, str(e)

    finally:
        # Ensure cursor is properly closed
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                logger.warning(f"Error closing cursor: {e}")
        if db_connection and db_connection.is_connected():
            close_db_connection(db_connection)


# Check if table has any date/datetime columns for filtering
def check_date_columns(table_name):
    try:
        # Query to get column information (works for MySQL/MariaDB)
        query = """
        SELECT COLUMN_NAME, DATA_TYPE 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = %s AND TABLE_SCHEMA = DATABASE()
        """
        
        columns, error = execute_query(query, (table_name,))
        if error:
            logger.error(f"Error getting columns for {table_name}: {error}")
            return [], error
        
        if not columns:
            logger.warning(f"No columns found for table {table_name}")
            return [], "Table not found or no columns"
        
        # Filter date/datetime columns
        date_types = ['date', 'datetime', 'timestamp', 'time']
        date_columns = []
        
        for col in columns:
            col_name = col['COLUMN_NAME']
            col_type = col['DATA_TYPE'].lower()
            
            if any(date_type in col_type for date_type in date_types):
                date_columns.append(col_name)
        
        logger.debug(f"Found date columns for {table_name}: {date_columns}")
        return date_columns, None
        
    except Exception as e:
        logger.error(f"Exception in check_date_columns: {e}")
        return [], str(e)


# Get all tables in the database
@export_bp.route('/api/database/tables', methods=['GET'])
def get_all_tables():
    """
    Get all table names from the current database
    Returns: JSON array of table names
    """
    try:
        query = "SHOW TABLES"
        tables, error = execute_query(query)
        
        if error:
            logger.error(f"Error fetching tables: {error}")
            return jsonify({'error': error}), 500
        
        if not tables:
            logger.warning("No tables found in database")
            return jsonify([]), 200
        
        # Extract table names from the result
        table_names = []
        for table in tables:
            # Get the first (and only) value from each row
            table_name = list(table.values())[0] if table else None
            if table_name:
                table_names.append(table_name)
        
        logger.info(f"Found {len(table_names)} tables: {table_names}")
        return jsonify(table_names), 200
        
    except Exception as e:
        logger.error(f"Exception in get_all_tables: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


# Get tables that have date/datetime columns for filtering
@export_bp.route('/api/database/filterable-tables', methods=['GET'])
def get_filterable_tables():
    """
    Get all tables that have date/datetime columns available for filtering
    Returns: JSON array of objects with table_name and date_columns
    """
    try:
        logger.info("Fetching filterable tables from database")
        
        # First get all tables
        query = "SHOW TABLES"
        tables, error = execute_query(query)
        
        if error:
            logger.error(f"Error fetching tables: {error}")
            return jsonify({'error': error}), 500
        
        if not tables:
            logger.warning("No tables found in database")
            return jsonify([]), 200
        
        filterable_tables = []
        
        # Check each table for date columns
        for table in tables:
            table_name = list(table.values())[0]
            logger.debug(f"Checking date columns for table: {table_name}")
            
            date_columns, error = check_date_columns(table_name)
            
            if error:
                logger.warning(f"Error checking date columns for {table_name}: {error}")
                continue
            
            # Only include tables that have date columns
            if date_columns:
                filterable_tables.append({
                    'table_name': table_name,
                    'date_columns': date_columns
                })
                logger.debug(f"Table {table_name} has date columns: {date_columns}")
            else:
                logger.debug(f"Table {table_name} has no date columns")
        
        logger.info(f"Found {len(filterable_tables)} filterable tables")
        return jsonify(filterable_tables), 200
        
    except Exception as e:
        logger.error(f"Exception in get_filterable_tables: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Date range wise data export to CSV
@export_bp.route('/api/data/export/csv/<table_name>/by-date-range', methods=['GET'])
def export_table_by_date_range_csv(table_name):
    """
    Export table data as CSV filtered by date range
    Query parameters: start_date, end_date, date_column
    """
    # Validate table_name to prevent SQL injection
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        return jsonify({'error': 'Invalid table name'}), 400

    # Get required parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    date_column = request.args.get('date_column')
    
    # Validate required parameters
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    
    if not date_column:
        return jsonify({'error': 'date_column parameter is required'}), 400

    # Check if table has any date columns for filtering
    available_date_columns, check_error = check_date_columns(table_name)
    if check_error:
        return jsonify({'error': f'Unable to check table structure: {check_error}'}), 500
    
    # Handle case where table has no date columns
    if not available_date_columns:
        return jsonify({
            'error': f'Table "{table_name}" has no date/datetime columns available for filtering',
            'message': 'This table cannot be filtered by date range as it contains no date or datetime columns'
        }), 400

    # Validate date_column against actual table columns
    if date_column not in available_date_columns:
        return jsonify({
            'error': f'Column "{date_column}" is not a valid date/datetime column in table "{table_name}"',
            'available_columns': available_date_columns
        }), 400
    
    logger.info(f"Received date range export request for {table_name} | {date_column} from {start_date} to {end_date}")
    
    # Handle date format - if same date, search full day
    if start_date == end_date:
        # If only date provided (no time), search entire day
        if len(start_date) == 10:  # YYYY-MM-DD format
            start_datetime = f"{start_date} 00:00:00"
            end_datetime = f"{end_date} 23:59:59"
        else:
            start_datetime = start_date
            end_datetime = end_date
    else:
        # Different dates
        if len(start_date) == 10:
            start_datetime = f"{start_date} 00:00:00"
        else:
            start_datetime = start_date
            
        if len(end_date) == 10:
            end_datetime = f"{end_date} 23:59:59"
        else:
            end_datetime = end_date
    
    query = f"SELECT * FROM {table_name} WHERE {date_column} BETWEEN %s AND %s ORDER BY {date_column}"
    logger.debug(f"Query: {query}")
    
    data, error = execute_query(query, (start_datetime, end_datetime))
    
    if error:
        logger.error(f"Database error: {error}")
        return jsonify({'error': error}), 500
    
    if not data:
        logger.warning(f"No data found in {table_name} between {start_datetime} and {end_datetime}")
        return jsonify({'error': 'No data found for the specified date range'}), 404
    
    logger.info(f"Exported {len(data)} records from {table_name} between {start_datetime} and {end_datetime}")
    
    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={table_name}_{date_column}_{start_date}_to_{end_date}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response


# Export full table to CSV
@export_bp.route('/api/data/export/csv/<table_name>', methods=['GET'])
def export_full_table_csv(table_name):
    """
    Export complete table data as CSV file
    """
    # Validate table_name to prevent SQL injection
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        return jsonify({'error': 'Invalid table name'}), 400
    
    logger.info(f"Exporting full table: {table_name}")
    
    query = f"SELECT * FROM {table_name}"
    data, error = execute_query(query)
    
    if error:
        logger.error(f"Error exporting table {table_name}: {error}")
        return jsonify({'error': error}), 500
    
    if not data:
        logger.warning(f"No data found in table {table_name}")
        return jsonify({'error': 'No data found'}), 404
    
    logger.info(f"Successfully exported {len(data)} records from {table_name}")
    
    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={table_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response


# Export full table to JSON
@export_bp.route('/api/data/export/json/<table_name>', methods=['GET'])
def export_full_table_json(table_name):
    """
    Export complete table data as JSON response
    Returns: JSON object with table metadata and data array
    """
    import base64
    
    # Validate table_name to prevent SQL injection
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        return jsonify({'error': 'Invalid table name'}), 400
    
    logger.info(f"Exporting full table as JSON: {table_name}")
    
    query = f"SELECT * FROM {table_name}"
    data, error = execute_query(query)
    
    if error:
        logger.error(f"Error exporting table {table_name}: {error}")
        return jsonify({'error': error}), 500
    
    if not data:
        logger.warning(f"No data found in table {table_name}")
        return jsonify({'error': 'No data found'}), 404
    
    # Handle binary data (BLOB fields) by converting to base64
    processed_data = []
    for row in data:
        processed_row = {}
        for key, value in row.items():
            if isinstance(value, bytes):
                # Convert binary data to base64 string
                processed_row[key] = base64.b64encode(value).decode('utf-8')
                processed_row[f"{key}_type"] = "base64_encoded"
            else:
                processed_row[key] = value
        processed_data.append(processed_row)
    
    logger.info(f"Successfully exported {len(processed_data)} records from {table_name} as JSON")
    
    # Return the data as JSON with proper response headers
    response = jsonify({
        'table_name': table_name,
        'record_count': len(processed_data),
        'export_timestamp': datetime.now().isoformat(),
        'data': processed_data
    })
    
    # Set response headers
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    
    return response


# Export table data by date range as JSON
@export_bp.route('/api/data/export/json/<table_name>/by-date-range', methods=['GET'])
def export_table_by_date_range_json(table_name):
    """
    Export table data as JSON filtered by date range
    Query parameters: start_date, end_date, date_column
    """
    import base64
    
    # Validate table_name to prevent SQL injection
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        return jsonify({'error': 'Invalid table name'}), 400

    # Get required parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    date_column = request.args.get('date_column')
    
    # Validate required parameters
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    
    if not date_column:
        return jsonify({'error': 'date_column parameter is required'}), 400

    # Check if table has any date columns for filtering
    available_date_columns, check_error = check_date_columns(table_name)
    if check_error:
        return jsonify({'error': f'Unable to check table structure: {check_error}'}), 500
    
    # Handle case where table has no date columns
    if not available_date_columns:
        return jsonify({
            'error': f'Table "{table_name}" has no date/datetime columns available for filtering',
            'message': 'This table cannot be filtered by date range as it contains no date or datetime columns'
        }), 400

    # Validate date_column against actual table columns
    if date_column not in available_date_columns:
        return jsonify({
            'error': f'Column "{date_column}" is not a valid date/datetime column in table "{table_name}"',
            'available_columns': available_date_columns
        }), 400
    
    logger.info(f"Received JSON date range export request for {table_name} | {date_column} from {start_date} to {end_date}")
    
    # Handle date format - if same date, search full day
    if start_date == end_date:
        # If only date provided (no time), search entire day
        if len(start_date) == 10:  # YYYY-MM-DD format
            start_datetime = f"{start_date} 00:00:00"
            end_datetime = f"{end_date} 23:59:59"
        else:
            start_datetime = start_date
            end_datetime = end_date
    else:
        # Different dates
        if len(start_date) == 10:
            start_datetime = f"{start_date} 00:00:00"
        else:
            start_datetime = start_date
            
        if len(end_date) == 10:
            end_datetime = f"{end_date} 23:59:59"
        else:
            end_datetime = end_date
    
    query = f"SELECT * FROM {table_name} WHERE {date_column} BETWEEN %s AND %s ORDER BY {date_column}"
    logger.debug(f"Query: {query}")
    
    data, error = execute_query(query, (start_datetime, end_datetime))
    
    if error:
        logger.error(f"Database error: {error}")
        return jsonify({'error': error}), 500
    
    if not data:
        logger.warning(f"No data found in {table_name} between {start_datetime} and {end_datetime}")
        return jsonify({'error': 'No data found for the specified date range'}), 404
    
    # Handle binary data (BLOB fields) by converting to base64  
    processed_data = []
    for row in data:
        processed_row = {}
        for key, value in row.items():
            if isinstance(value, bytes):
                # Convert binary data to base64 string
                processed_row[key] = base64.b64encode(value).decode('utf-8')
                processed_row[f"{key}_type"] = "base64_encoded"
            else:
                processed_row[key] = value
        processed_data.append(processed_row)
    
    logger.info(f"Exported {len(processed_data)} records from {table_name} between {start_datetime} and {end_datetime}")
    
    # Return the data as JSON with proper response headers
    response = jsonify({
        'table_name': table_name,
        'date_column': date_column,
        'date_range': {
            'start': start_datetime,
            'end': end_datetime
        },
        'record_count': len(processed_data),
        'export_timestamp': datetime.now().isoformat(),
        'data': processed_data
    })
    
    # Set response headers
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    
    return response