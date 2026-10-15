import base64
import hashlib
import hmac
import os
import jwt
from datetime import timedelta
from fastapi import Depends
from fastapi.security import HTTPBearer
from .core import settings, now, DomainError
from .db import User, get_db

bearer=HTTPBearer(auto_error=False)
def hash_password(password, salt=None):
    salt=salt or os.urandom(16)
    digest=hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000)
    return base64.b64encode(salt+digest).decode()
def check_password(password, stored):
    return hmac.compare_digest(hash_password(password, base64.b64decode(stored)[:16]), stored)
def token(user):
    return jwt.encode({'sub':user.id,'iat':now(),'exp':now()+timedelta(minutes=30),'aud':'marketmind','iss':'marketmind'}, settings.secret, algorithm='HS256')
def identity(credentials=Depends(bearer), db=Depends(get_db)):
    try:
        claims=jwt.decode(credentials.credentials, settings.secret, algorithms=['HS256'], audience='marketmind', issuer='marketmind', options={'require':['sub','exp','iat']})
        user=db.get(User, claims['sub'])
        if not user or not user.active:
            raise ValueError()
        return user
    except (AttributeError, ValueError, jwt.PyJWTError):
        raise DomainError('UNAUTHENTICATED','Sign in again',401)
def admin(user=Depends(identity)):
    if user.role!='administrator' or user.email not in settings.admins:
        raise DomainError('FORBIDDEN','Administrator allowlist required',403)
    return user
