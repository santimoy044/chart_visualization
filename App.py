from flask import Flask, jsonify
import mysql.connector
from collections import Counter

app = Flask(__name__)


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Ananya@2002",
        database="employeeinfo"
    )


#  Route 1: Return usernames and exception_counts
@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT Username, COUNT(*) AS exception_count
    FROM exception_logs
    GROUP BY Username
    """
    cursor.execute(query)
    result = cursor.fetchall()

    usernames = [row[0] for row in result]
    exception_counts = [row[1] for row in result]

    cursor.close()
    conn.close()

    return jsonify({
        'usernames': usernames,
        'exception_counts': exception_counts
    })


#  Route 2: Return time-based exception data
@app.route('/plot-exceptions')
def plot_exceptions():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT time_occurred, Exception_Type FROM exception_logs")
    rows = cursor.fetchall()
    conn.close()

 
    time_stamps = [row[0].strftime("%Y-%m-%d %H:%M:%S") for row in rows]

    # Count occurrences
    counter = Counter(time_stamps)
    x = list(counter.keys())
    y = list(counter.values())

    # Find max count and time
    max_count = max(y)
    max_time = x[y.index(max_count)]

    return jsonify({
        'x': x,
        'y': y,
        'max_count': max_count,
        'max_time': max_time
    })


if __name__ == '__main__':
    app.run(debug=True)
# code here
# Hello World App