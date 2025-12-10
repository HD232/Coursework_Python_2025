from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status, UploadFile
from typing import List, Optional
from datetime import datetime
import shutil
import os
from app import models
from app import auth
from app.schemas import MovieDB, ReviewDB, UserDB

async def create_user(db: AsyncSession, user: models.UserCreate):
    existing_user = await auth.get_user_by_username(db, user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )
    
    existing_email = await auth.get_user_by_email(db, user.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    hashed_password = auth.get_password_hash(user.password)
    
    db_user = UserDB(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_admin=False
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_movies(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    genre: Optional[str] = None,
    min_rating: Optional[float] = None,
    title: Optional[str] = None
):
    query = select(MovieDB)
    
    if genre:
        query = query.where(MovieDB.genre.contains(genre))
    
    if min_rating:
        query = query.where(MovieDB.rating >= min_rating)
    
    if title:
        query = query.where(MovieDB.title.contains(title))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def get_movie(db: AsyncSession, movie_id: int):
    result = await db.execute(
        select(MovieDB).where(MovieDB.id == movie_id)
    )
    movie = result.scalar_one_or_none()
    
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фильм не найден"
        )
    
    return movie

async def create_movie(
    db: AsyncSession,
    movie: models.MovieCreate,
    user_id: int,
    photo: Optional[UploadFile] = None
):
    photo_url = "static/default_movie.jpg"
    
    if photo and photo.filename:
        os.makedirs("static/uploads", exist_ok=True)
        file_extension = os.path.splitext(photo.filename)[1]
        unique_filename = f"{datetime.now().timestamp()}{file_extension}"
        photo_path = f"static/uploads/{unique_filename}"
        
        with open(photo_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        
        photo_url = photo_path
    
    db_movie = MovieDB(
        **movie.dict(),
        photo_url=photo_url,
        added_by=user_id
    )
    
    db.add(db_movie)
    await db.commit()
    await db.refresh(db_movie)
    return db_movie

async def update_movie(
    db: AsyncSession,
    movie_id: int,
    movie_update: models.MovieUpdate,
    photo: Optional[UploadFile] = None
):
    db_movie = await get_movie(db, movie_id)
    
    update_data = movie_update.dict(exclude_unset=True)
    
    if photo and photo.filename:
        if db_movie.photo_url and db_movie.photo_url != "static/default_movie.jpg":
            if os.path.exists(db_movie.photo_url):
                os.remove(db_movie.photo_url)
        
        os.makedirs("static/uploads", exist_ok=True)
        file_extension = os.path.splitext(photo.filename)[1]
        unique_filename = f"{datetime.now().timestamp()}{file_extension}"
        photo_path = f"static/uploads/{unique_filename}"
        
        with open(photo_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        
        update_data["photo_url"] = photo_path
    
    for field, value in update_data.items():
        setattr(db_movie, field, value)
    
    db_movie.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_movie)
    return db_movie

async def delete_movie(db: AsyncSession, movie_id: int):
    db_movie = await get_movie(db, movie_id)
    
    if db_movie.photo_url and db_movie.photo_url != "static/default_movie.jpg":
        if os.path.exists(db_movie.photo_url):
            os.remove(db_movie.photo_url)
    
    await db.delete(db_movie)
    await db.commit()
    return {"message": "Фильм удален"}

async def create_review(
    db: AsyncSession,
    review: models.ReviewCreate,
    user_id: int
):
    movie = await get_movie(db, review.movie_id)
    
    result = await db.execute(
        select(ReviewDB).where(
            ReviewDB.movie_id == review.movie_id,
            ReviewDB.user_id == user_id
        )
    )
    existing_review = result.scalar_one_or_none()
    
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже оставляли отзыв на этот фильм"
        )
    
    db_review = ReviewDB(
        **review.dict(),
        user_id=user_id
    )
    
    movie_reviews = await get_movie_reviews(db, review.movie_id)
    total_rating = sum([r.rating * 2 for r in movie_reviews]) + (review.rating * 2)  # Конвертация в 0-10
    movie.rating = total_rating / (len(movie_reviews) + 1)
    
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)
    return db_review

async def get_movie_reviews(db: AsyncSession, movie_id: int):
    result = await db.execute(
        select(ReviewDB).where(ReviewDB.movie_id == movie_id)
    )
    return result.scalars().all()

async def get_user_reviews(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(ReviewDB).where(ReviewDB.user_id == user_id)
    )
    return result.scalars().all()

async def get_review(db: AsyncSession, review_id: int):
    result = await db.execute(
        select(ReviewDB).where(ReviewDB.id == review_id)
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )
    return review

async def update_review(db: AsyncSession, review_id: int, review_update: models.ReviewUpdate):
    review = await get_review(db, review_id)
    
    old_rating = review.rating
    update_data = review_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(review, field, value)
    
    await db.commit()
    await db.refresh(review)
    
    if 'rating' in update_data:
        movie = await get_movie(db, review.movie_id)
        movie_reviews = await get_movie_reviews(db, review.movie_id)
        if movie_reviews:
            total_rating = sum([r.rating * 2 for r in movie_reviews])
            movie.rating = total_rating / len(movie_reviews)
            await db.commit()
    
    return review

async def delete_review(db: AsyncSession, review_id: int):
    review = await get_review(db, review_id)
    movie_id = review.movie_id
    
    await db.delete(review)
    await db.commit()
    
    movie = await get_movie(db, movie_id)
    movie_reviews = await get_movie_reviews(db, movie_id)
    if movie_reviews:
        total_rating = sum([r.rating * 2 for r in movie_reviews])
        movie.rating = total_rating / len(movie_reviews)
    else:
        movie.rating = 0.0
    
    await db.commit()
    return {"message": "Отзыв успешно удален"}