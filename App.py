from flask import Flask
from export_routes import export_bp
import os
from dotenv import load_dotenv



# Load environment variables
load_dotenv()

app = Flask(__name__)

# Add security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


# Register Blueprint
app.register_blueprint(export_bp)


if __name__ == '__main__':
    app.run(debug=True)