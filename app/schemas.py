from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class MovieDB(Base):
    __tablename__ = "movies"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    director = Column(String(100), nullable=False)
    year = Column(Integer, nullable=True)
    genre = Column(String(100), nullable=True)
    rating = Column(Float, default=0.0, index=True)
    description = Column(String(2000), nullable=True)
    duration = Column(Integer, nullable=True)
    cost = Column(Float, default=0.0)
    is_recommended = Column(Boolean, default=False)
    photo_url = Column(String(500), default="static/default_movie.jpg")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    user = relationship("UserDB", back_populates="movies")
    reviews = relationship("ReviewDB", back_populates="movie", cascade="all, delete-orphan")

class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    movies = relationship("MovieDB", back_populates="user")
    reviews = relationship("ReviewDB", back_populates="user", cascade="all, delete-orphan")

class ReviewDB(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    movie = relationship("MovieDB", back_populates="reviews")
    user = relationship("UserDB", back_populates="reviews")