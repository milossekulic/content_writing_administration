from fastapi import APIRouter, Depends, status, HTTPException, Response
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.logger import logger
import logging
from .. import database, schemas, models, utils, oauth2

router = APIRouter(tags=['Authentication'])

# Configure the root logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@router.post('/login', response_model=schemas.Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    logger.info("LOGIN: %s",user_credentials.username)
    user = db.query(models.User).filter(
        models.User.email == user_credentials.username, models.User.deleted == False).first()

    if not user:
        logger.info("User not exist: %s",user_credentials.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credentials")

    if not utils.verify(user_credentials.password, user.password):
        logger.info("Wrong credentials: %s",user_credentials.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credentials")

    # create a token
    # return token

    access_token = oauth2.create_access_token(data={"user_id": user.id, "role": user.role})

    return {"access_token": access_token, "token_type": "bearer"}