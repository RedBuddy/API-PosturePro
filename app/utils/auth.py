import time
import secrets
from flask import request
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models import User, SessionToken, PasswordResetToken

def hash_password(pw: str) -> str:
    return generate_password_hash(pw)

def verify_password(pw_hash: str, pw: str) -> bool:
    return check_password_hash(pw_hash, pw)

def find_user_by_email(email: str):
    return User.query.filter_by(email=email).first()

def create_user(user_id: str, email: str, name: str, password: str) -> User:
    user = User(id=user_id, email=email, name=name, password_hash=hash_password(password))
    db.session.add(user)
    db.session.commit()
    return user

def generate_token(user_id: str, ttl_seconds: int = 24 * 3600) -> str:
    token = secrets.token_urlsafe(32)
    exp = int(time.time()) + ttl_seconds
    db.session.add(SessionToken(token=token, user_id=user_id, exp=exp))
    db.session.commit()
    return token

def get_current_user():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth.split(' ', 1)[1].strip()
    st = SessionToken.query.filter_by(token=token).first()
    if not st:
        return None
    if st.exp < int(time.time()):
        db.session.delete(st)
        db.session.commit()
        return None
    u = st.user
    return {'id': u.id, 'email': u.email, 'name': u.name}

def create_reset_token(user_id: str) -> str:
    token = secrets.token_urlsafe(24)
    db.session.add(PasswordResetToken(token=token, user_id=user_id))
    db.session.commit()
    return token

def pop_reset_token(token: str):
    rt = PasswordResetToken.query.filter_by(token=token).first()
    if not rt:
        return None
    user_id = rt.user_id
    db.session.delete(rt)
    db.session.commit()
    return user_id

def invalidate_user_sessions(user_id: str) -> None:
    SessionToken.query.filter_by(user_id=user_id).delete()
    db.session.commit()