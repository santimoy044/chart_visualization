from flask import Blueprint, make_response, jsonify, request
from datetime import datetime
import re, csv, io, logging
from database import execute_query


# Create a Flask Blueprint named 'export' for organizing export-related routes.
# All routes in this blueprint will have '/export' as their URL prefix.
export_bp = Blueprint('export', __name__, url_prefix='/export')


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
            return [], error
        
        if not columns:
            return [], "Table not found or no columns"
        
        # Filter date/datetime columns
        date_types = ['date', 'datetime', 'timestamp', 'time']
        date_columns = []
        
        for col in columns:
            col_name = col['COLUMN_NAME']
            col_type = col['DATA_TYPE'].lower()
            
            if any(date_type in col_type for date_type in date_types):
                date_columns.append(col_name)
        
        return date_columns, None
        
    except Exception as e:
        return [], str(e)


@export_bp.route('/csv/<table_name>/daterange', methods=['GET'])
def export_table_by_date(table_name):
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
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={table_name}_{date_column}_{start_date}_to_{end_date}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response


# Export full table to CSV
@export_bp.route('/csv/<table_name>', methods=['GET'])
def export_table(table_name):
    # Validate table_name to prevent SQL injection
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        return jsonify({'error': 'Invalid table name'}), 400
    
    query = f"SELECT * FROM {table_name}"
    data, error = execute_query(query)
    
    if error:
        return jsonify({'error': error}), 500
    
    if not data:
        return jsonify({'error': 'No data found'}), 404
    
    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={table_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response
