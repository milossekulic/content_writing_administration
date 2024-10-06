from jose import JWTError, jwt
from datetime import datetime, timedelta
from . import schemas, database, models
from fastapi import Depends, status, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

from sqlalchemy.orm import Session
from .config import settings

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login',auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')
# SECRET_KEY
# Algorithm
# Expriation time

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_access_token(token: str, credentials_exception):

    try:

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id: str = payload.get("user_id")
        if id is None:
            raise credentials_exception
        token_data = schemas.TokenData(id=id)
    except JWTError:
        raise credentials_exception

    return token_data


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    try:
        # Verify and decode the access token
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
        token_data = verify_access_token(token, credentials_exception)

        # Retrieve user from the database based on decoded token
        user = db.query(models.User).filter(models.User.id == token_data.id, models.User.deleted == False).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return user

    except HTTPException as e:
        # Propagate HTTPExceptions without modification
        raise e

    except Exception as e:
        # Handle other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


    
def admin_api_key( api_key: str = Header(None)):
    if api_key:
        print("tu smoooo")
        # Validate API key
        if api_key != settings.security_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )


oauth2_scheme_2 = OAuth2PasswordBearer(tokenUrl='login',auto_error=False)         
def get_current_user_public(token: Optional[str] = Depends(oauth2_scheme_2), db: Session = Depends(database.get_db)):
    if token:
        credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                            detail=f"Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
        
        try:
            # Add more debugging output if needed
            token = verify_access_token(token, credentials_exception)
        except Exception as e:
            print(f"Token verification failed: {e}")
            raise credentials_exception

        user = db.query(models.User).filter(models.User.id == token.id, models.User.deleted == False).first()

        return user
    else:
        print("Token not provided")
        return False