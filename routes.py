from flask import Blueprint, request, jsonify
from db import connect_to_db, close_db_connection

# Create a Blueprint for API routes
api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/exception_piechart', methods=['GET'])
def get_exception_piechart():
    time_range = request.args.get('time_range', 'all')  # default is 'all'
    
    conn = connect_to_db()
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