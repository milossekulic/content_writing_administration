from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from sqlalchemy.sql.sqltypes import TIMESTAMP, BigInteger
from sqlalchemy.ext.mutable import MutableList

from .database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    html_path = Column(String, nullable=False)
    image_paths = Column(MutableList.as_mutable(ARRAY(String)))
    cover_photo_path = Column(String, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )  # , ondelete="CASCADE"
    author = Column(String)
    category = Column(String, nullable=True)
    description = Column(String)
    group_id = Column(Integer, nullable=True)

    status = Column(String, nullable=False, default="draft")
    user = relationship("User", back_populates="posts")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String(255), nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    profile_image_path = Column(String)
    group_id = Column(
        Integer, ForeignKey("groups.id"), nullable=True
    )  # , ondelete="CASCADE"
    deleted = Column(Boolean, default=False)
    group = relationship("Group", back_populates="users")
    posts = relationship("Post", back_populates="user")


class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, nullable=False)
    group_name = Column(
        String,
        nullable=True,
    )
    group_photo_path = Column(String, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    users = relationship("User", back_populates="group")
