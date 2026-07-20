import hashlib, jwt, uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from config import JWT_SECRET, ACCESS_TOKEN_MINUTES, REFRESH_TOKEN_DAYS
from db import query

def hash_password(password):
    return generate_password_hash(password, method="scrypt")

def verify_password(stored, password):
    if not stored:
        return False
    if stored.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored, password)
    return stored == hashlib.sha256(password.encode()).hexdigest()

def _token(user, kind, expires):
    now=datetime.now(timezone.utc)
    return jwt.encode({
        "id":user["id"], "email":user["email"], "name":user["name"],
        "type":kind, "jti":str(uuid.uuid4()), "iat":now, "exp":now+expires
    }, JWT_SECRET, algorithm="HS256")

def create_token(user):
    return _token(user, "access", timedelta(minutes=ACCESS_TOKEN_MINUTES))

def create_refresh_token(user):
    return _token(user, "refresh", timedelta(days=REFRESH_TOKEN_DAYS))

def decode_token(token, kind="access"):
    data=jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    if data.get("type") != kind:
        raise jwt.InvalidTokenError("Wrong token type")
    return data

def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization','')
        token = auth.split(' ',1)[1] if auth.startswith('Bearer ') else request.cookies.get('access_token')
        if not token: return jsonify({'error':'Token missing'}),401
        try:
            data = decode_token(token, "access")
            user = query('SELECT id,name,email FROM users WHERE id=%s',(data['id'],),fetch=True,one=True)
            if not user: return jsonify({'error':'Invalid user'}),401
            return f(user,*args,**kwargs)
        except Exception:
            return jsonify({'error':'Invalid token'}),401
    return wrapper
