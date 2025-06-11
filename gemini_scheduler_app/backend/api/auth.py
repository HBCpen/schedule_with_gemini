from flask import Blueprint, request, jsonify
from models.user import User
from app import db, bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import os

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 400

    new_user = User(email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"msg": "User created successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200

    return jsonify({"msg": "Bad email or password"}), 401

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({"msg": "Logout successful (token invalidated if blocklist implemented)"}), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    # Updated from User.query.get(current_user_id) to db.session.get(User, current_user_id)
    user = db.session.get(User, current_user_id)
    if user:
        return jsonify(logged_in_as=user.email, user_id=user.id), 200
    return jsonify({"msg": "User not found"}), 404
