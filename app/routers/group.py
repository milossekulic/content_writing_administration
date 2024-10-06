from typing import List, Optional
from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter, File, Form, UploadFile, Body
from sqlalchemy.orm import Session
import os
from .. import models, schemas, utils, oauth2
from ..database import get_db
from ..config import settings
from fastapi.encoders import jsonable_encoder
html_storage_path = "stored_html"
image_storage_path = "stored_images"


router = APIRouter(
    prefix="/groups",
    tags=['Groups']
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.GroupOut)
def create_group(group_name: str = Form(...),image_file: Optional[UploadFile] = File(None), db: Session = Depends(get_db), current_user: int =Depends(oauth2.get_current_user)):
    #validations
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Access denied")
    
    check_db_user = db.query(models.Group).filter(models.Group.group_name == group_name).first()
    if check_db_user:
        raise HTTPException(status_code=400,detail=f"Group with that name already exists")
    if image_file: 
        os.makedirs(image_storage_path, exist_ok=True)
            # Save the attached image to the images folder
        image_name = f"{len(os.listdir(image_storage_path))}_{image_file.filename}"
        image_path = os.path.join(image_storage_path, image_name)
        
        with open(image_path, "wb") as img_file:
            img_file.write(image_file.file.read())
        image_path = settings.backend_url+image_path
    else:
        image_path = None
        
    new_group = models.Group(group_name=group_name,group_photo_path=image_path )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)

    return new_group

@router.put("/{group_id}", response_model=schemas.GroupOut)
def update_group(
    group_id: int,
    group_name: str = Form(...),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Access denied")
    
    # Check if the group exists
    existing_group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not existing_group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Validate if the new group_name is unique
    if group_name != existing_group.group_name:
        check_db_user = db.query(models.Group).filter(models.Group.group_name == group_name).first()
        if check_db_user:
            raise HTTPException(status_code=400, detail="Group with that name already exists")

    # Handle image file update
    if image_file:
        os.makedirs(image_storage_path, exist_ok=True)
        # Save the attached image to the images folder
        image_name = f"{len(os.listdir(image_storage_path))}_{image_file.filename}"
        image_path = os.path.join(image_storage_path, image_name)

        with open(image_path, "wb") as img_file:
            img_file.write(image_file.file.read())
        updated_group_photo_path = settings.backend_url + image_path
    else:
        # If no new image provided, keep the existing image_path
        updated_group_photo_path = existing_group.group_photo_path

    # Update the group in the database
    existing_group.group_name = group_name
    existing_group.group_photo_path = updated_group_photo_path
    db.commit()
    db.refresh(existing_group)

    return existing_group



@router.get('/{group_id}', response_model=schemas.GroupOut)
def get_group(group_id: int, db: Session = Depends(get_db), current_user: int =Depends(oauth2.get_current_user)):

    if current_user.role != "admin" and (current_user.role == "leader" and current_user.group_id != group_id):
        raise HTTPException(status_code=401, detail="Access denied")
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Group with id: {id} does not exist")

    return group

@router.get('/', response_model=List[schemas.GroupOut])
def get_group_all(db: Session = Depends(get_db), current_user: int =Depends(oauth2.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Access denied")
    group = db.query(models.Group).all()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No groups for now")

    return group

@router.delete("/{group_id}")
async def delete_group_and_update_users(
    group_id: int, db: Session = Depends(get_db), current_user: int =Depends(oauth2.get_current_user)):
    
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Access denied")
    # Check if the group exists
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    # Update users related to the deleted group
    db.query(models.User).filter(models.User.group_id == group_id).update({"group_id": None}, synchronize_session=False)
    
    # Delete the group
    db.query(models.Group).filter(models.Group.id == group_id).delete(synchronize_session=False)


    db.commit()
    
    return {"message": f"Group {group_id} deleted, and related users updated"}



@router.post('/groupping')
def get_group_user(db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Access denied")
        
    result = {}

    # Fetch all groups, including those without users
    all_groups = db.query(models.Group).order_by(models.Group.id).all()

    # Organize the result for all groups
    for group in all_groups:
        result[group.group_name] = []
        
    # Fetch groups with users using SQLAlchemy
    groups_with_users = db.query(models.Group).outerjoin(models.User, models.Group.id == models.User.group_id).order_by(models.Group.id).all()
    
    # Organize the result for groups with users
    for group in groups_with_users:
        result[group.group_name] = [{"user_id": user.id, "username": user.username, "role": user.role} for user in group.users if user.deleted == False]
    # Fetch users without a group and add them to the result
    users_without_group = db.query(models.User).filter(models.User.group_id.is_(None), models.User.deleted == False).all()
    result["without_group"] = [{"user_id": user.id, "username": user.username, "role": user.role} for user in users_without_group]

    

    return result
