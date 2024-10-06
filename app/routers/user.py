from typing import List
from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter, Header, File, Form, UploadFile, Query
from sqlalchemy.orm import Session
from .. import models, schemas, utils, oauth2
from ..database import get_db
from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr
from ..config import settings
import os


router = APIRouter(
    prefix="/user",
    tags=['Users']
)
html_storage_path = "stored_html"
image_storage_path = "stored_images"
'''
INSTRUCTIONS:
if you are admin-->provide leader user id while you are creating new publishers-on that way you can assigne and update who is a leader of which publisher
    1. get all users
    2. you can see user_ids there
    3. you can see who is leader there
    4. take id of the leader
    5. use it while creating a new publisher in this endpoint(create user)


if you are leader-->not required to provide any leader user id because a user that you are creating will be assigned to you
'''
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
def create_user(
    username: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    role: schemas.Roles = Form(...),
    group_id: int = Form(None),
    profile_photo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),):
    #validations
    if current_user.role != "admin":
        raise HTTPException(status_code = 401, detail = f"Access denied")
    
    check_db_user = db.query(models.User).filter((models.User.email == email) | (models.User.username == username)).first()
    if check_db_user:
        raise HTTPException(status_code=404,
                        detail=f"User with this email or username already exists")
    if group_id:
        check_db_group = db.query(models.Group).filter(models.Group.id == group_id).first()
        if not check_db_group:
            raise HTTPException(status_code=404,
                                detail=f"Provided group ID does not exist")

    
    # hash the password - user.password
    hashed_password = utils.hash(password)
    password = hashed_password
    if profile_photo: 
        os.makedirs(image_storage_path, exist_ok=True)
            # Save the attached image to the images folder
        image_name = f"profile_{len(os.listdir(image_storage_path))}_{profile_photo.filename}"
        profile_image_path = os.path.join(image_storage_path, image_name)
        
        with open(profile_image_path, "wb") as img_file:
            img_file.write(profile_photo.file.read())
        profile_image_path = settings.backend_url+profile_image_path
    else:
        profile_image_path = None
    new_user = models.User(username=username,email=email,password=password,role=role,group_id=group_id,profile_image_path=profile_image_path)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    username: str = Form(None),
    email: EmailStr = Form(None),
    password: str = Form(None),
    role: schemas.Roles = Form(None),
    group_id: int = Form(None),
    profile_photo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
):
    # Validate if the current user has the necessary permissions and if current user is not updating his/her settings
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=401, detail="Access denied")

    # Fetch the existing user from the database
    existing_user = db.query(models.User).filter(models.User.id == user_id, models.User.deleted == False).first()
    print(jsonable_encoder(existing_user))
    if not existing_user:
        raise HTTPException(status_code=400,
                        detail=f"User with this id doesn't exist")

    # Validate if the updated email or username is already in use
    if email and email != existing_user.email:
        check_email = db.query(models.User).filter(models.User.email == email).first()
        if check_email:
            raise HTTPException(status_code=400, detail="Email is already in use")
        existing_user.email = email

    if username and username != existing_user.username:
        check_username = db.query(models.User).filter(models.User.username == username).first()
        if check_username:
            raise HTTPException(status_code=400, detail="Username is already in use")
        existing_user.username = username
        
    # Update user fields
    if password:
        existing_user.password = utils.hash(password)
    
    if role and current_user.role == "admin":
        existing_user.role = role
        
    if group_id and current_user.role == "admin":
        check_db_group = db.query(models.Group).filter(models.Group.id == group_id).first()
        if not check_db_group:
            raise HTTPException(status_code=404,
                                detail=f"Provided group ID does not exist")
        existing_user.group_id = group_id
    if profile_photo: 
        os.makedirs(image_storage_path, exist_ok=True)
            # Save the attached image to the images folder
        image_name = f"profile_{len(os.listdir(image_storage_path))}_{profile_photo.filename}"
        profile_image_path = os.path.join(image_storage_path, image_name)
        
        with open(profile_image_path, "wb") as img_file:
            img_file.write(profile_photo.file.read())
        profile_image_path = settings.backend_url+profile_image_path

        existing_user.profile_image_path = profile_image_path
    print(jsonable_encoder(existing_user))
    # Commit changes to the database
    db.commit()
    db.refresh(existing_user)

    return existing_user

@router.delete("/{user_id}", response_model=schemas.UserOut)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    # Validate if the current user has the necessary permissions
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Access denied")

    # Fetch the existing user from the database
    existing_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    # Soft delete the user from the database
    existing_user.deleted = True
    db.commit()
    db.refresh(existing_user)

    return existing_user

@router.get('/me', response_model=schemas.UserOut)
def get_current_user(db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    return current_user

@router.get('/{id}', response_model=schemas.UserOut)
def get_user(id: int, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    if current_user.role == 'publisher':
        raise HTTPException(status_code=401, detail=f"Permission denied")

    # Execute the query to get the user object
    user = db.query(models.User).filter(models.User.id == id, models.User.deleted == False)
    
    if current_user.role == 'leader':
        user = user.filter(models.User.group_id == current_user.group_id)
    
    # Execute the query and get the first result
    user = user.first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with id: {id} does not exist or you don't have access")

    # Use jsonable_encoder here to convert the user object to a JSON-serializable format
    return jsonable_encoder(user)

@router.get('/', response_model=List[schemas.UserOut])
def get_user_all(db: Session = Depends(get_db), current_user: int =Depends(oauth2.get_current_user)):
    if current_user.role == 'publisher':
        raise HTTPException(status_code=401, detail=f"Permission denied")
    user = db.query(models.User).filter(models.User.deleted == False)
    if current_user.role == 'leader':
        user = user.filter(models.User.group_id == current_user.group_id)
    
    user = user.all()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No users for now")

    return user



@router.post("/api_key", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
def create_user_api_key(user: schemas.UserCreate, db: Session = Depends(get_db), api_key: str = Header(None)):
   
    # Validate API key
    if api_key != settings.security_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    check_db_user = db.query(models.User).filter((models.User.email == user.email) | (models.User.username == user.username)).first()
    if check_db_user:
        raise HTTPException(status_code=404,
                        detail=f"User with this email or username already exists")
    if user.group_id:
        check_db_group = db.query(models.Group).filter(models.Group.id == user.group_id).first()
        if not check_db_group:
            raise HTTPException(status_code=404,
                                detail=f"Provided group ID does not exist")

    
    # hash the password - user.password
    hashed_password = utils.hash(user.password)
    user.password = hashed_password

    new_user = models.User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user