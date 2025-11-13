import time
from .extensions import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100))
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.Integer, default=lambda: int(time.time()), nullable=False)

class SessionToken(db.Model):
    __tablename__ = 'sessions'
    token = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    exp = db.Column(db.Integer, nullable=False)
    user = db.relationship('User', backref='sessions', lazy=True)

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    token = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.Integer, default=lambda: int(time.time()), nullable=False)
    user = db.relationship('User', backref='reset_tokens', lazy=True)