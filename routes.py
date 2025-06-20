from flask import Blueprint, request, jsonify
from database import get_db_connection, close_db_connection
from datetime import datetime, timedelta
import calendar
from collections import Counter

# Create a Blueprint for API routes
api = Blueprint('api', __name__, url_prefix='/api')

# Helper function to get start and end dates based on range
def get_date_range(range_type: str, date_str: str):
    base_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    range_type = range_type.lower()

    if range_type == 'week':
        start_date = base_date - timedelta(days=base_date.weekday())
        end_date = start_date + timedelta(days=6)
    elif range_type == 'month':
        start_date = base_date.replace(day=1)
        _, last_day = calendar.monthrange(base_date.year, base_date.month)
        end_date = base_date.replace(day=last_day)
    elif range_type == 'quarter':
        quarter = (base_date.month - 1) // 3 + 1
        start_month = 3 * (quarter - 1) + 1
        start_date = datetime(base_date.year, start_month, 1).date()
        end_month = start_month + 2
        _, last_day = calendar.monthrange(base_date.year, end_month)
        end_date = datetime(base_date.year, end_month, last_day).date()
    elif range_type == 'year':
        start_date = datetime(base_date.year, 1, 1).date()
        end_date = datetime(base_date.year, 12, 31).date()
    else:
        raise ValueError("Invalid range type. Use week, month, quarter, or year.")
    
    return start_date, end_date


@api.route('/', methods=['GET'])
def get_user_exception_counts():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to the database"}), 500

    cursor = conn.cursor()

    try:
        query = """
        SELECT Username, COUNT(*) AS exception_count
        FROM exception_logs
        GROUP BY Username
        """
        cursor.execute(query)
        result = cursor.fetchall()

        usernames = [row[0] for row in result]
        exception_counts = [row[1] for row in result]

        return jsonify({
            'usernames': usernames,
            'exception_counts': exception_counts
        })
    except Exception as e:
        print(f"DB Query Error: {e}")
        return jsonify({"error": "Failed to fetch data from DB"}), 500
    finally:
        cursor.close()
        close_db_connection(conn)

@api.route('/plot-exceptions', methods=['GET'])
def plot_exceptions():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to the database"}), 500

    cursor = conn.cursor()

    try:
        cursor.execute("SELECT time_occurred, Exception_Type FROM exception_logs")
        rows = cursor.fetchall()

        time_stamps = [row[0].strftime("%Y-%m-%d %H:%M:%S") for row in rows]

        counter = Counter(time_stamps)
        x = list(counter.keys())
        y = list(counter.values())

        max_count = max(y) if y else 0
        max_time = x[y.index(max_count)] if y else None

        return jsonify({
            'x': x,
            'y': y,
            'max_count': max_count,
            'max_time': max_time
        })
    except Exception as e:
        print(f"DB Query Error: {e}")
        return jsonify({"error": "Failed to fetch data from DB"}), 500
    finally:
        cursor.close()
        close_db_connection(conn)

@api.route('/exception_piechart', methods=['GET'])
def get_exception_piechart():
    time_range = request.args.get('time_range', 'all')  # default is 'all'

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Failed to connect to the database"}), 500

    cursor = conn.cursor()

    try:
        query = "SELECT Exception_Type, COUNT(*) AS count FROM exception_logs"
        
        # Add WHERE clause based on time_range
        if time_range == "day":
            query += " WHERE time_occurred >= NOW() - INTERVAL 1 DAY"
        elif time_range == "week":
            query += " WHERE time_occurred >= NOW() - INTERVAL 7 DAY"
        elif time_range == "month":
            query += " WHERE time_occurred >= NOW() - INTERVAL 1 MONTH"
        elif time_range == "quarter":
            query += " WHERE time_occurred >= NOW() - INTERVAL 3 MONTH"
        elif time_range == "year":
            query += " WHERE time_occurred >= NOW() - INTERVAL 1 YEAR"
        
        query += " GROUP BY Exception_Type"
        
        cursor.execute(query)
        results = cursor.fetchall()

    except Exception as e:
        print(f"DB Query Error: {e}")
        return jsonify({"error": "Failed to fetch data from DB"}), 500
    finally:
        cursor.close()
        close_db_connection(conn)

    data = [{"label": row[0], "value": row[1]} for row in results]
    return jsonify(data)

@api.route('/logs/by-date', methods=['GET'])
def fetch_logs_by_date():
    request_date = request.args.get('date')

    if not request_date:
        return jsonify({'error': 'Date parameter is required'}), 400

    try:
        date_obj = datetime.strptime(request_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT * FROM exception_logs
            WHERE DATE(time_occurred) = %s
        """
        cursor.execute(query, (date_obj,))
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        if not rows:
            return jsonify({'count': 0, 'message': 'No logs/data found for the specified date'}), 404
        
        return jsonify({'count': len(rows), 'data': rows})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Date range calculation helper
def get_date_range(range_type: str, params: dict):
    import calendar
    from datetime import timedelta

    range_type = range_type.lower()

    if range_type == 'week':
        month = int(params.get('month'))
        week_number = int(params.get('week_number'))
        year = int(params.get('year', datetime.now().year))

        first_day = datetime(year, month, 1).date()
        weekday_offset = first_day.weekday()
        start_date = first_day + timedelta(days=(week_number - 1) * 7 - weekday_offset)
        end_date = start_date + timedelta(days=6)

    elif range_type == 'month':
        month = int(params.get('month_number'))
        year = int(params.get('year', datetime.now().year))
        start_date = datetime(year, month, 1).date()
        _, last_day = calendar.monthrange(year, month)
        end_date = datetime(year, month, last_day).date()

    elif range_type == 'quarter':
        month_range = params.get('month_range')  # Expects '01 to 03' or 'jan to mar'
        year = int(params.get('year', datetime.now().year))

        if 'to' in month_range:
            parts = month_range.lower().split('to')
            start_month = parts[0].strip()
            end_month = parts[1].strip()

            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3,
                'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9,
                'oct': 10, 'nov': 11, 'dec': 12
            }

            def to_month(m):
                return int(m) if m.isdigit() else month_map.get(m[:3], 1)

            sm = to_month(start_month)
            em = to_month(end_month)
        else:
            raise ValueError("Invalid month_range format for quarter")

        start_date = datetime(year, sm, 1).date()
        _, last_day = calendar.monthrange(year, em)
        end_date = datetime(year, em, last_day).date()

    elif range_type == 'year':
        year = int(params.get('year'))
        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year, 12, 31).date()

    else:
        raise ValueError("Invalid range type. Use week, month, quarter, or year.")

    return start_date, end_date

@api.route('/logs/trend_analysis', methods=['GET'])
def fetch_logs_by_trend_analysis():
    try:
        range_type = request.args.get('range')

        if not range_type:
            return jsonify({'error': '"range" parameter is required'}), 400

        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Failed to connect to the database"}), 500

        cursor = conn.cursor()

        # Handle different range types
        if range_type == 'weekly':
            # Get exception count for each day of the week (last 7 days)
            query = """
                SELECT 
                    DAYNAME(time_occurred) as day_name,
                    DATE(time_occurred) as date,
                    COUNT(*) as count
                FROM exception_logs 
                WHERE time_occurred >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY DATE(time_occurred), DAYNAME(time_occurred)
                ORDER BY DATE(time_occurred)
            """
            
        elif range_type == 'monthly':
            # Get exception count for each week in the current month
            query = """
                SELECT 
                    CONCAT('Week ', FLOOR((DAY(time_occurred) - 1) / 7) + 1) as week_label,
                    FLOOR((DAY(time_occurred) - 1) / 7) + 1 as week_number,
                    COUNT(*) as count
                FROM exception_logs 
                WHERE MONTH(time_occurred) = MONTH(NOW()) 
                AND YEAR(time_occurred) = YEAR(NOW())
                GROUP BY week_number, week_label
                ORDER BY week_number
            """
            
        elif range_type == 'quarterly':
            # Get exception count for each quarter in the current year
            query = """
                SELECT 
                    CASE 
                        WHEN QUARTER(time_occurred) = 1 THEN 'Q1 (Jan-Mar)'
                        WHEN QUARTER(time_occurred) = 2 THEN 'Q2 (Apr-Jun)'
                        WHEN QUARTER(time_occurred) = 3 THEN 'Q3 (Jul-Sep)'
                        WHEN QUARTER(time_occurred) = 4 THEN 'Q4 (Oct-Dec)'
                    END as quarter_label,
                    QUARTER(time_occurred) as quarter_number,
                    COUNT(*) as count
                FROM exception_logs 
                WHERE YEAR(time_occurred) = YEAR(NOW())
                GROUP BY QUARTER(time_occurred), quarter_label
                ORDER BY QUARTER(time_occurred)
            """
            
        elif range_type == 'yearly':
            # Get exception count for each month in the current year
            query = """
                SELECT 
                    MONTHNAME(time_occurred) as month_name,
                    MONTH(time_occurred) as month_number,
                    COUNT(*) as count
                FROM exception_logs 
                WHERE YEAR(time_occurred) = YEAR(NOW())
                GROUP BY MONTH(time_occurred), MONTHNAME(time_occurred)
                ORDER BY MONTH(time_occurred)
            """
        else:
            return jsonify({'error': 'Invalid range type. Use weekly, monthly, quarterly, or yearly.'}), 400

        cursor.execute(query)
        results = cursor.fetchall()
        
        # Format the response based on range type with complete arrays
        if range_type == 'weekly':
            # Create complete week array (last 7 days)
            data = []
            today = datetime.now().date()
            
            for i in range(7):
                current_date = today - timedelta(days=6-i)
                day_name = current_date.strftime('%A')
                
                # Find if we have data for this date
                found_data = None
                for row in results:
                    if str(row[1]) == str(current_date):
                        found_data = row
                        break
                
                if found_data:
                    data.append({
                        'label': f"{found_data[0]} ({found_data[1]})",
                        'day': found_data[0],
                        'date': str(found_data[1]),
                        'count': found_data[2]
                    })
                else:
                    data.append({
                        'label': f"{day_name} ({current_date})",
                        'day': day_name,
                        'date': str(current_date),
                        'count': 0
                    })
                
        elif range_type == 'monthly':
            # Create complete month array (all weeks in current month)
            data = []
            current_year = datetime.now().year
            current_month = datetime.now().month
            _, last_day = calendar.monthrange(current_year, current_month)
            
            # Calculate weeks within the current month only
            first_day = datetime(current_year, current_month, 1).date()
            last_date = datetime(current_year, current_month, last_day).date()
            
            # Get week numbers within the month
            week_numbers = []
            current_date = first_day
            while current_date <= last_date:
                # Calculate week number within the month (1-5)
                week_of_month = ((current_date.day - 1) // 7) + 1
                if week_of_month not in week_numbers:
                    week_numbers.append(week_of_month)
                current_date += timedelta(days=1)
            
            # Create data for each week
            for week_num in sorted(week_numbers):
                week_label = f"Week {week_num}"
                
                # Find if we have data for this week
                found_data = None
                for row in results:
                    if row[1] == week_num:
                        found_data = row
                        break
                
                if found_data:
                    data.append({
                        'label': found_data[0],
                        'week_number': found_data[1],
                        'count': found_data[2]
                    })
                else:
                    data.append({
                        'label': week_label,
                        'week_number': week_num,
                        'count': 0
                    })
                
        elif range_type == 'quarterly':
            # Create complete quarter array (all 4 quarters)
            data = []
            quarters = [
                {'label': 'Q1 (Jan-Mar)', 'quarter': 1},
                {'label': 'Q2 (Apr-Jun)', 'quarter': 2},
                {'label': 'Q3 (Jul-Sep)', 'quarter': 3},
                {'label': 'Q4 (Oct-Dec)', 'quarter': 4}
            ]
            
            for quarter_info in quarters:
                # Find if we have data for this quarter
                found_data = None
                for row in results:
                    if row[1] == quarter_info['quarter']:
                        found_data = row
                        break
                
                if found_data:
                    data.append({
                        'label': found_data[0],
                        'quarter': found_data[1],
                        'count': found_data[2]
                    })
                else:
                    data.append({
                        'label': quarter_info['label'],
                        'quarter': quarter_info['quarter'],
                        'count': 0
                    })
                
        elif range_type == 'yearly':
            # Create complete year array (all 12 months)
            data = []
            months = [
                {'name': 'January', 'number': 1},
                {'name': 'February', 'number': 2},
                {'name': 'March', 'number': 3},
                {'name': 'April', 'number': 4},
                {'name': 'May', 'number': 5},
                {'name': 'June', 'number': 6},
                {'name': 'July', 'number': 7},
                {'name': 'August', 'number': 8},
                {'name': 'September', 'number': 9},
                {'name': 'October', 'number': 10},
                {'name': 'November', 'number': 11},
                {'name': 'December', 'number': 12}
            ]
            
            for month_info in months:
                # Find if we have data for this month
                found_data = None
                for row in results:
                    if row[1] == month_info['number']:
                        found_data = row
                        break
                
                if found_data:
                    data.append({
                        'label': found_data[0],
                        'month': found_data[1],
                        'count': found_data[2]
                    })
                else:
                    data.append({
                        'label': month_info['name'],
                        'month': month_info['number'],
                        'count': 0
                    })

        cursor.close()
        conn.close()

        return jsonify({
            'range': range_type,
            'total_records': len(data),
            'data': data
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500