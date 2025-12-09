from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import timedelta
import os

from app import models, auth, crud
from app.database import get_db, init_db
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI(
    title="Movie Rating API",
    description="API для учета просмотренных фильмов с рейтингами и отзывами",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Создаем директорию для статических файлов
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация БД при старте
# Инициализация БД при старте
# Инициализация БД при старте
@app.on_event("startup")
async def startup_event():
    await init_db()
    
    # Создаем администратора при первом запуске
    async for db in get_db():
        try:
            admin = await crud.create_admin_user(db)
            print(f"✅ Администратор создан: {admin.username}")
            await db.close()  # Явно закрываем сессию
            break
        except Exception as e:
            print(f"⚠️ Администратор уже существует или ошибка: {e}")
            await db.close()  # Явно закрываем сессию
            break

# ============ Главная страница ============
@app.get("/", response_class=HTMLResponse, summary="Главная страница")
async def home():
    return HTMLResponse("""
    <html>
        <head>
            <title>Movie Rating API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .method { display: inline-block; padding: 5px 10px; border-radius: 3px; color: white; font-weight: bold; }
                .get { background: #61affe; }
                .post { background: #49cc90; }
                .put { background: #fca130; }
                .delete { background: #f93e3e; }
            </style>
        </head>
        <body>
            <h1>🎬 Movie Rating API</h1>
            <p>Добро пожаловать в систему учета фильмов с рейтингами и отзывами!</p>
            
            <h2>🔑 Аутентификация</h2>
            <div class="endpoint">
                <span class="method get">GET</span> <strong><a href="/register-page">/auth/register</a></strong> - Форма регистрации
            </div>
            <div class="endpoint">
                <span class="method post">POST</span> <strong>/auth/register</strong> - Регистрация (API)
            </div>
            <div class="endpoint">
                <span class="method get">GET</span> <strong><a href="/login-page">/auth/login</a></strong> - Форма входа
            </div>
            <div class="endpoint">
                <span class="method post">POST</span> <strong>/auth/login</strong> - Вход (API)
            </div>
            
            <h2>🎥 Фильмы</h2>
            <div class="endpoint">
                <span class="method get">GET</span> <strong>/movies/</strong> - Все фильмы
            </div>
            <div class="endpoint">
                <span class="method get">GET</span> <strong>/movies/{id}</strong> - Фильм по ID
            </div>
            
            <h2>⭐ Отзывы</h2>
            <div class="endpoint">
                <span class="method post">POST</span> <strong>/reviews/</strong> - Добавить отзыв
            </div>
            
            <h2>👑 Админ-панель</h2>
            <p><a href="/admin-panel">Перейти в админ-панель</a></p>
            
            <h2>📚 Документация</h2>
            <ul>
                <li><a href="/docs">Swagger UI документация</a></li>
                <li><a href="/redoc">ReDoc документация</a></li>
            </ul>
            
            <script>
                // Проверка авторизации
                const token = localStorage.getItem('access_token');
                if (token) {
                    try {
                        const payload = JSON.parse(atob(token.split('.')[1]));
                        document.body.innerHTML += '<p style="color: green;">✓ Вы авторизованы как: ' + payload.sub + '</p>';
                    } catch (e) {
                        console.log('Ошибка декодирования токена');
                    }
                }
            </script>
        </body>
    </html>
    """)

# ============ HTML формы для регистрации и входа ============
@app.get("/auth/register", response_class=HTMLResponse, summary="Форма регистрации")
async def register_form():
    return RedirectResponse(url="/register-page")

@app.get("/auth/login", response_class=HTMLResponse, summary="Форма входа")
async def login_form():
    return RedirectResponse(url="/login-page")

# ============ Аутентификация (API) ============
@app.post("/auth/register", response_model=models.UserResponse, summary="Регистрация")
async def register(user: models.UserCreate, db: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя"""
    return await crud.create_user(db, user)

@app.post("/auth/login", response_model=models.Token, summary="Вход")
async def login(user_data: models.UserLogin, db: AsyncSession = Depends(get_db)):
    """Вход в систему. Возвращает JWT токен."""
    user = await auth.authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Обновляем время последнего входа
    from datetime import datetime
    user.last_login = datetime.utcnow()
    await db.commit()
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# ============ Фильмы (публичные) ============
@app.get("/movies/", response_model=List[models.MovieResponse], summary="Все фильмы")
async def read_movies(
    skip: int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(100, ge=1, le=100, description="Лимит записей"),
    genre: Optional[str] = Query(None, description="Фильтр по жанру"),
    min_rating: Optional[float] = Query(None, ge=0.0, le=10.0, description="Минимальный рейтинг"),
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех фильмов с фильтрацией"""
    return await crud.get_movies(db, skip=skip, limit=limit, genre=genre, min_rating=min_rating)

@app.get("/movies/{movie_id}", response_model=models.MovieResponse, summary="Фильм по ID")
async def read_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    """Получить информацию о конкретном фильме"""
    return await crud.get_movie(db, movie_id)

# ============ Отзывы ============
@app.post("/reviews/", response_model=models.ReviewResponse, summary="Добавить отзыв")
async def create_review(
    review: models.ReviewCreate,
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Добавить отзыв на фильм (требует авторизации)"""
    return await crud.create_review(db, review, current_user.id)

@app.get("/reviews/", response_model=List[models.ReviewResponse], summary="Получить отзывы")
async def read_reviews(
    movie_id: Optional[int] = Query(None, description="ID фильма"),
    skip: int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(100, ge=1, le=100, description="Лимит записей"),
    db: AsyncSession = Depends(get_db)
):
    """Получить список отзывов с фильтрацией по фильму"""
    if movie_id:
        return await crud.get_movie_reviews(db, movie_id)
    # Если не указан movie_id, возвращаем все отзывы (с пагинацией)
    from sqlalchemy.future import select
    from app.schemas import ReviewDB
    result = await db.execute(
        select(ReviewDB).offset(skip).limit(limit)
    )
    return result.scalars().all()

# ============ Админ-панель (CRUD для фильмов) ============
@app.post("/admin/movies/", response_model=models.MovieResponse, summary="Добавить фильм (админ)")
async def admin_create_movie(
    title: str = Form(...),
    director: str = Form(...),
    year: Optional[int] = Form(None),
    genre: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    duration: Optional[int] = Form(None),
    cost: float = Form(0.0),
    is_recommended: bool = Form(False),
    photo: Optional[UploadFile] = File(None),
    current_user = Depends(auth.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Добавить новый фильм (требуются права администратора)"""
    movie_data = models.MovieCreate(
        title=title,
        director=director,
        year=year,
        genre=genre,
        description=description,
        duration=duration,
        cost=cost,
        is_recommended=is_recommended
    )
    
    return await crud.create_movie(db, movie_data, current_user.id, photo)

@app.put("/admin/movies/{movie_id}", response_model=models.MovieResponse, summary="Обновить фильм (админ)")
async def admin_update_movie(
    movie_id: int,
    title: Optional[str] = Form(None),
    director: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    genre: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    duration: Optional[int] = Form(None),
    cost: Optional[float] = Form(None),
    is_recommended: Optional[bool] = Form(None),
    photo: Optional[UploadFile] = File(None),
    current_user = Depends(auth.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновить информацию о фильме (требуются права администратора)"""
    update_data = {}
    if title is not None: update_data["title"] = title
    if director is not None: update_data["director"] = director
    if year is not None: update_data["year"] = year
    if genre is not None: update_data["genre"] = genre
    if description is not None: update_data["description"] = description
    if duration is not None: update_data["duration"] = duration
    if cost is not None: update_data["cost"] = cost
    if is_recommended is not None: update_data["is_recommended"] = is_recommended
    
    movie_update = models.MovieUpdate(**update_data)
    return await crud.update_movie(db, movie_id, movie_update, photo)

@app.delete("/admin/movies/{movie_id}", summary="Удалить фильм (админ)")
async def admin_delete_movie(
    movie_id: int,
    current_user = Depends(auth.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить фильм (требуются права администратора)"""
    return await crud.delete_movie(db, movie_id)

# ============ HTML интерфейсы ============
@app.get("/admin-panel", response_class=HTMLResponse, summary="Панель администратора")
async def admin_panel():
    return HTMLResponse("""
    <html>
        <head>
            <title>Панель администратора</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
                .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
                th { background: #f5f5f5; }
                input, textarea { width: 100%; padding: 8px; margin: 5px 0; }
                button { background: #49cc90; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 10px 5px; }
                .delete-btn { background: #f93e3e; }
            </style>
        </head>
        <body>
            <h1>🎬 Панель администратора</h1>
            
            <div id="authInfo"></div>
            
            <div class="section">
                <h2>➕ Добавить фильм</h2>
                <form id="addMovieForm" enctype="multipart/form-data">
                    <input type="text" name="title" placeholder="Название" required>
                    <input type="text" name="director" placeholder="Режиссёр" required>
                    <input type="number" name="year" placeholder="Год">
                    <input type="text" name="genre" placeholder="Жанр">
                    <textarea name="description" placeholder="Описание" rows="3"></textarea>
                    <input type="number" name="duration" placeholder="Длительность (минут)">
                    <input type="number" name="cost" placeholder="Бюджет" step="0.01">
                    <label><input type="checkbox" name="is_recommended"> Рекомендуется</label>
                    <input type="file" name="photo" accept="image/*">
                    <button type="submit">Добавить</button>
                </form>
                <div id="message"></div>
            </div>
            
            <div class="section">
                <h2>📋 Список фильмов</h2>
                <div id="moviesList">Загрузка...</div>
            </div>
            
            <div class="section">
                <h2>⭐ Управление отзывами</h2>
                <div id="reviewsList">Загрузка отзывов...</div>
            </div>
            
            <p><a href="/">На главную</a></p>
            
            <script>
                // Проверка авторизации
                const token = localStorage.getItem('access_token');
                const authInfo = document.getElementById('authInfo');
                
                if (!token) {
                    authInfo.innerHTML = '<p style="color: red;">❌ Вы не авторизованы. <a href="/login-page">Войдите</a></p>';
                } else {
                    try {
                        const payload = JSON.parse(atob(token.split('.')[1]));
                        authInfo.innerHTML = `<p style="color: green;">✓ Авторизован как: ${payload.sub}</p>`;
                        loadMovies();
                        loadReviews();
                    } catch (e) {
                        authInfo.innerHTML = '<p style="color: red;">❌ Неверный токен</p>';
                    }
                }
                
                // Загрузка фильмов
                async function loadMovies() {
                    try {
                        const response = await fetch('/movies/?limit=50');
                        if (!response.ok) throw new Error('Ошибка загрузки');
                        const movies = await response.json();
                        
                        let html = '<table><tr><th>ID</th><th>Название</th><th>Режиссёр</th><th>Рейтинг</th><th>Действия</th></tr>';
                        
                        movies.forEach(movie => {
                            html += `
                                <tr>
                                    <td>${movie.id}</td>
                                    <td>${movie.title}</td>
                                    <td>${movie.director}</td>
                                    <td>${movie.rating?.toFixed(1) || '0.0'}</td>
                                    <td>
                                        <button onclick="deleteMovie(${movie.id})" class="delete-btn">Удалить</button>
                                    </td>
                                </tr>
                            `;
                        });
                        
                        html += '</table>';
                        document.getElementById('moviesList').innerHTML = html;
                    } catch (error) {
                        document.getElementById('moviesList').innerHTML = '<p style="color: red;">Ошибка загрузки фильмов</p>';
                    }
                }
                
                // Загрузка отзывов
                async function loadReviews() {
                    try {
                        const response = await fetch('/reviews/');
                        if (!response.ok) throw new Error('Ошибка загрузки');
                        const reviews = await response.json();
                        
                        let html = '<table><tr><th>ID</th><th>Фильм ID</th><th>Пользователь ID</th><th>Рейтинг</th><th>Комментарий</th></tr>';
                        
                        reviews.forEach(review => {
                            html += `
                                <tr>
                                    <td>${review.id}</td>
                                    <td>${review.movie_id}</td>
                                    <td>${review.user_id}</td>
                                    <td>${review.rating}/5</td>
                                    <td>${review.comment || '—'}</td>
                                </tr>
                            `;
                        });
                        
                        html += '</table>';
                        document.getElementById('reviewsList').innerHTML = html;
                    } catch (error) {
                        document.getElementById('reviewsList').innerHTML = '<p style="color: red;">Ошибка загрузки отзывов</p>';
                    }
                }
                
                // Добавление фильма
                document.getElementById('addMovieForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const token = localStorage.getItem('access_token');
                    if (!token) {
                        alert('Требуется авторизация');
                        return;
                    }
                    
                    const formData = new FormData(this);
                    
                    try {
                        const response = await fetch('/admin/movies/', {
                            method: 'POST',
                            headers: {
                                'Authorization': 'Bearer ' + token
                            },
                            body: formData
                        });
                        
                        const result = await response.json();
                        
                        if (response.ok) {
                            document.getElementById('message').innerHTML = 
                                '<p style="color: green;">✅ Фильм добавлен!</p>';
                            this.reset();
                            loadMovies();
                        } else {
                            document.getElementById('message').innerHTML = 
                                `<p style="color: red;">❌ Ошибка: ${result.detail}</p>`;
                        }
                    } catch (error) {
                        document.getElementById('message').innerHTML = 
                            '<p style="color: red;">❌ Ошибка сети</p>';
                    }
                });
                
                // Удаление фильма
                async function deleteMovie(movieId) {
                    if (!confirm('Удалить этот фильм?')) return;
                    
                    const token = localStorage.getItem('access_token');
                    if (!token) {
                        alert('Требуется авторизация');
                        return;
                    }
                    
                    try {
                        const response = await fetch(`/admin/movies/${movieId}`, {
                            method: 'DELETE',
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (response.ok) {
                            alert('Фильм удален!');
                            loadMovies();
                        } else {
                            const error = await response.json();
                            alert('Ошибка: ' + error.detail);
                        }
                    } catch (error) {
                        alert('Ошибка сети');
                    }
                }
            </script>
        </body>
    </html>
    """)

@app.get("/login-page", response_class=HTMLResponse, summary="Страница входа")
async def login_page():
    return HTMLResponse("""
    <html>
        <head>
            <title>Вход</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }
                form { display: flex; flex-direction: column; }
                input { margin: 10px 0; padding: 10px; font-size: 16px; }
                button { background: #49cc90; color: white; padding: 10px; border: none; cursor: pointer; }
                a { color: #61affe; text-decoration: none; }
            </style>
        </head>
        <body>
            <h2>Вход в систему</h2>
            <form id="loginForm">
                <label>Имя пользователя:</label>
                <input type="text" id="username" required>
                <label>Пароль:</label>
                <input type="password" id="password" required>
                <button type="submit">Войти</button>
            </form>
            <div id="message"></div>
            <p>Нет аккаунта? <a href="/register-page">Зарегистрируйтесь</a></p>
            <p><a href="/">На главную</a></p>
            
            <script>
                document.getElementById('loginForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const username = document.getElementById('username').value;
                    const password = document.getElementById('password').value;
                    
                    try {
                        const response = await fetch('/auth/login', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ username, password })
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            localStorage.setItem('access_token', data.access_token);
                            document.getElementById('message').innerHTML = 
                                '<p style="color: green;">✅ Успешный вход!</p>';
                            setTimeout(() => window.location.href = '/', 1000);
                        } else {
                            const error = await response.json();
                            document.getElementById('message').innerHTML = 
                                `<p style="color: red;">❌ ${error.detail}</p>`;
                        }
                    } catch (error) {
                        document.getElementById('message').innerHTML = 
                            '<p style="color: red;">❌ Ошибка сети</p>';
                    }
                });
            </script>
        </body>
    </html>
    """)

@app.get("/register-page", response_class=HTMLResponse, summary="Страница регистрации")
async def register_page():
    return HTMLResponse("""
    <html>
        <head>
            <title>Регистрация</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }
                form { display: flex; flex-direction: column; }
                input { margin: 10px 0; padding: 10px; font-size: 16px; }
                button { background: #49cc90; color: white; padding: 10px; border: none; cursor: pointer; }
                a { color: #61affe; text-decoration: none; }
            </style>
        </head>
        <body>
            <h2>Регистрация</h2>
            <form id="registerForm">
                <label>Имя пользователя (мин. 3 символа):</label>
                <input type="text" id="username" required>
                <label>Email:</label>
                <input type="email" id="email" required>
                <label>Пароль (мин. 6 символов):</label>
                <input type="password" id="password" required>
                <button type="submit">Зарегистрироваться</button>
            </form>
            <div id="message"></div>
            <p>Уже есть аккаунт? <a href="/login-page">Войдите</a></p>
            <p><a href="/">На главную</a></p>
            
            <script>
                document.getElementById('registerForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const username = document.getElementById('username').value;
                    const email = document.getElementById('email').value;
                    const password = document.getElementById('password').value;
                    
                    try {
                        const response = await fetch('/auth/register', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ username, email, password })
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            document.getElementById('message').innerHTML = 
                                '<p style="color: green;">✅ Регистрация успешна! Теперь войдите в систему.</p>';
                            setTimeout(() => window.location.href = '/login-page', 2000);
                        } else {
                            const error = await response.json();
                            document.getElementById('message').innerHTML = 
                                `<p style="color: red;">❌ ${error.detail}</p>`;
                        }
                    } catch (error) {
                        document.getElementById('message').innerHTML = 
                            '<p style="color: red;">❌ Ошибка сети</p>';
                    }
                });
            </script>
        </body>
    </html>
    """)