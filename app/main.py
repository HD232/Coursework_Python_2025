from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import timedelta
import os
from app import models, auth, crud
from app.database import get_db, init_db
from app.routes import router as user_router
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

app.include_router(user_router)

os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse("""
    <html>
        <head>
            <title>Movie Tracker API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                .nav { 
                    margin: 20px 0; 
                    display: flex; 
                    gap: 10px; 
                    white-space: nowrap;
                    justify-content: flex-start;
                }
                .nav a { 
                    padding: 8px 15px; 
                    background: #3498db; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px; 
                    display: inline-block;
                    flex-shrink: 0;
                }
                .logout-btn { background: #e74c3c; }
                .movie-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
                .movie-card { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
                .movie-card img { max-width: 100%; height: 150px; object-fit: cover; }
            </style>
        </head>
        <body>
            <h1>Movie Tracker API</h1>
            <p>Система учета фильмов с рейтингами и отзывами</p>
            
            <div class="nav">
                <a href="/login-page">Войти</a>
                <a href="/register-page">Зарегистрироваться</a>
                <a href="/my-movies-page">Мои фильмы</a>
                <a href="/movies-page">Все фильмы</a>
                <a href="/docs">Документация API</a>
                <a href="#" onclick="logout()" class="logout-btn">Выйти</a>
            </div>
            
            <script>
                function isTokenExpired(token) {
                    try {
                        const payload = JSON.parse(atob(token.split('.')[1]));
                        const exp = payload.exp * 1000;
                        const now = Date.now();
                        return now >= exp;
                    } catch (e) {
                        return true;
                    }
                }
                
                const token = localStorage.getItem('access_token');
                if (token && !isTokenExpired(token)) {
                    try {
                        const payload = JSON.parse(atob(token.split('.')[1]));
                        document.body.innerHTML += '<p style="color: green; padding: 10px; background: #f0f8f0; border-radius: 4px;">Вы авторизованы как: ' + payload.sub + '</p>';
                    } catch (e) {}
                } else if (token && isTokenExpired(token)) {
                    localStorage.removeItem('access_token');
                    document.body.innerHTML += '<p style="color: red; padding: 10px; background: #f8d7da; border-radius: 4px;">Сессия истекла. Пожалуйста, войдите снова.</p>';
                }
                
                function logout() {
                    localStorage.removeItem('access_token');
                    window.location.href = '/';
                }
            </script>
        </body>
    </html>
    """)

@app.get("/register-page", response_class=HTMLResponse)
async def register_page():
    return HTMLResponse("""
    <html>
        <head>
            <title>Регистрация</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
                form { display: flex; flex-direction: column; }
                input { margin: 10px 0; padding: 10px; font-size: 16px; }
                button { background: #3498db; color: white; padding: 10px; border: none; cursor: pointer; }
                a { color: #3498db; text-decoration: none; }
                .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
                .nav { 
                    display: flex; 
                    gap: 10px; 
                    margin-bottom: 20px; 
                    white-space: nowrap;
                }
                .nav a { 
                    padding: 8px 15px; 
                    text-decoration: none; 
                    background: #3498db; 
                    color: white; 
                    border-radius: 4px;
                    flex-shrink: 0;
                }
            </style>
        </head>
        <body>
            <div class="nav">
                <a href="/">На главную</a>
            </div>
            
            <h2>Регистрация</h2>
            <form id="registerForm">
                <label>Имя пользователя (мин. 3 символа):</label>
                <input type="text" id="username" required minlength="3">
                <label>Email:</label>
                <input type="email" id="email" required>
                <label>Пароль (мин. 6 символов):</label>
                <input type="password" id="password" required minlength="6">
                <button type="submit">Зарегистрироваться</button>
            </form>
            <div id="message"></div>
            <p>Уже есть аккаунт? <a href="/login-page">Войдите</a></p>
            
            <script>
                document.getElementById('registerForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const username = document.getElementById('username').value;
                    const email = document.getElementById('email').value;
                    const password = document.getElementById('password').value;
                    
                    try {
                        const response = await fetch('/auth/register', {
                            method: 'POST',
                            headers: { 
                                'Content-Type': 'application/json',
                                'Accept': 'application/json'
                            },
                            body: JSON.stringify({ 
                                username: username, 
                                email: email, 
                                password: password 
                            })
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            document.getElementById('message').innerHTML = 
                                '<div class="message success">Регистрация успешна! Теперь войдите в систему.</div>';
                            setTimeout(() => window.location.href = '/login-page', 2000);
                        } else {
                            const error = await response.json();
                            document.getElementById('message').innerHTML = 
                                `<div class="message error">${error.detail || 'Ошибка регистрации'}</div>`;
                        }
                    } catch (error) {
                        document.getElementById('message').innerHTML = 
                            '<div class="message error">Ошибка сети</div>';
                    }
                });
            </script>
        </body>
    </html>
    """)

@app.get("/login-page", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse("""
    <html>
        <head>
            <title>Вход</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
                form { display: flex; flex-direction: column; }
                input { margin: 10px 0; padding: 10px; font-size: 16px; }
                button { background: #3498db; color: white; padding: 10px; border: none; cursor: pointer; }
                a { color: #3498db; text-decoration: none; }
                .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
                .nav { 
                    display: flex; 
                    gap: 10px; 
                    margin-bottom: 20px; 
                    white-space: nowrap;
                }
                .nav a { 
                    padding: 8px 15px; 
                    text-decoration: none; 
                    background: #3498db; 
                    color: white; 
                    border-radius: 4px;
                    flex-shrink: 0;
                }
            </style>
        </head>
        <body>
            <div class="nav">
                <a href="/">На главную</a>
            </div>
            
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
            
            <script>
                document.getElementById('loginForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const username = document.getElementById('username').value;
                    const password = document.getElementById('password').value;
                    
                    try {
                        const response = await fetch('/auth/login', {
                            method: 'POST',
                            headers: { 
                                'Content-Type': 'application/json',
                                'Accept': 'application/json'
                            },
                            body: JSON.stringify({ 
                                username: username, 
                                password: password 
                            })
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            localStorage.setItem('access_token', data.access_token);
                            setTimeout(() => window.location.href = '/my-movies-page', 1000);
                        } else {
                            const error = await response.json();
                            document.getElementById('message').innerHTML = 
                                `<div class="message error">${error.detail || 'Неверное имя пользователя или пароль'}</div>`;
                        }
                    } catch (error) {
                        document.getElementById('message').innerHTML = 
                            '<div class="message error">Ошибка сети</div>';
                    }
                });
            </script>
        </body>
    </html>
    """)

@app.get("/my-movies-page", response_class=HTMLResponse)
async def my_movies_page():
    return HTMLResponse("""
    <html>
        <head>
            <title>Мои фильмы</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; }
                .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .movies-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
                .movie-card { border: 1px solid #eee; padding: 15px; border-radius: 5px; }
                .movie-card img { max-width: 100%; height: 200px; object-fit: cover; }
                input, textarea, select { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }
                button { background: #3498db; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 10px 5px; border-radius: 4px; }
                .delete-btn { background: #e74c3c; }
                .edit-btn { background: #f39c12; }
                .nav { 
                    display: flex; 
                    gap: 10px; 
                    margin: 20px 0; 
                    white-space: nowrap;
                }
                .nav a { 
                    padding: 8px 15px; 
                    background: #3498db; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px; 
                    flex-shrink: 0;
                }
                .logout-btn { background: #e74c3c; }
                .loading { text-align: center; padding: 20px; }
                .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
                .recommended { border-left: 4px solid #f39c12; }
                .modal { display: none; position: fixed; z-index: 1; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.4); }
                .modal-content { background-color: white; margin: 10% auto; padding: 20px; border: 1px solid #888; width: 80%; max-width: 500px; border-radius: 5px; }
                .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
                .close:hover { color: black; }
            </style>
        </head>
        <body>
            <h1>Мои фильмы</h1>
            
            <div class="nav">
                <a href="/">На главную</a>
                <a href="/movies-page">Все фильмы</a>
                <a href="/docs">Документация API</a>
                <a href="#" onclick="logout()" class="logout-btn">Выйти</a>
            </div>
            
            <div id="authInfo"></div>
            
            <div class="section">
                <h2>Добавить новый фильм</h2>
                <form id="addMovieForm" enctype="multipart/form-data">
                    <input type="text" name="title" placeholder="Название" required>
                    <input type="text" name="director" placeholder="Режиссёр" required>
                    <input type="number" name="year" placeholder="Год" min="1888" max="2025">
                    <input type="text" name="genre" placeholder="Жанр">
                    <textarea name="description" placeholder="Описание" rows="3"></textarea>
                    <input type="number" name="duration" placeholder="Длительность (минут)" min="1">
                    <input type="number" name="cost" placeholder="Бюджет" step="0.01" min="0">
                    <input type="number" name="rating" placeholder="Мой рейтинг (0-10)" step="0.1" min="0" max="10">
                    <label><input type="checkbox" name="is_recommended"> Рекомендую</label>
                    <input type="file" name="photo" accept="image/*">
                    <button type="submit">Добавить в мою коллекцию</button>
                </form>
                <div id="message"></div>
            </div>
            
            <div class="section">
                <h2>Моя коллекция</h2>
                <div id="moviesList" class="loading">Загрузка...</div>
            </div>
            
            <div class="section">
                <h2>Рекомендации для вас</h2>
                <div id="recommendations" class="loading">Загрузка рекомендаций...</div>
            </div>
            
            <div id="editModal" class="modal">
                <div class="modal-content">
                    <span class="close" onclick="closeEditModal()">&times;</span>
                    <h3>Редактировать фильм</h3>
                    <form id="editMovieForm" enctype="multipart/form-data">
                        <input type="hidden" id="editMovieId" name="movie_id">
                        <input type="text" id="editTitle" name="title" placeholder="Название" required>
                        <input type="text" id="editDirector" name="director" placeholder="Режиссёр" required>
                        <input type="number" id="editYear" name="year" placeholder="Год" min="1888" max="2025">
                        <input type="text" id="editGenre" name="genre" placeholder="Жанр">
                        <textarea id="editDescription" name="description" placeholder="Описание" rows="3"></textarea>
                        <input type="number" id="editDuration" name="duration" placeholder="Длительность (минут)" min="1">
                        <input type="number" id="editCost" name="cost" placeholder="Бюджет" step="0.01" min="0">
                        <input type="number" id="editRating" name="rating" placeholder="Мой рейтинг (0-10)" step="0.1" min="0" max="10">
                        <label><input type="checkbox" id="editIsRecommended" name="is_recommended"> Рекомендую</label>
                        <input type="file" id="editPhoto" name="photo" accept="image/*">
                        <div id="currentPhoto"></div>
                        <button type="submit">Сохранить изменения</button>
                    </form>
                    <div id="editMessage"></div>
                </div>
            </div>
            
            <script>
                function isTokenExpired(token) {
                    try {
                        const payload = JSON.parse(atob(token.split('.')[1]));
                        const exp = payload.exp * 1000;
                        const now = Date.now();
                        return now >= exp;
                    } catch (e) {
                        return true;
                    }
                }
                
                const token = localStorage.getItem('access_token');
                const authInfo = document.getElementById('authInfo');
                
                if (!token || isTokenExpired(token)) {
                    if (token && isTokenExpired(token)) {
                        localStorage.removeItem('access_token');
                    }
                    authInfo.innerHTML = '<div class="message error">Вы не авторизованы. <a href="/login-page">Войдите</a> чтобы управлять своей коллекцией фильмов</div>';
                } else {
                    try {
                        const payload = JSON.parse(atob(token.split('.')[1]));
                        authInfo.innerHTML = `<div class="message success">Вы авторизованы как: ${payload.sub}</div>`;
                        loadMyMovies();
                        loadRecommendations();
                    } catch (e) {
                        authInfo.innerHTML = '<div class="message error">Неверный токен. <a href="/login-page">Войдите снова</a></div>';
                    }
                }
                
                function logout() {
                    localStorage.removeItem('access_token');
                    window.location.href = '/';
                }
                
                async function loadMyMovies() {
                    try {
                        const response = await fetch('/user/movies/', {
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (!response.ok) {
                            if (response.status === 401) {
                                if (isTokenExpired(token)) {
                                    localStorage.removeItem('access_token');
                                    window.location.href = '/login-page';
                                }
                                document.getElementById('moviesList').innerHTML = '<div class="message error">Требуется авторизация</div>';
                                return;
                            }
                            throw new Error('Ошибка загрузки');
                        }
                        
                        const movies = await response.json();
                        
                        if (movies.length === 0) {
                            document.getElementById('moviesList').innerHTML = '<p>Ваша коллекция пуста. Добавьте первый фильм!</p>';
                            return;
                        }
                        
                        let html = '<div class="movies-grid">';
                        
                        movies.forEach(movie => {
                            const movieClass = movie.is_recommended ? 'movie-card recommended' : 'movie-card';
                            const photoUrl = movie.photo_url || '/static/default_movie.jpg';
                            
                            html += `
                                <div class="${movieClass}" id="movie-${movie.id}">
                                    <h3>${movie.title}</h3>
                                    <img src="${photoUrl}" alt="${movie.title}" onerror="this.src='/static/default_movie.jpg'">
                                    <p><strong>Режиссёр:</strong> ${movie.director}</p>
                                    <p><strong>Год:</strong> ${movie.year || '—'}</p>
                                    <p><strong>Жанр:</strong> ${movie.genre || '—'}</p>
                                    <p><strong>Мой рейтинг:</strong> ${movie.rating?.toFixed(1) || '0.0'}/10</p>
                                    ${movie.is_recommended ? '<p><strong>Рекомендую этот фильм!</strong></p>' : ''}
                                    <div>
                                        <button onclick="openEditModal(${movie.id})" class="edit-btn">Редактировать</button>
                                        <button onclick="deleteMovie(${movie.id})" class="delete-btn">Удалить</button>
                                    </div>
                                </div>
                            `;
                        });
                        
                        html += '</div>';
                        document.getElementById('moviesList').innerHTML = html;
                    } catch (error) {
                        document.getElementById('moviesList').innerHTML = '<div class="message error">Ошибка загрузки фильмов</div>';
                    }
                }
                
                async function loadRecommendations() {
                    try {
                        const response = await fetch('/recommendations/?limit=6', {
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (!response.ok) throw new Error('Ошибка загрузки');
                        const recommendations = await response.json();
                        
                        if (recommendations.length === 0) {
                            document.getElementById('recommendations').innerHTML = '<p>Пока нет рекомендаций</p>';
                            return;
                        }
                        
                        let html = '<div class="movies-grid">';
                        
                        recommendations.forEach(movie => {
                            const photoUrl = movie.photo_url || '/static/default_movie.jpg';
                            
                            html += `
                                <div class="movie-card">
                                    <h3>${movie.title}</h3>
                                    <img src="${photoUrl}" alt="${movie.title}" onerror="this.src='/static/default_movie.jpg'">
                                    <p><strong>Режиссёр:</strong> ${movie.director}</p>
                                    <p><strong>Год:</strong> ${movie.year || '—'}</p>
                                    <p><strong>Рейтинг:</strong> ${movie.rating?.toFixed(1) || '0.0'}/10</p>
                                </div>
                            `;
                        });
                        
                        html += '</div>';
                        document.getElementById('recommendations').innerHTML = html;
                    } catch (error) {
                        document.getElementById('recommendations').innerHTML = '<div class="message error">Ошибка загрузки рекомендаций</div>';
                    }
                }
                
                document.getElementById('addMovieForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    if (!token || isTokenExpired(token)) {
                        if (token && isTokenExpired(token)) {
                            localStorage.removeItem('access_token');
                        }
                        alert('Сессия истекла. Пожалуйста, войдите снова.');
                        window.location.href = '/login-page';
                        return;
                    }
                    
                    const formData = new FormData(this);
                    
                    try {
                        const response = await fetch('/user/movies/', {
                            method: 'POST',
                            headers: {
                                'Authorization': 'Bearer ' + token
                            },
                            body: formData
                        });
                        
                        if (response.status === 401) {
                            if (isTokenExpired(token)) {
                                localStorage.removeItem('access_token');
                                alert('Сессия истекла. Пожалуйста, войдите снова.');
                                window.location.href = '/login-page';
                            }
                            return;
                        }
                        
                        const result = await response.json();
                        
                        if (response.ok) {
                            document.getElementById('message').innerHTML = 
                                '<div class="message success">Фильм добавлен в вашу коллекцию!</div>';
                            this.reset();
                            loadMyMovies();
                        } else {
                            document.getElementById('message').innerHTML = 
                                `<div class="message error">Ошибка: ${result.detail}</div>`;
                        }
                    } catch (error) {
                        document.getElementById('message').innerHTML = 
                            '<div class="message error">Ошибка сети</div>';
                    }
                });
                
                async function deleteMovie(movieId) {
                    if (!confirm('Удалить этот фильм из вашей коллекции?')) return;
                    
                    if (!token || isTokenExpired(token)) {
                        if (token && isTokenExpired(token)) {
                            localStorage.removeItem('access_token');
                        }
                        alert('Сессия истекла. Пожалуйста, войдите снова.');
                        window.location.href = '/login-page';
                        return;
                    }
                    
                    try {
                        const response = await fetch(`/user/movies/${movieId}`, {
                            method: 'DELETE',
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (response.ok) {
                            alert('Фильм удален из вашей коллекции!');
                            loadMyMovies();
                        } else {
                            if (response.status === 401) {
                                if (isTokenExpired(token)) {
                                    localStorage.removeItem('access_token');
                                    alert('Сессия истекла. Пожалуйста, войдите снова.');
                                    window.location.href = '/login-page';
                                }
                                return;
                            }
                            const error = await response.json();
                            alert('Ошибка: ' + error.detail);
                        }
                    } catch (error) {
                        alert('Ошибка сети');
                    }
                }
                
                async function openEditModal(movieId) {
                    if (!token || isTokenExpired(token)) {
                        if (token && isTokenExpired(token)) {
                            localStorage.removeItem('access_token');
                        }
                        alert('Сессия истекла. Пожалуйста, войдите снова.');
                        window.location.href = '/login-page';
                        return;
                    }
                    
                    try {
                        const response = await fetch(`/movies/${movieId}`);
                        if (!response.ok) throw new Error('Ошибка загрузки данных фильма');
                        
                        const movie = await response.json();
                        
                        document.getElementById('editMovieId').value = movie.id;
                        document.getElementById('editTitle').value = movie.title;
                        document.getElementById('editDirector').value = movie.director;
                        document.getElementById('editYear').value = movie.year || '';
                        document.getElementById('editGenre').value = movie.genre || '';
                        document.getElementById('editDescription').value = movie.description || '';
                        document.getElementById('editDuration').value = movie.duration || '';
                        document.getElementById('editCost').value = movie.cost || '';
                        document.getElementById('editRating').value = movie.rating || '';
                        document.getElementById('editIsRecommended').checked = movie.is_recommended || false;
                        
                        const photoUrl = movie.photo_url || '/static/default_movie.jpg';
                        document.getElementById('currentPhoto').innerHTML = `
                            <p>Текущее изображение:</p>
                            <img src="${photoUrl}" alt="${movie.title}" style="max-width: 100px; height: auto;" onerror="this.src='/static/default_movie.jpg'">
                        `;
                        
                        document.getElementById('editModal').style.display = 'block';
                    } catch (error) {
                        alert('Ошибка загрузки данных фильма');
                    }
                }
                
                function closeEditModal() {
                    document.getElementById('editModal').style.display = 'none';
                    document.getElementById('editMessage').innerHTML = '';
                }
                
                document.getElementById('editMovieForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    if (!token || isTokenExpired(token)) {
                        if (token && isTokenExpired(token)) {
                            localStorage.removeItem('access_token');
                        }
                        alert('Сессия истекла. Пожалуйста, войдите снова.');
                        window.location.href = '/login-page';
                        return;
                    }
                    
                    const movieId = document.getElementById('editMovieId').value;
                    const formData = new FormData(this);
                    
                    try {
                        const response = await fetch(`/user/movies/${movieId}`, {
                            method: 'PUT',
                            headers: {
                                'Authorization': 'Bearer ' + token
                            },
                            body: formData
                        });
                        
                        if (response.status === 401) {
                            if (isTokenExpired(token)) {
                                localStorage.removeItem('access_token');
                                alert('Сессия истекла. Пожалуйста, войдите снова.');
                                window.location.href = '/login-page';
                            }
                            return;
                        }
                        
                        const result = await response.json();
                        
                        if (response.ok) {
                            document.getElementById('editMessage').innerHTML = 
                                '<div class="message success">Фильм обновлен!</div>';
                            setTimeout(() => {
                                closeEditModal();
                                loadMyMovies();
                            }, 1500);
                        } else {
                            document.getElementById('editMessage').innerHTML = 
                                `<div class="message error">Ошибка: ${result.detail}</div>`;
                        }
                    } catch (error) {
                        document.getElementById('editMessage').innerHTML = 
                            '<div class="message error">Ошибка сети</div>';
                    }
                });
                
                window.onclick = function(event) {
                    const modal = document.getElementById('editModal');
                    if (event.target == modal) {
                        closeEditModal();
                    }
                }
            </script>
        </body>
    </html>
    """)

@app.get("/movies-page", response_class=HTMLResponse)
async def movies_page():
    return HTMLResponse("""
    <html>
        <head>
            <title>Все фильмы</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; }
                .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .movies-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
                .movie-card { border: 1px solid #eee; padding: 15px; border-radius: 5px; }
                .movie-card img { max-width: 100%; height: 200px; object-fit: cover; }
                input, textarea, select { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }
                button { background: #3498db; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 10px 5px; border-radius: 4px; }
                .nav { 
                    display: flex; 
                    gap: 10px; 
                    margin: 20px 0; 
                    white-space: nowrap;
                }
                .nav a { 
                    padding: 8px 15px; 
                    background: #3498db; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px; 
                    flex-shrink: 0;
                }
                .logout-btn { background: #e74c3c; }
                .search-container { display: flex; gap: 10px; margin: 20px 0; }
                .search-container input { flex: 1; }
                .loading { text-align: center; padding: 20px; }
                .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
                .modal { display: none; position: fixed; z-index: 1; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.4); }
                .modal-content { background-color: white; margin: 10% auto; padding: 20px; border: 1px solid #888; width: 80%; max-width: 500px; border-radius: 5px; }
                .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
                .close:hover { color: black; }
                .review-section { margin-top: 20px; border-top: 1px solid #ddd; padding-top: 15px; }
            </style>
        </head>
        <body>
            <h1>Все фильмы</h1>
            
            <div class="nav">
                <a href="/">На главную</a>
                <a href="/my-movies-page">Мои фильмы</a>
                <a href="/docs">Документация API</a>
                <a href="#" onclick="logout()" class="logout-btn">Выйти</a>
            </div>
            
            <div class="section">
                <h2>Поиск фильмов</h2>
                <div class="search-container">
                    <input type="text" id="searchTitle" placeholder="Поиск по названию...">
                    <input type="number" id="searchMinRating" placeholder="Минимальный рейтинг (0-10)" step="0.1" min="0" max="10">
                    <button onclick="searchMovies()">Поиск</button>
                    <button onclick="clearSearch()">Сбросить</button>
                </div>
            </div>
            
            <div class="section">
                <h2>Каталог фильмов</h2>
                <div id="moviesList" class="loading">Загрузка фильмов...</div>
            </div>
            
            <div id="reviewModal" class="modal">
                <div class="modal-content">
                    <span class="close" onclick="closeReviewModal()">&times;</span>
                    <h3>Добавить отзыв</h3>
                    <form id="reviewForm">
                        <input type="hidden" id="reviewMovieId" name="movie_id">
                        <p>Фильм: <span id="reviewMovieTitle"></span></p>
                        <label>Рейтинг (1-5):</label>
                        <select id="reviewRating" name="rating" required>
                            <option value="1">1 - Плохо</option>
                            <option value="2">2 - Неплохо</option>
                            <option value="3">3 - Хорошо</option>
                            <option value="4" selected>4 - Очень хорошо</option>
                            <option value="5">5 - Отлично</option>
                        </select>
                        <label>Комментарий:</label>
                        <textarea id="reviewComment" name="comment" rows="4" placeholder="Ваш отзыв..."></textarea>
                        <button type="submit">Отправить отзыв</button>
                    </form>
                    <div id="reviewMessage"></div>
                    
                    <div id="reviewsList" class="review-section">
                        <h4>Отзывы на этот фильм:</h4>
                        <div id="existingReviews">Загрузка отзывов...</div>
                    </div>
                </div>
            </div>
            
            <script>
                function isTokenExpired(token) {
                    try {
                        const payload = JSON.parse(atob(token.split('.')[1]));
                        const exp = payload.exp * 1000;
                        const now = Date.now();
                        return now >= exp;
                    } catch (e) {
                        return true;
                    }
                }
                
                const token = localStorage.getItem('access_token');
                
                function logout() {
                    localStorage.removeItem('access_token');
                    window.location.href = '/';
                }
                
                async function loadAllMovies() {
                    try {
                        const response = await fetch('/movies/?limit=100');
                        if (!response.ok) throw new Error('Ошибка загрузки');
                        
                        const movies = await response.json();
                        displayMovies(movies);
                    } catch (error) {
                        document.getElementById('moviesList').innerHTML = '<div class="message error">Ошибка загрузки фильмов</div>';
                    }
                }
                
                async function searchMovies() {
                    const title = document.getElementById('searchTitle').value;
                    const minRating = document.getElementById('searchMinRating').value;
                    
                    let url = '/movies/?limit=100';
                    if (title) url += `&title=${encodeURIComponent(title)}`;
                    if (minRating) url += `&min_rating=${minRating}`;
                    
                    try {
                        const response = await fetch(url);
                        if (!response.ok) throw new Error('Ошибка поиска');
                        
                        const movies = await response.json();
                        displayMovies(movies);
                    } catch (error) {
                        document.getElementById('moviesList').innerHTML = '<div class="message error">Ошибка поиска</div>';
                    }
                }
                
                function clearSearch() {
                    document.getElementById('searchTitle').value = '';
                    document.getElementById('searchMinRating').value = '';
                    loadAllMovies();
                }
                
                function displayMovies(movies) {
                    if (movies.length === 0) {
                        document.getElementById('moviesList').innerHTML = '<p>Фильмы не найдены</p>';
                        return;
                    }
                    
                    let html = '<div class="movies-grid">';
                    
                    movies.forEach(movie => {
                        const photoUrl = movie.photo_url || '/static/default_movie.jpg';
                        
                        html += `
                            <div class="movie-card">
                                <h3>${movie.title}</h3>
                                <img src="${photoUrl}" alt="${movie.title}" onerror="this.src='/static/default_movie.jpg'">
                                <p><strong>Режиссёр:</strong> ${movie.director}</p>
                                <p><strong>Год:</strong> ${movie.year || '—'}</p>
                                <p><strong>Жанр:</strong> ${movie.genre || '—'}</p>
                                <p><strong>Рейтинг:</strong> ${movie.rating?.toFixed(1) || '0.0'}/10</p>
                                <button onclick="openReviewModal(${movie.id}, '${movie.title.replace(/'/g, "\\'")}')">Оставить отзыв</button>
                            </div>
                        `;
                    });
                    
                    html += '</div>';
                    document.getElementById('moviesList').innerHTML = html;
                }
                
                function openReviewModal(movieId, movieTitle) {
                    if (!token || isTokenExpired(token)) {
                        if (token && isTokenExpired(token)) {
                            localStorage.removeItem('access_token');
                        }
                        alert('Для добавления отзыва необходимо авторизоваться');
                        window.location.href = '/login-page';
                        return;
                    }
                    
                    document.getElementById('reviewMovieId').value = movieId;
                    document.getElementById('reviewMovieTitle').textContent = movieTitle;
                    document.getElementById('reviewModal').style.display = 'block';
                    loadExistingReviews(movieId);
                }
                
                function closeReviewModal() {
                    document.getElementById('reviewModal').style.display = 'none';
                    document.getElementById('reviewMessage').innerHTML = '';
                }
                
                async function loadExistingReviews(movieId) {
                    try {
                        const response = await fetch(`/reviews/?movie_id=${movieId}`);
                        if (!response.ok) throw new Error('Ошибка загрузки отзывов');
                        
                        const reviews = await response.json();
                        let html = '';
                        
                        if (reviews.length === 0) {
                            html = '<p>Пока нет отзывов. Будьте первым!</p>';
                        } else {
                            reviews.forEach(review => {
                                html += `
                                    <div style="border-bottom: 1px solid #eee; padding: 10px 0;">
                                        <p><strong>Рейтинг:</strong> ${review.rating}/5</p>
                                        <p><strong>Комментарий:</strong> ${review.comment || 'Без комментария'}</p>
                                        <p style="font-size: 0.9em; color: #666;">Добавлен: ${new Date(review.created_at).toLocaleDateString()}</p>
                                    </div>
                                `;
                            });
                        }
                        
                        document.getElementById('existingReviews').innerHTML = html;
                    } catch (error) {
                        document.getElementById('existingReviews').innerHTML = '<p>Ошибка загрузки отзывов</p>';
                    }
                }
                
                document.getElementById('reviewForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    if (!token || isTokenExpired(token)) {
                        if (token && isTokenExpired(token)) {
                            localStorage.removeItem('access_token');
                        }
                        alert('Сессия истекла. Пожалуйста, войдите снова.');
                        window.location.href = '/login-page';
                        return;
                    }
                    
                    const movieId = document.getElementById('reviewMovieId').value;
                    const rating = document.getElementById('reviewRating').value;
                    const comment = document.getElementById('reviewComment').value;
                    
                    try {
                        const response = await fetch('/reviews/', {
                            method: 'POST',
                            headers: {
                                'Authorization': 'Bearer ' + token,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                movie_id: parseInt(movieId),
                                rating: parseInt(rating),
                                comment: comment
                            })
                        });
                        
                        if (response.status === 401) {
                            if (isTokenExpired(token)) {
                                localStorage.removeItem('access_token');
                                alert('Сессия истекла. Пожалуйста, войдите снова.');
                                window.location.href = '/login-page';
                            }
                            return;
                        }
                        
                        const result = await response.json();
                        
                        if (response.ok) {
                            document.getElementById('reviewMessage').innerHTML = 
                                '<div class="message success">Отзыв добавлен!</div>';
                            setTimeout(() => {
                                closeReviewModal();
                                loadExistingReviews(movieId);
                            }, 1500);
                        } else {
                            document.getElementById('reviewMessage').innerHTML = 
                                `<div class="message error">Ошибка: ${result.detail}</div>`;
                        }
                    } catch (error) {
                        document.getElementById('reviewMessage').innerHTML = 
                            '<div class="message error">Ошибка сети</div>';
                    }
                });
                
                window.onclick = function(event) {
                    const modal = document.getElementById('reviewModal');
                    if (event.target == modal) {
                        closeReviewModal();
                    }
                }
                
                loadAllMovies();
            </script>
        </body>
    </html>
    """)


@app.post("/auth/register", response_model=models.UserResponse, 
        summary="Регистрация пользователя",
        description="Создает нового пользователя в системе с уникальным username и email.")
async def register(user: models.UserCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_user(db, user)


@app.post("/auth/login", response_model=models.Token,
        summary="Вход в систему",
        description="Аутентификация пользователя. Возвращает JWT токен для доступа к защищенным эндпоинтам.")
async def login(user_data: models.UserLogin, db: AsyncSession = Depends(get_db)):
    user = await auth.authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    from datetime import datetime
    user.last_login = datetime.utcnow()
    await db.commit()
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/movies/", response_model=List[models.MovieResponse],
        summary="Получить все фильмы",
        description="Возвращает список всех фильмов.")
async def read_movies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    genre: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None, ge=0.0, le=10.0),
    title: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.future import select
    from app.schemas import MovieDB
    
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


@app.get("/movies/{movie_id}", response_model=models.MovieResponse,
        summary="Получить фильм по ID",
        description="Возвращает информацию о фильме по его ID.")
async def read_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    return await crud.get_movie(db, movie_id)


@app.post("/reviews/", response_model=models.ReviewResponse,
        summary="Создать отзыв",
        description="Создает новый отзыв на фильм. Пользователь может оставить только один отзыв на фильм.")
async def create_review(
    review: models.ReviewCreate,
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await crud.create_review(db, review, current_user.id)


@app.get("/reviews/", response_model=List[models.ReviewResponse],
        summary="Получить отзывы",
        description="Возвращает список отзывов.")
async def read_reviews(
    movie_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    if movie_id:
        return await crud.get_movie_reviews(db, movie_id)
    from sqlalchemy.future import select
    from app.schemas import ReviewDB
    result = await db.execute(
        select(ReviewDB).offset(skip).limit(limit)
    )
    return result.scalars().all()