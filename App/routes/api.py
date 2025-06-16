from flask import Blueprint, jsonify, request
from datetime import datetime
from sqlalchemy import text
# from App import db
from App import get_db_connection

api_bp = Blueprint('api_bp', __name__,  url_prefix='/api')

@api_bp.route('/logs/by-date', methods=['POST'])
def fetch_logs_by_date():
    request_date = request.values.get('date')

    if not request_date:
        return jsonify({'error': 'Date is required'}), 400

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
def get_date_range(range_type: str, payload: dict):
    import calendar
    from datetime import timedelta

    range_type = range_type.lower()

    if range_type == 'week':
        month = int(payload.get('month'))
        week_number = int(payload.get('week_number'))
        year = int(payload.get('year', datetime.now().year))

        first_day = datetime(year, month, 1).date()
        weekday_offset = first_day.weekday()
        start_date = first_day + timedelta(days=(week_number - 1) * 7 - weekday_offset)
        end_date = start_date + timedelta(days=6)

    elif range_type == 'month':
        month = int(payload.get('month_number'))
        year = int(payload.get('year', datetime.now().year))
        start_date = datetime(year, month, 1).date()
        _, last_day = calendar.monthrange(year, month)
        end_date = datetime(year, month, last_day).date()

    elif range_type == 'quarter':
        month_range = payload.get('month_range')  # Expects '01 to 03' or 'jan to mar'
        year = int(payload.get('year', datetime.now().year))

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
        year = int(payload.get('year'))
        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year, 12, 31).date()

    else:
        raise ValueError("Invalid range type. Use week, month, quarter, or year.")

    return start_date, end_date

@api_bp.route('/logs/trend_analysis', methods=['POST'])
def fetch_logs_by_trend_analysis():
    try:
        payload = request.values.to_dict()  # supports form-data or x-www-form-urlencoded
        range_type = payload.get('range')

        if not range_type:
            return jsonify({'error': '"range" is required'}), 400

        # Get date range using the new helper
        start_date, end_date = get_date_range(range_type, payload)

        query = """
            SELECT * FROM exception_logs
            WHERE DATE(time_occurred) BETWEEN %s AND %s
        """

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(query, (start_date, end_date))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        def decode_bytes(val):
            if isinstance(val, bytes):
                try:
                    return val.decode('utf-8')
                except UnicodeDecodeError:
                    return str(val)
            return val

        data = [{col: decode_bytes(row[i]) for i, col in enumerate(columns)} for row in rows]

        cursor.close()
        conn.close()

        return jsonify({
            'range': range_type,
            'start_date': str(start_date),
            'end_date': str(end_date),
            'count': len(data),
            'data': data
        })

    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
