from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

class MovieBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    director: str = Field(..., min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1888, le=datetime.now().year)
    genre: Optional[str] = None
    rating: float = Field(0.0, ge=0.0, le=10.0)
    description: Optional[str] = None
    duration: Optional[int] = Field(None, ge=1)
    cost: float = Field(0.0, ge=0.0)
    is_recommended: bool = False

class MovieCreate(MovieBase):
    pass

class MovieUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    director: Optional[str] = Field(None, min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1888, le=datetime.now().year)
    genre: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0.0, le=10.0)
    description: Optional[str] = None
    duration: Optional[int] = Field(None, ge=1)
    cost: Optional[float] = Field(None, ge=0.0)
    is_recommended: Optional[bool] = None

class MovieResponse(MovieBase):
    id: int
    photo_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    added_by: Optional[int]
    
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class ReviewBase(BaseModel):
    movie_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)

class ReviewCreate(ReviewBase):
    pass

class ReviewResponse(ReviewBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)

class ReviewWithUserResponse(ReviewResponse):
    username: str
    user_email: Optional[str]
    
    class Config:
        from_attributes = True

class ReviewWithDetailsResponse(ReviewResponse):
    username: str
    user_email: Optional[str]
    movie_title: str
    movie_director: str
    
    class Config:
        from_attributes = True