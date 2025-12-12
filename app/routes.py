from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app import models, auth, crud
from app.database import get_db
from app.schemas import MovieDB, ReviewDB, UserDB
from sqlalchemy.orm import selectinload

router = APIRouter()

@router.get("/user/movies/", 
           response_model=List[models.MovieResponse],
           summary="Получить фильмы пользователя",
           description="Возвращает список всех фильмов, добавленных текущим авторизованным пользователем.")
async def read_user_movies(
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MovieDB).where(MovieDB.added_by == current_user.id)
    )
    return result.scalars().all()

@router.post("/user/movies/", 
            response_model=models.MovieResponse,
            summary="Добавить фильм",
            description="Добавляет новый фильм в коллекцию текущего пользователя. Поддерживает загрузку изображения.")
async def create_user_movie(
    title: str = Form(...),
    director: str = Form(...),
    year: Optional[int] = Form(None),
    genre: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    duration: Optional[int] = Form(None),
    cost: float = Form(0.0),
    is_recommended: bool = Form(False),
    rating: float = Form(0.0, ge=0.0, le=10.0),
    photo: Optional[UploadFile] = File(None),
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    movie_data = models.MovieCreate(
        title=title,
        director=director,
        year=year,
        genre=genre,
        description=description,
        duration=duration,
        cost=cost,
        is_recommended=is_recommended,
        rating=rating
    )
    
    return await crud.create_movie(db, movie_data, current_user.id, photo)

@router.put("/user/movies/{movie_id}", 
           response_model=models.MovieResponse,
           summary="Обновить фильм",
           description="Обновляет информацию о фильме. Пользователь может обновлять только свои фильмы.")
async def update_user_movie(
    movie_id: int,
    title: Optional[str] = Form(None),
    director: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    genre: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    duration: Optional[int] = Form(None),
    cost: Optional[float] = Form(None),
    is_recommended: Optional[bool] = Form(None),
    rating: Optional[float] = Form(None, ge=0.0, le=10.0),
    photo: Optional[UploadFile] = File(None),
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    movie = await crud.get_movie(db, movie_id)
    if movie.added_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Этот фильм не принадлежит вам"
        )
    
    update_data = {}
    if title is not None: update_data["title"] = title
    if director is not None: update_data["director"] = director
    if year is not None: update_data["year"] = year
    if genre is not None: update_data["genre"] = genre
    if description is not None: update_data["description"] = description
    if duration is not None: update_data["duration"] = duration
    if cost is not None: update_data["cost"] = cost
    if is_recommended is not None: update_data["is_recommended"] = is_recommended
    if rating is not None: update_data["rating"] = rating
    
    movie_update = models.MovieUpdate(**update_data)
    return await crud.update_movie(db, movie_id, movie_update, photo)

@router.delete("/user/movies/{movie_id}",
              summary="Удалить фильм",
              description="Удаляет фильм из коллекции пользователя. Пользователь может удалять только свои фильмы.")
async def delete_user_movie(
    movie_id: int,
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    movie = await crud.get_movie(db, movie_id)
    if movie.added_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Этот фильм не принадлежит вам"
        )
    
    return await crud.delete_movie(db, movie_id)

@router.get("/recommendations/", 
           response_model=List[models.MovieResponse],
           summary="Получить рекомендации",
           description="Возвращает список рекомендованных фильмов с высоким рейтингом от других пользователей.")
async def get_recommendations(
    current_user = Depends(auth.get_current_user),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MovieDB)
        .where(MovieDB.added_by != current_user.id)
        .where(MovieDB.rating >= 7.0)
        .order_by(MovieDB.rating.desc())
        .limit(limit)
    )
    
    return result.scalars().all()

@router.put("/reviews/{review_id}", 
           response_model=models.ReviewResponse,
           summary="Обновить отзыв",
           description="Обновляет отзыв на фильм. Пользователь может обновлять только свои отзывы.")
async def update_user_review(
    review_id: int,
    review_update: models.ReviewUpdate,
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    review = await crud.get_review(db, review_id)
    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете редактировать только свои отзывы"
        )
    
    return await crud.update_review(db, review_id, review_update)

@router.delete("/reviews/{review_id}",
              summary="Удалить отзыв",
              description="Удаляет отзыв на фильм. Пользователь может удалять свои отзывы, администратор - любые.")
async def delete_user_review(
    review_id: int,
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    review = await crud.get_review(db, review_id)
    if review.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления этого отзыва"
        )
    
    return await crud.delete_review(db, review_id)

@router.get("/admin/reviews-with-details/", 
           response_model=List[models.ReviewWithDetailsResponse],
           summary="Получить все отзывы с деталями (админ)",
           description="Возвращает все отзывы с детальной информацией о фильмах и пользователях. Только для администраторов.")
async def get_all_reviews_with_details_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user = Depends(auth.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ReviewDB)
        .options(selectinload(ReviewDB.user), selectinload(ReviewDB.movie))
        .order_by(ReviewDB.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    reviews = result.scalars().all()
    
    reviews_data = []
    for review in reviews:
        review_response = models.ReviewWithDetailsResponse(
            id=review.id,
            movie_id=review.movie_id,
            user_id=review.user_id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
            username=review.user.username if review.user else "Неизвестный",
            user_email=review.user.email if review.user else None,
            movie_title=review.movie.title if review.movie else "Неизвестный фильм",
            movie_director=review.movie.director if review.movie else "Неизвестный режиссер"
        )
        reviews_data.append(review_response)
    
    return reviews_data

@router.delete("/admin/reviews/{review_id}",
              summary="Удалить любой отзыв (админ)",
              description="Удаляет отзыв на фильм. Только для администраторов.")
async def admin_delete_review(
    review_id: int,
    current_user = Depends(auth.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    return await crud.delete_review(db, review_id)

@router.get("/user/reviews-with-details/", 
           response_model=List[models.ReviewWithDetailsResponse],
           summary="Получить отзывы пользователя с деталями",
           description="Возвращает отзывы текущего пользователя с детальной информацией о фильмах.")
async def get_user_reviews_with_details(
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(ReviewDB, MovieDB)
        .join(MovieDB, ReviewDB.movie_id == MovieDB.id)
        .where(ReviewDB.user_id == current_user.id)
        .order_by(ReviewDB.created_at.desc())
    )
    
    reviews_data = []
    for review, movie in result.all():
        review_response = models.ReviewWithDetailsResponse(
            id=review.id,
            movie_id=review.movie_id,
            user_id=review.user_id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
            username=current_user.username,
            user_email=current_user.email,
            movie_title=movie.title,
            movie_director=movie.director
        )
        reviews_data.append(review_response)
    
    return reviews_data

@router.get("/movies/{movie_id}/reviews", 
           response_model=List[models.ReviewWithUserResponse],
           summary="Получить отзывы на фильм",
           description="Возвращает все отзывы на указанный фильм.")
async def get_movie_reviews(
    movie_id: int,
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(ReviewDB)
        .options(selectinload(ReviewDB.user))
        .where(ReviewDB.movie_id == movie_id)
    )
    
    reviews = result.scalars().all()
    
    review_responses = []
    for review in reviews:
        review_response = models.ReviewWithUserResponse(
            id=review.id,
            movie_id=review.movie_id,
            user_id=review.user_id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
            username=review.user.username,
            user_email=review.user.email
        )
        review_responses.append(review_response)
    
    return review_responses