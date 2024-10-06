from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic.types import conint



class Categories(str, Enum):
    medicine = "Medicine"
    education = "Education"
    humanitarian_aid = "Humanitarian aid"
    
class Roles(str, Enum):
    admin = "admin"
    leader = "leader"
    publisher = "publisher"

class Status(str, Enum):
    draft = "draft"
    sent_to_leader = "sent_to_leader"
    sent_to_admin = "sent_to_admin"
    refused = "refused"
    published = "published"
    
class PostBase(BaseModel):
    title: str
    html_path: str
    image_paths: Optional[List[str]]
    category: Optional[str]
    
class PostCreate(PostBase):
    approve: bool = False
    reject:bool = False
    

class PostOut(PostBase):
    user_id: int
    group_id: Optional[int]
    status: Status
    class Config:
        orm_mode = True
    
class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: Roles
    created_at: datetime    
    group_id: Optional[int]
    profile_image_path: Optional[str]
    class Config:
        orm_mode = True




class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Roles
    group_id: Optional[int]


    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[Roles] = None
    group_id: Optional[int] = None

    class Config:
        orm_mode = True
        
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[str] = None


class Group(BaseModel):
    group_name: str
    
class GroupIn(Group):
    pass
    class Config:
        orm_mode = True

class GroupOut(Group):
    id: int
    group_photo_path: Optional[str]
    created_at: datetime
    class Config:
        orm_mode = True