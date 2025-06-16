# from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from flask import Flask
import os
import mysql.connector

load_dotenv()

# db = SQLAlchemy()

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', DB_HOST),
        user=os.getenv('DB_USER', DB_USER),
        password=os.getenv('DB_PASSWORD', DB_PASS),
        database=os.getenv('DB_NAME', DB_NAME)
    )

def create_app():
    app = Flask(__name__)
    # app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    # app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # db.init_app(app)

    from App.routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # with app.app_context():
    #     db.create_all()

    return app
