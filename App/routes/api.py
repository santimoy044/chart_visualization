from flask import Blueprint, jsonify, request
from datetime import datetime
from sqlalchemy import text
from App import db

api_bp = Blueprint('api_bp', __name__,  url_prefix='/api')

@api_bp.route('/logs/by-date', methods=['POST'])
def fetch_logs_by_date():
    request_date = request.values.get('date')

    if not request_date:
        return jsonify({'error': 'Date is required'}), 400

    try:
        # Parse the date string to a datetime.date object
        date_obj = datetime.strptime(request_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    try:
        query = text("""
            SELECT * FROM exception_logs
            WHERE DATE(time_occurred) = :date
        """)
        result = db.session.execute(query, {'date': date_obj})
        rows = result.fetchall()

        # Convert result rows into list of dicts
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]

        if not data:
            return jsonify({'count': len(data), 'message': 'No logs/data found for the specified date'}), 404
        
        return jsonify({'count': len(data), 'data': data})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Date range calculation helper
def get_date_range(range_type: str, date_str: str):
    from datetime import timedelta
    import calendar

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

# Flask API Route
@api_bp.route('/logs/trend_analysis', methods=['POST'])
def fetch_logs_by_trend_analysis():
    # data = request.get_json(silent=True) or request.values
    range_type = request.values.get('range')
    date_str = request.values.get('date')

    if not range_type or not date_str:
        return jsonify({'error': 'Both "range" and "date" are required'}), 400

    try:
        start_date, end_date = get_date_range(range_type, date_str)

        query = text("""
            SELECT * FROM exception_logs
            WHERE DATE(time_occurred) BETWEEN :start_date AND :end_date
        """)
        result = db.session.execute(query, {
            'start_date': start_date,
            'end_date': end_date
        })
        rows = result.fetchall()
        columns = result.keys()
        # data = [dict(zip(columns, row)) for row in rows]

        def decode_bytes(val):
            if isinstance(val, bytes):
                try:
                    return val.decode('utf-8')
                except UnicodeDecodeError:
                    return str(val)
            return val

        data = [ {col: decode_bytes(row[i]) for i, col in enumerate(columns)} for row in rows ]

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