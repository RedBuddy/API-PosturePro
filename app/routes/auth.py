import uuid
from flask import Blueprint, jsonify, request
from app.utils.auth import (
    find_user_by_email, create_user, generate_token, get_current_user,
    create_reset_token, pop_reset_token, hash_password, verify_password,
    invalidate_user_sessions
)
from app.extensions import db
from app.models import User
from app.utils.mailer import send_reset_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def api_register():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    name = (data.get('name') or '').strip()

    if not email or not password:
        return jsonify({'message': 'Email y password son requeridos'}), 400
    if len(password) < 6:
        return jsonify({'message': 'La contraseña debe tener al menos 6 caracteres'}), 400
    if find_user_by_email(email):
        return jsonify({'message': 'El email ya está registrado'}), 409

    user_id = str(uuid.uuid4())
    create_user(user_id, email, name, password)
    token = generate_token(user_id)
    return jsonify({'access_token': token, 'user': {'id': user_id, 'email': email, 'name': name}})

@auth_bp.route('/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    user = find_user_by_email(email)
    if not user or not verify_password(user.password_hash, password):
        return jsonify({'message': 'Credenciales inválidas'}), 401

    token = generate_token(user.id)
    return jsonify({'access_token': token, 'user': {'id': user.id, 'email': user.email, 'name': user.name}})

@auth_bp.route('/forgot-password', methods=['POST'])
def api_forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    user = find_user_by_email(email)
    if user:
        token = create_reset_token(user.id)
        send_reset_email(email, token)
        return jsonify({'message': 'Si el correo existe, se enviará un enlace de recuperación'})
    return jsonify({'message': 'Si el correo existe, se enviará un enlace de recuperación'})

@auth_bp.route('/reset-password', methods=['POST'])
def api_reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get('token')
    new_password = data.get('new_password') or ''
    if not token or not new_password:
        return jsonify({'message': 'Token y nueva contraseña son requeridos'}), 400
    if len(new_password) < 6:
        return jsonify({'message': 'La contraseña debe tener al menos 6 caracteres'}), 400

    user_id = pop_reset_token(token)
    if not user_id:
        return jsonify({'message': 'Token inválido'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'Usuario no encontrado'}), 404

    user.password_hash = hash_password(new_password)
    db.session.commit()
    invalidate_user_sessions(user_id)
    return jsonify({'message': 'Contraseña actualizada'})

@auth_bp.route('/me', methods=['GET'])
def api_me():
    user = get_current_user()
    if not user:
        return jsonify({'message': 'No autorizado'}), 401
    return jsonify(user)