from App import db

class ExceptionLog(db.Model):
    __tablename__ = 'exception_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False)