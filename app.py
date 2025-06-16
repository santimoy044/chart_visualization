from flask import Flask
from routes import api
from export_routes import export_bp
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(api)
app.register_blueprint(export_bp)

if __name__ == '__main__':
    app.run(debug=True)

