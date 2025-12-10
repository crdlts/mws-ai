import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer


class JWTConfig:
    """JWT конфигурация"""
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))


class JWTHandler:
    """JWT токены для авторизации"""
    
    @staticmethod
    def create_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Создает JWT токен"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=JWTConfig.EXPIRATION_HOURS)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode,
            JWTConfig.SECRET_KEY,
            algorithm=JWTConfig.ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Проверяет и декодирует JWT токен"""
        try:
            payload = jwt.decode(
                token,
                JWTConfig.SECRET_KEY,
                algorithms=[JWTConfig.ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )


# FastAPI dependency для авторизации
security = HTTPBearer()


async def verify_jwt_token(credentials = Depends(security)) -> Dict[str, Any]:
    """Dependency для проверки JWT в заголовках"""
    token = credentials.credentials
    return JWTHandler.verify_token(token)