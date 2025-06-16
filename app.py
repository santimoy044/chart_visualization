from flask import Flask
from routes import api
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Register Blueprint
app.register_blueprint(api)

if __name__ == '__main__':
    app.run(debug=True)

