
from flask import Flask
from routes import export_bp
import os
from dotenv import load_dotenv



# Load environment variables
load_dotenv()

app = Flask(__name__)


# Register Blueprint
app.register_blueprint(export_bp)


if __name__ == '__main__':
    app.run(debug=True)

