from logging import raiseExceptions
from typing import List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
    File,
    Form,
    UploadFile,
    Query,
)
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.logger import logger
import logging
from sqlalchemy.orm.session import Session
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from ..database import get_db
from .. import models, schemas, oauth2
import os

# from bs4 import BeautifulSoup
from ..config import settings
from fastapi.encoders import jsonable_encoder
from typing import Optional, Union

# Configure the root logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

html_storage_path = "stored_html"
image_storage_path = "stored_images"

router = APIRouter(prefix="/posts", tags=["Post"])

# @router.get('/category_groupping')
# def get_lists(db: Session = Depends(get_db)):
#     # Assuming Post has a 'category' attribute
#     posts = (
#         db.query(models.Post.category,
#                  func.array_agg(models.Post.id).label('post_ids'),
#                  func.array_agg(models.Post.title).label('titles'),
#                  func.array_agg(models.Post.slug).label('slug'),
#                  func.array_agg(models.Post.cover_photo_path).label('cover_photo_path'),
#                  func.array_agg(models.Post.author).label('author'),
#                  func.array_agg(models.Post.created_at).label('created_at'),
#                  func.array_agg(models.Post.category).label('category')
#                  # Add other columns as needed
#         )
#         .group_by(models.Post.category)
#         .all()
#     )

#     if not posts:
#         raise HTTPException(status_code=404, detail="No posts found")

#     formatted_response = {}
#     for post_category, post_ids, post_titles, slugs, cover_photo_paths, authors, created_ats,categories in posts:
#         category_posts = []
#         for post_id, post_title, slug, cover_photo_path, author, created_at,category in zip(post_ids, post_titles, slugs, cover_photo_paths, authors, created_ats,categories):
#             category_posts.append({
#                 "id": post_id,
#                 "title": post_title,
#                 "slug": slug,
#                 "cover_photo_path": cover_photo_path,
#                 "author": author,
#                 "created_at": created_at,
#                 "category": category,
#                 # Add other attributes as needed
#             })
#         formatted_response[post_category] = category_posts

#     return formatted_response


@router.get("/")
async def get_posts(
    category: str = Query(None),
    user_id: int = Query(None),
    author: str = Query(None),
    group_id: int = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user_public),
):
    # Construct a filter dictionary based on provided parameters
    filters = {}
    if category is not None:
        filters["category"] = category
    if user_id is not None:
        filters["user_id"] = user_id
    if author is not None:
        filters["author"] = author
    if group_id is not None:
        filters["group_id"] = group_id

    if current_user:
        logger.info("USER: %s", current_user.username)
        if status is not None:
            filters["status"] = status
        if current_user.role == "publisher":
            # PLACEHOLDER:  STATUS = SUBMITED -->GIVE BACK ALL SUBMITED TO LEADER(publisher push, leader review!!!!)
            filters["user_id"] = current_user.id
        if current_user.role == "leader":
            # PLACEHOLDER:  STATUS = SUBMITED -->GIVE BACK ALL SUBMITED TO ADMIN
            filters["group_id"] = current_user.group_id
    else:
        logger.info("USER: %s external")
        filters["status"] = "published"

    # posts = db.query(models.Post).filter_by(**filters).all()
    posts = (
        db.query(models.Post)
        .filter_by(**filters)
        .options(joinedload(models.Post.user).load_only("profile_image_path"))
        .all()
    )
    return jsonable_encoder(posts)


# placeholder for get all by admin/filtering
# @router.get('/')
# def get_lists( db:Session=Depends(get_db),current_user: int =Depends(oauth2.get_current_user)):
#     # Construct the full file path
#     # file_path = os.path.join(html_storage_path, file_name)
#     # posts = db.query(models.Post).filter(models.Post.id == id).all()
#     posts = db.query(models.Post).all()
#     if not posts:
#         raise HTTPException(status_code=404, detail="No posts found")


#     return posts


# image_files: if there is no any updates, please provide None as a value
@router.post("/upload_images")
async def upload_images(
    image_file: UploadFile = File(
        ...
    ),  # , max_length=10 * 1024 * 1024 Set your desired max length
    current_user: int = Depends(oauth2.get_current_user),
):
    logger.info("USER: %s", current_user.username)
    if image_file:
        html_storage_path = "stored_images"
        os.makedirs(html_storage_path, exist_ok=True)
        # Save the attached image to the images folder
        image_name = f"{len(os.listdir(html_storage_path))}_{image_file.filename}"
        image_path = os.path.join(html_storage_path, image_name)
        logger.info("IMAGE PATH: %s", image_path)
        with open(image_path, "wb") as img_file:
            img_file.write(image_file.file.read())

        return {"uploaded_paths": settings.backend_url + image_path}


@router.post("/draft_html")
def draft_html(
    title: str = Form(...),
    slug: str = Form(...),
    category: schemas.Categories = Form(None),
    description: str = Form(None),
    html_content: str = Form(...),
    cover_photo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
):
    logger.info("USER: %s", current_user.username)
    post_check = db.query(models.Post).filter(models.Post.title == title).first()
    if post_check:
        logger.error("Post with this title already exists")
        raise HTTPException(
            status_code=404, detail="Post with this title already exists"
        )
    post_check = db.query(models.Post).filter(models.Post.slug == slug).first()
    if post_check:
        logger.error("Post with this slug already exists")
        raise HTTPException(
            status_code=404, detail="Post with this slug already exists"
        )
    # Ensure that the 'stored_html' folder exists
    html_storage_path = "stored_html"
    os.makedirs(html_storage_path, exist_ok=True)

    # Save the HTML content to the storage folder
    file_name = f"{len(os.listdir(html_storage_path)) + 1}.html"
    file_path = os.path.join(html_storage_path, file_name)

    with open(file_path, "w", encoding="utf-8") as html_file:
        html_file.write(html_content)

    if cover_photo:
        os.makedirs(image_storage_path, exist_ok=True)
        # Save the attached image to the images folder
        image_name = (
            f"cover_{len(os.listdir(image_storage_path))}_{cover_photo.filename}"
        )
        cover_image_path = os.path.join(image_storage_path, image_name)

        with open(cover_image_path, "wb") as img_file:
            img_file.write(cover_photo.file.read())
        cover_image_path = settings.backend_url + cover_image_path
    else:
        cover_image_path = []

    new_post = models.Post(
        user_id=current_user.id,
        group_id=current_user.group_id,
        author=current_user.username,
        slug=slug,
        title=title,
        category=category,
        description=description,
        html_path=file_path,
        cover_photo_path=cover_image_path,
        status="draft",
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


# @router.post("/draft_html")
# def draft_html(
#     title: str = Form(...),
#     slug: str = Form(...),
#     category: schemas.Categories = Form(None),
#     description: str = Form(None),
#     html_content: str = Form(...),
#     image_files: List[Union[UploadFile, None]] = File(None),
#     cover_photo: UploadFile = File(...),
#     db: Session = Depends(get_db),
#     current_user: int = Depends(oauth2.get_current_user),
# ):
#     print(current_user.id, current_user.role)
#     post_check = db.query(models.Post).filter(models.Post.title == title).first()
#     if post_check:
#         raise HTTPException(status_code=404, detail="Post with this title already exists")
#     post_check = db.query(models.Post).filter(models.Post.slug == slug).first()
#     if post_check:
#         raise HTTPException(status_code=404, detail="Post with this slug already exists")
#     # Ensure that the 'stored_html' folder exists
#     html_storage_path = "stored_html"
#     os.makedirs(html_storage_path, exist_ok=True)

#     # Save the HTML content to the storage folder
#     file_name = f"{len(os.listdir(html_storage_path)) + 1}.html"
#     file_path = os.path.join(html_storage_path, file_name)

#     with open(file_path, "w", encoding="utf-8") as html_file:
#         html_file.write(html_content)
#     if image_files:
#         list_of_paths = []
#         html_storage_path = "stored_images"
#         os.makedirs(html_storage_path, exist_ok=True)
#         for image_file in image_files:
#             # Save the attached image to the images folder
#             # image_name = f"{len(os.listdir(image_storage_path))}_{image_file.filename}"
#             #image_name = f"{image_file.filename}"
#             image_path = os.path.join(image_storage_path, image_file.filename)

#             with open(image_path, "wb") as img_file:
#                 img_file.write(image_file.file.read())
#             list_of_paths.append(settings.backend_url+image_path)
#     else:
#         list_of_paths = None
#     if cover_photo:
#         os.makedirs(image_storage_path, exist_ok=True)
#             # Save the attached image to the images folder
#         image_name = f"cover_{len(os.listdir(image_storage_path))}_{cover_photo.filename}"
#         cover_image_path = os.path.join(image_storage_path, image_name)

#         with open(cover_image_path, "wb") as img_file:
#             img_file.write(cover_photo.file.read())
#         cover_image_path = settings.backend_url+cover_image_path
#     else:
#         cover_image_path = []
#     print(current_user.id, current_user.role)

#     new_post=models.Post(user_id=current_user.id,group_id=current_user.group_id, author=current_user.username,slug=slug, title=title, category=category, description=description, html_path=file_path, image_paths=list_of_paths, cover_photo_path=cover_image_path, status="draft")
#     db.add(new_post)
#     db.commit()
#     db.refresh(new_post)
#     return new_post

#     # new_group = models.Group(group_name=group_name,group_photo_path=image_path )
#     return {"message": f"HTML content and image saved: {file_name}, {image_file.filename}"}


# image_files: if there is no any updates, please provide None as a value
# if you want to update the old HTML with additional image, you need to reference it on the right way 'https://url to backend/stored_images/name of image and upload it in 'image_files'. Other references from HTML should not be touched except you are changint it's path with new image that you are uploading
@router.put("/update_html")
def update_html(
    post_slug: str = Form(...),
    title: str = Form(None),
    slug: str = Form(None),
    category: schemas.Categories = Form(None),
    description: str = Form(None),
    html_content: str = Form(None),
    # image_files: List[Union[UploadFile, None]] = File(None),
    cover_photo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
):
    logger.info("USER: %s", current_user.username)
    # Fetch the existing post from the database
    post = db.query(models.Post).filter(models.Post.slug == post_slug)
    if current_user.role == "leader":
        post.filter(models.Post.group_id == current_user.group_id)
    if current_user.role == "publisher":
        post.filter(models.Post.user_id == current_user.id)
    post = post.first()

    if not post:
        logger.info("Post not found, or access denied")
        raise HTTPException(status_code=404, detail="Post not found, or access denied")

    # Update the existing post with the new data
    if title:
        post.title = title
    if slug:
        post.slug = slug
    if category:
        post.category = category
    if description:
        post.description = description
    # Save the updated HTML content to the storage folder. Images can be edited only if the whole HTML content is provided
    if html_content:
        file_name = post.html_path
        file_path = os.path.join(file_name)

        with open(file_path, "w", encoding="utf-8") as html_file:
            html_file.write(html_content)

        # Handle image updates
        # if image_files:
        #     list_of_paths = []
        #     image_storage_path = "stored_images"
        #     os.makedirs(image_storage_path, exist_ok=True)
        #     for image_file in image_files:
        #         image_name = f"{image_file.filename}"
        #         image_path = os.path.join(image_storage_path, image_name)
        #         with open(image_path, "wb") as img_file:
        #             img_file.write(image_file.file.read())
        #         if post.image_paths:
        #             post.image_paths.append(settings.backend_url + image_path)
        #         else:
        #             post.image_paths = []
        #             post.image_paths.append(settings.backend_url + image_path)
        #     # post.image_paths = list_of_paths

    # Handle cover photo update
    if cover_photo:
        image_storage_path = "stored_images"
        os.makedirs(image_storage_path, exist_ok=True)
        cover_image_name = f"cover_{cover_photo.filename}"
        cover_image_path = os.path.join(image_storage_path, cover_image_name)
        with open(cover_image_path, "wb") as img_file:
            img_file.write(cover_photo.file.read())
        post.cover_photo_path = settings.backend_url + cover_image_path

    # Commit the changes to the database
    db.commit()
    db.refresh(post)

    """VRATI OVDE REFRESH POST
    i 
    DUZINA ACCESS TOKENA"""
    return post


"""NAPRAVI BRISANJE SLIKAAAAA ILI HTML FAJLAAAAA



"""


# USE THIS ACCESS POINT FOR NOT AUTHENTICATED USERS
@router.get("/html/{slug}")
async def get_html(
    slug: str,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user_public),
):
    if current_user:
        post = db.query(models.Post).filter(models.Post.slug == slug)
        logger.info("USER: %s", current_user.username)
        if current_user.role == "publisher":
            # PLACEHOLDER:  STATUS = SUBMITED -->GIVE BACK ALL SUBMITED TO LEADER(publisher push, leader review!!!!)
            post.filter(models.Post.user_id == current_user.id)
        if current_user.role == "leader":
            # PLACEHOLDER:  STATUS = SUBMITED -->GIVE BACK ALL SUBMITED TO ADMIN
            post.filter(models.Post.group_id == current_user.group_id)
    else:
        logger.info("USER: %s external")
        post = db.query(models.Post).filter(
            models.Post.slug == slug, models.Post.status == "published"
        )

    post = post.first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found, or access denied")
    # Check if the file exists
    if not os.path.isfile(post.html_path):
        raise HTTPException(status_code=404, detail="HTML file not found.")

    # Read the HTML content from the file
    with open(post.html_path, "r", encoding="utf-8") as html_file:
        html_content = html_file.read()

    # Return the HTML content as a response
    # return {
    #     "html":HTMLResponse(content=html_content),
    #     "post_data":post
    #     }
    return HTMLResponse(content=html_content)


# USE THIS ACCESS POINT FOR AUTHENTICATED USERS
@router.get("/post/{slug}")
async def get_html(
    slug: str,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user_public),
):
    if current_user:
        post = (
            db.query(models.Post, models.User.username, models.User.role)
            .filter(models.Post.slug == slug)
            .outerjoin(models.User, models.Post.user_id == models.User.id)
            .with_entities(
                models.Post.author,
                models.Post.category,
                models.Post.created_at,
                models.Post.description,
                models.Post.title,
                models.Post.status,
                models.Post.cover_photo_path,
                models.User.profile_image_path,
                models.User.role,
                models.User.id,
                models.User.email,
                models.User.group_id,
                models.User.group,
            )
        )
        if current_user.role == "leader":
            post.filter(models.Post.group_id == current_user.group_id)
        if current_user.role == "publisher":
            post.filter(models.Post.user_id == current_user.id)
        post = post.first()
        if not post:
            raise HTTPException(
                status_code=404, detail="Post not found, or access denied"
            )
    # this is for publish access:
    else:
        post = (
            db.query(models.Post, models.User.username, models.User.role)
            .filter(models.Post.slug == slug, models.Post.status == "published")
            .outerjoin(models.User, models.Post.user_id == models.User.id)
            .with_entities(
                models.Post.author,
                models.Post.category,
                models.Post.created_at,
                models.Post.description,
                models.Post.title,
                models.Post.cover_photo_path,
                models.User.profile_image_path,
            )
            .first()
        )
        if not post:
            raise HTTPException(
                status_code=404, detail="Post not found, or access denied"
            )

    return jsonable_encoder(post)


@router.get("/images/{image_name}")
async def get_image(image_name: str):
    # Construct the full file path
    image_path = os.path.join(image_storage_path, image_name)

    # Check if the image file exists
    if not os.path.isfile(image_path):
        raise HTTPException(status_code=404, detail="Image not found.")

    # Return the image file as a response
    return FileResponse(image_path, media_type="image/jpeg")


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_list(
    slug: str,
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
):
    logger.info("USER: %s", current_user.username)
    # Fetch the existing post from the database
    post_query = db.query(models.Post).filter(models.Post.slug == slug)
    if current_user.role == "leader":
        post_query.filter(models.Post.group_id == current_user.group_id)
    if current_user.role == "publisher":
        post_query.filter(models.Post.user_id == current_user.id)
    post = post_query.first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found, or access denied")
    post_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/publish")
def update_status(
    slug: str = Form(...),
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
):
    logger.info("USER: %s", current_user.username)
    # Fetch the existing post from the database
    post = db.query(models.Post).filter(models.Post.slug == slug)
    if current_user.role == "leader":
        post.filter(models.Post.group_id == current_user.group_id)
    if current_user.role == "publisher":
        post.filter(models.Post.user_id == current_user.id)
    post = post.first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found, or access denied")

    if current_user.role == "publisher":
        if current_user.group_id == None:
            post.status = "submited_to_admin"
        else:
            find_leader = (
                db.query(models.User)
                .filter(models.User.group_id == current_user.group_id)
                .all()
            )
            if find_leader:
                leader_found = False
                for user in find_leader:
                    if user.role == "leader":
                        leader_found = True
                        break
                if leader_found:
                    post.status = "submited_to_leader"
                else:
                    post.status = "submited_to_admin"
    if current_user.role == "leader":
        post.status = "submited_to_admin"
    if current_user.role == "admin":
        post.status = "published"

    # Commit the changes to the database
    db.commit()
    db.refresh(post)
    return jsonable_encoder(post)


@router.put("/refuse")
def update_status(
    slug: str = Form(...),
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user),
):
    logger.info("USER: %s", current_user.username)
    # Fetch the existing post from the database
    post = db.query(models.Post).filter(models.Post.slug == slug)
    if current_user.role == "leader":
        post.filter(models.Post.group_id == current_user.group_id)
    if current_user.role == "publisher":
        post.filter(models.Post.user_id == current_user.id)
    post = post.first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found, or access denied")

    if current_user.role == "publisher":
        post.status = "refused"
    if current_user.role == "leader":
        post.status = "refused"
    if current_user.role == "admin":
        post.status = "refused"

    # Commit the changes to the database
    db.commit()

    return jsonable_encoder(post)
