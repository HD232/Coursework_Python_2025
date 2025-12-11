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
                    flex-wrap: wrap;
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
                .admin-link { background: #e74c3c; }
                .logout-btn { background: #e74c3c; }
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
                <a href="/my-reviews-page">Мои отзывы</a>
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
                        
                        const nav = document.querySelector('.nav');
                        const adminLink = document.createElement('a');
                        adminLink.href = '/admin-panel';
                        adminLink.className = 'admin-link';
                        adminLink.textContent = 'Панель администратора';
                        nav.appendChild(adminLink);
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
                }
            </style>
        </head>
        <body>
            <div class="nav">
                <a href="/">На главную</a>
            </div>
            
            <h2>Регистрация</h2>
            <form id="registerForm">
                <label>Имя пользователя:</label>
                <input type="text" id="username" required minlength="3">
                <label>Email:</label>
                <input type="email" id="email" required>
                <label>Пароль:</label>
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
                                'Content-Type': 'application/json'
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
                                '<div class="message success">Регистрация успешна!</div>';
                            setTimeout(() => window.location.href = '/login-page', 2000);
                        } else {
                            const error = await response.json();
                            document.getElementById('message').innerHTML = 
                                `<div class="message error">${error.detail || 'Ошибка'}</div>`;
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
                .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
                .nav { 
                    display: flex; 
                    gap: 10px; 
                    margin-bottom: 20px; 
                }
                .nav a { 
                    padding: 8px 15px; 
                    text-decoration: none; 
                    background: #3498db; 
                    color: white; 
                    border-radius: 4px;
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
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ 
                                username: username, 
                                password: password 
                            })
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            localStorage.setItem('access_token', data.access_token);
                            window.location.href = '/my-movies-page';
                        } else {
                            const error = await response.json();
                            document.getElementById('message').innerHTML = 
                                `<div class="message error">${error.detail || 'Ошибка'}</div>`;
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
                    flex-wrap: wrap;
                }
                .nav a { 
                    padding: 8px 15px; 
                    background: #3498db; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px; 
                }
                .logout-btn { background: #e74c3c; }
                .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
                .recommended { border-left: 4px solid #f39c12; }
                .modal { display: none; position: fixed; z-index: 1; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.4); }
                .modal-content { background-color: white; margin: 10% auto; padding: 20px; border: 1px solid #888; width: 80%; max-width: 500px; border-radius: 5px; }
                .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>Мои фильмы</h1>
            
            <div class="nav">
                <a href="/">На главную</a>
                <a href="/movies-page">Все фильмы</a>
                <a href="/docs">Документация API</a>
                <a href="/my-reviews-page">Мои отзывы</a>
                <a href="#" onclick="logout()" class="logout-btn">Выйти</a>
            </div>
            
            <div id="authInfo"></div>
            
            <div class="section">
                <h2>Добавить фильм</h2>
                <form id="addMovieForm" enctype="multipart/form-data">
                    <input type="text" name="title" placeholder="Название" required>
                    <input type="text" name="director" placeholder="Режиссёр" required>
                    <input type="number" name="year" placeholder="Год" min="1888" max="2025">
                    <input type="text" name="genre" placeholder="Жанр">
                    <textarea name="description" placeholder="Описание" rows="3"></textarea>
                    <input type="number" name="duration" placeholder="Длительность" min="1">
                    <input type="number" name="cost" placeholder="Бюджет" step="0.01" min="0">
                    <input type="number" name="rating" placeholder="Рейтинг" step="0.1" min="0" max="10">
                    <label><input type="checkbox" name="is_recommended"> Рекомендую</label>
                    <input type="file" name="photo" accept="image/*">
                    <button type="submit">Добавить</button>
                </form>
                <div id="message"></div>
            </div>
            
            <div class="section">
                <h2>Моя коллекция</h2>
                <div id="moviesList">Загрузка...</div>
            </div>
            
            <div class="section">
                <h2>Рекомендации</h2>
                <div id="recommendations">Загрузка...</div>
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
                        <input type="number" id="editDuration" name="duration" placeholder="Длительность" min="1">
                        <input type="number" id="editCost" name="cost" placeholder="Бюджет" step="0.01" min="0">
                        <input type="number" id="editRating" name="rating" placeholder="Рейтинг" step="0.1" min="0" max="10">
                        <label><input type="checkbox" id="editIsRecommended" name="is_recommended"> Рекомендую</label>
                        <input type="file" id="editPhoto" name="photo" accept="image/*">
                        <div id="currentPhoto"></div>
                        <button type="submit">Сохранить</button>
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
                    authInfo.innerHTML = '<div class="message error">Требуется авторизация</div>';
                } else {
                    loadMyMovies();
                    loadRecommendations();
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
                            throw new Error('Ошибка загрузки');
                        }
                        
                        const movies = await response.json();
                        
                        if (movies.length === 0) {
                            document.getElementById('moviesList').innerHTML = '<p>Коллекция пуста</p>';
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
                                    <p><strong>Рейтинг:</strong> ${movie.rating?.toFixed(1) || '0.0'}/10</p>
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
                        document.getElementById('moviesList').innerHTML = '<div class="message error">Ошибка загрузки</div>';
                    }
                }
                
                async function loadRecommendations() {
                    try {
                        const response = await fetch('/recommendations/?limit=6', {
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (!response.ok) throw new Error('Ошибка');
                        const recommendations = await response.json();
                        
                        if (recommendations.length === 0) {
                            document.getElementById('recommendations').innerHTML = '<p>Нет рекомендаций</p>';
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
                        document.getElementById('recommendations').innerHTML = '<div class="message error">Ошибка</div>';
                    }
                }
                
                document.getElementById('addMovieForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    
                    try {
                        const response = await fetch('/user/movies/', {
                            method: 'POST',
                            headers: {
                                'Authorization': 'Bearer ' + token
                            },
                            body: formData
                        });
                        
                        const result = await response.json();
                        
                        if (response.ok) {
                            document.getElementById('message').innerHTML = 
                                '<div class="message success">Фильм добавлен</div>';
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
                    if (!confirm('Удалить фильм?')) return;
                    
                    try {
                        const response = await fetch(`/user/movies/${movieId}`, {
                            method: 'DELETE',
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (response.ok) {
                            alert('Фильм удален');
                            loadMyMovies();
                        } else {
                            const error = await response.json();
                            alert('Ошибка: ' + error.detail);
                        }
                    } catch (error) {
                        alert('Ошибка сети');
                    }
                }
                
                async function openEditModal(movieId) {
                    try {
                        const response = await fetch(`/movies/${movieId}`);
                        if (!response.ok) throw new Error('Ошибка');
                        
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
                            <img src="${photoUrl}" alt="${movie.title}" style="max-width: 100px;" onerror="this.src='/static/default_movie.jpg'">
                        `;
                        
                        document.getElementById('editModal').style.display = 'block';
                    } catch (error) {
                        alert('Ошибка загрузки');
                    }
                }
                
                function closeEditModal() {
                    document.getElementById('editModal').style.display = 'none';
                }
                
                document.getElementById('editMovieForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
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
                        
                        const result = await response.json();
                        
                        if (response.ok) {
                            document.getElementById('editMessage').innerHTML = 
                                '<div class="message success">Фильм обновлен</div>';
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
                    flex-wrap: wrap;
                }
                .nav a { 
                    padding: 8px 15px; 
                    background: #3498db; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px; 
                }
                .search-container { display: flex; gap: 10px; margin: 20px 0; }
                .search-container input { flex: 1; }
                .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
                .modal { display: none; position: fixed; z-index: 1; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.4); }
                .modal-content { background-color: white; margin: 10% auto; padding: 20px; border: 1px solid #888; width: 80%; max-width: 500px; border-radius: 5px; }
                .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>Все фильмы</h1>
            
            <div class="nav">
                <a href="/">На главную</a>
                <a href="/my-movies-page">Мои фильмы</a>
                <a href="/docs">Документация API</a>
                <a href="/my-reviews-page">Мои отзывы</a>
            </div>
            
            <div class="section">
                <h2>Поиск</h2>
                <div class="search-container">
                    <input type="text" id="searchTitle" placeholder="Поиск по названию...">
                    <input type="number" id="searchMinRating" placeholder="Мин. рейтинг" step="0.1" min="0" max="10">
                    <button onclick="searchMovies()">Поиск</button>
                    <button onclick="clearSearch()">Сбросить</button>
                </div>
            </div>
            
            <div class="section">
                <h2>Каталог фильмов</h2>
                <div id="moviesList">Загрузка...</div>
            </div>
            
            <div id="reviewModal" class="modal">
                <div class="modal-content">
                    <span class="close" onclick="closeReviewModal()">&times;</span>
                    <h3>Добавить отзыв</h3>
                    <form id="reviewForm">
                        <input type="hidden" id="reviewMovieId" name="movie_id">
                        <p>Фильм: <span id="reviewMovieTitle"></span></p>
                        <label>Рейтинг:</label>
                        <select id="reviewRating" name="rating" required>
                            <option value="1">1</option>
                            <option value="2">2</option>
                            <option value="3">3</option>
                            <option value="4" selected>4</option>
                            <option value="5">5</option>
                        </select>
                        <label>Комментарий:</label>
                        <textarea id="reviewComment" name="comment" rows="4" placeholder="Ваш отзыв..."></textarea>
                        <button type="submit">Отправить</button>
                    </form>
                    <div id="reviewMessage"></div>
                </div>
            </div>
            
            <script>
                const token = localStorage.getItem('access_token');
                
                async function loadAllMovies() {
                    try {
                        const response = await fetch('/movies/?limit=100');
                        if (!response.ok) throw new Error('Ошибка');
                        
                        const movies = await response.json();
                        displayMovies(movies);
                    } catch (error) {
                        document.getElementById('moviesList').innerHTML = '<div class="message error">Ошибка</div>';
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
                        if (!response.ok) throw new Error('Ошибка');
                        
                        const movies = await response.json();
                        displayMovies(movies);
                    } catch (error) {
                        document.getElementById('moviesList').innerHTML = '<div class="message error">Ошибка</div>';
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
                                <p><strong>Рейтинг:</strong> ${movie.rating?.toFixed(1) || '0.0'}/10</p>
                                <button onclick="openReviewModal(${movie.id}, '${movie.title.replace(/'/g, "\\'")}')">Оставить отзыв</button>
                            </div>
                        `;
                    });
                    
                    html += '</div>';
                    document.getElementById('moviesList').innerHTML = html;
                }
                
                function openReviewModal(movieId, movieTitle) {
                    if (!token) {
                        alert('Требуется авторизация');
                        window.location.href = '/login-page';
                        return;
                    }
                    
                    document.getElementById('reviewMovieId').value = movieId;
                    document.getElementById('reviewMovieTitle').textContent = movieTitle;
                    document.getElementById('reviewModal').style.display = 'block';
                }
                
                function closeReviewModal() {
                    document.getElementById('reviewModal').style.display = 'none';
                }
                
                document.getElementById('reviewForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
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
                        
                        const result = await response.json();
                        
                        if (response.ok) {
                            document.getElementById('reviewMessage').innerHTML = 
                                '<div class="message success">Отзыв добавлен</div>';
                            setTimeout(() => {
                                closeReviewModal();
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

@app.get("/admin-panel", response_class=HTMLResponse)
async def admin_panel_page():
    return HTMLResponse("""
    <html>
        <head>
            <title>Панель администратора</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; }
                .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
                .card { border: 1px solid #eee; padding: 15px; border-radius: 5px; }
                button { background: #3498db; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 5px; border-radius: 4px; }
                .delete-btn { background: #e74c3c; }
                .nav { 
                    display: flex; 
                    gap: 10px; 
                    margin: 20px 0; 
                    flex-wrap: wrap;
                }
                .nav a { 
                    padding: 8px 15px; 
                    background: #3498db; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px; 
                }
                .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
                .tab { overflow: hidden; border: 1px solid #ccc; background-color: #f1f1f1; }
                .tab button { background-color: inherit; float: left; border: none; outline: none; cursor: pointer; padding: 14px 16px; transition: 0.3s; }
                .tab button:hover { background-color: #ddd; }
                .tab button.active { background-color: #ccc; }
                .tabcontent { display: none; padding: 6px 12px; border: 1px solid #ccc; border-top: none; }
            </style>
        </head>
        <body>
            <h1>Панель администратора</h1>
            
            <div class="nav">
                <a href="/">На главную</a>
            </div>
            
            <div id="authInfo"></div>
            
            <div class="tab">
                <button class="tablinks" onclick="openTab(event, 'Reviews')">Отзывы</button>
                <button class="tablinks" onclick="openTab(event, 'Movies')">Фильмы</button>
                <button class="tablinks" onclick="openTab(event, 'Users')">Пользователи</button>
            </div>
            
            <div id="Reviews" class="tabcontent">
                <h3>Все отзывы</h3>
                <div id="allReviews">Загрузка...</div>
            </div>
            
            <div id="Movies" class="tabcontent">
                <h3>Все фильмы</h3>
                <div id="allMovies">Загрузка...</div>
            </div>
            
            <div id="Users" class="tabcontent">
                <h3>Все пользователи</h3>
                <div id="allUsers">Загрузка...</div>
            </div>
            
            <script>
                const token = localStorage.getItem('access_token');
                const authInfo = document.getElementById('authInfo');
                
                if (!token) {
                    authInfo.innerHTML = '<div class="message error">Доступ запрещен</div>';
                } else {
                    loadAllReviews();
                    document.getElementsByClassName('tablinks')[0].click();
                }
                
                async function loadAllReviews() {
                    try {
                        const response = await fetch('/admin/reviews/?limit=50', {
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (!response.ok) throw new Error('Ошибка');
                        
                        const reviews = await response.json();
                        
                        if (reviews.length === 0) {
                            document.getElementById('allReviews').innerHTML = '<p>Нет отзывов</p>';
                            return;
                        }
                        
                        let html = '<div class="grid">';
                        
                        reviews.forEach(review => {
                            html += `
                                <div class="card">
                                    <h4>Отзыв #${review.id}</h4>
                                    <p><strong>Фильм ID:</strong> ${review.movie_id}</p>
                                    <p><strong>Автор ID:</strong> ${review.user_id}</p>
                                    <p><strong>Рейтинг:</strong> ${review.rating}/5</p>
                                    <p><strong>Дата:</strong> ${new Date(review.created_at).toLocaleString()}</p>
                                    <button onclick="deleteReview(${review.id})" class="delete-btn">Удалить</button>
                                </div>
                            `;
                        });
                        
                        html += '</div>';
                        document.getElementById('allReviews').innerHTML = html;
                    } catch (error) {
                        document.getElementById('allReviews').innerHTML = '<div class="message error">Ошибка</div>';
                    }
                }
                
                async function loadAllMovies() {
                    try {
                        const response = await fetch('/admin/movies/?limit=50', {
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (!response.ok) throw new Error('Ошибка');
                        
                        const movies = await response.json();
                        
                        if (movies.length === 0) {
                            document.getElementById('allMovies').innerHTML = '<p>Нет фильмов</p>';
                            return;
                        }
                        
                        let html = '<div class="grid">';
                        
                        movies.forEach(movie => {
                            const photoUrl = movie.photo_url || '/static/default_movie.jpg';
                            
                            html += `
                                <div class="card">
                                    <h4>${movie.title}</h4>
                                    <img src="${photoUrl}" alt="${movie.title}" style="max-width: 100%; height: 150px; object-fit: cover;" onerror="this.src='/static/default_movie.jpg'">
                                    <p><strong>ID:</strong> ${movie.id}</p>
                                    <p><strong>Рейтинг:</strong> ${movie.rating?.toFixed(1) || '0.0'}/10</p>
                                    <button onclick="deleteMovie(${movie.id})" class="delete-btn">Удалить</button>
                                </div>
                            `;
                        });
                        
                        html += '</div>';
                        document.getElementById('allMovies').innerHTML = html;
                    } catch (error) {
                        document.getElementById('allMovies').innerHTML = '<div class="message error">Ошибка</div>';
                    }
                }
                
                async function loadAllUsers() {
                    try {
                        const response = await fetch('/admin/users/?limit=50', {
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (!response.ok) throw new Error('Ошибка');
                        
                        const users = await response.json();
                        
                        if (users.length === 0) {
                            document.getElementById('allUsers').innerHTML = '<p>Нет пользователей</p>';
                            return;
                        }
                        
                        let html = '<div class="grid">';
                        
                        users.forEach(user => {
                            html += `
                                <div class="card">
                                    <h4>${user.username}</h4>
                                    <p><strong>ID:</strong> ${user.id}</p>
                                    <p><strong>Email:</strong> ${user.email}</p>
                                    <p><strong>Админ:</strong> ${user.is_admin ? 'Да' : 'Нет'}</p>
                                </div>
                            `;
                        });
                        
                        html += '</div>';
                        document.getElementById('allUsers').innerHTML = html;
                    } catch (error) {
                        document.getElementById('allUsers').innerHTML = '<div class="message error">Ошибка</div>';
                    }
                }
                
                async function deleteReview(reviewId) {
                    if (!confirm('Удалить отзыв?')) return;
                    
                    try {
                        const response = await fetch(`/admin/reviews/${reviewId}`, {
                            method: 'DELETE',
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (response.ok) {
                            alert('Отзыв удален');
                            loadAllReviews();
                        } else {
                            const error = await response.json();
                            alert('Ошибка: ' + error.detail);
                        }
                    } catch (error) {
                        alert('Ошибка сети');
                    }
                }
                
                async function deleteMovie(movieId) {
                    if (!confirm('Удалить фильм?')) return;
                    
                    try {
                        const response = await fetch(`/admin/movies/${movieId}`, {
                            method: 'DELETE',
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (response.ok) {
                            alert('Фильм удален');
                            loadAllMovies();
                        } else {
                            const error = await response.json();
                            alert('Ошибка: ' + error.detail);
                        }
                    } catch (error) {
                        alert('Ошибка сети');
                    }
                }
                
                function openTab(evt, tabName) {
                    var i, tabcontent, tablinks;
                    tabcontent = document.getElementsByClassName("tabcontent");
                    for (i = 0; i < tabcontent.length; i++) {
                        tabcontent[i].style.display = "none";
                    }
                    tablinks = document.getElementsByClassName("tablinks");
                    for (i = 0; i < tablinks.length; i++) {
                        tablinks[i].className = tablinks[i].className.replace(" active", "");
                    }
                    document.getElementById(tabName).style.display = "block";
                    evt.currentTarget.className += " active";
                    
                    if (tabName === 'Reviews') loadAllReviews();
                    if (tabName === 'Movies') loadAllMovies();
                    if (tabName === 'Users') loadAllUsers();
                }
            </script>
        </body>
    </html>
    """)

@app.get("/my-reviews-page", response_class=HTMLResponse)
async def my_reviews_page():
    return HTMLResponse("""
    <html>
        <head>
            <title>Мои отзывы</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; }
                .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .reviews-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
                .review-card { border: 1px solid #eee; padding: 15px; border-radius: 5px; }
                textarea, select { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }
                button { background: #3498db; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 5px; border-radius: 4px; }
                .edit-btn { background: #f39c12; }
                .delete-btn { background: #e74c3c; }
                .save-btn { background: #27ae60; }
                .nav { 
                    display: flex; 
                    gap: 10px; 
                    margin: 20px 0; 
                    flex-wrap: wrap;
                }
                .nav a { 
                    padding: 8px 15px; 
                    background: #3498db; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px; 
                }
                .message { padding: 10px; margin: 10px 0; border-radius: 4px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
            </style>
        </head>
        <body>
            <h1>Мои отзывы</h1>
            
            <div class="nav">
                <a href="/">На главную</a>
                <a href="/my-movies-page">Мои фильмы</a>
                <a href="/movies-page">Все фильмы</a>
                <a href="/docs">Документация API</a>
            </div>
            
            <div id="authInfo"></div>
            
            <div class="section">
                <h2>Мои отзывы</h2>
                <div id="reviewsList">Загрузка...</div>
            </div>
            
            <script>
                const token = localStorage.getItem('access_token');
                const authInfo = document.getElementById('authInfo');
                
                if (!token) {
                    authInfo.innerHTML = '<div class="message error">Требуется авторизация</div>';
                } else {
                    loadMyReviews();
                }
                
                async function loadMyReviews() {
                    try {
                        const response = await fetch('/user/reviews/', {
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (!response.ok) throw new Error('Ошибка');
                        
                        const reviews = await response.json();
                        
                        if (reviews.length === 0) {
                            document.getElementById('reviewsList').innerHTML = '<p>Нет отзывов</p>';
                            return;
                        }
                        
                        let html = '<div class="reviews-grid">';
                        
                        reviews.forEach(review => {
                            html += `
                                <div class="review-card" id="review-${review.id}">
                                    <h3>Фильм ID: ${review.movie_id}</h3>
                                    <div id="review-view-${review.id}">
                                        <p><strong>Рейтинг:</strong> ${review.rating}/5</p>
                                        <p><strong>Комментарий:</strong> ${review.comment || 'Без комментария'}</p>
                                        <p><strong>Дата:</strong> ${new Date(review.created_at).toLocaleDateString()}</p>
                                        <button onclick="startEditReview(${review.id})" class="edit-btn">Редактировать</button>
                                        <button onclick="deleteMyReview(${review.id})" class="delete-btn">Удалить</button>
                                    </div>
                                    
                                    <div id="review-edit-${review.id}" style="display: none;">
                                        <form onsubmit="saveReviewEdit(${review.id}); return false;">
                                            <label>Рейтинг:</label>
                                            <select id="edit-rating-${review.id}" required>
                                                <option value="1" ${review.rating === 1 ? 'selected' : ''}>1</option>
                                                <option value="2" ${review.rating === 2 ? 'selected' : ''}>2</option>
                                                <option value="3" ${review.rating === 3 ? 'selected' : ''}>3</option>
                                                <option value="4" ${review.rating === 4 ? 'selected' : ''}>4</option>
                                                <option value="5" ${review.rating === 5 ? 'selected' : ''}>5</option>
                                            </select>
                                            <label>Комментарий:</label>
                                            <textarea id="edit-comment-${review.id}" rows="3">${review.comment || ''}</textarea>
                                            <button type="submit" class="save-btn">Сохранить</button>
                                            <button type="button" onclick="cancelEditReview(${review.id})">Отмена</button>
                                        </form>
                                    </div>
                                </div>
                            `;
                        });
                        
                        html += '</div>';
                        document.getElementById('reviewsList').innerHTML = html;
                    } catch (error) {
                        document.getElementById('reviewsList').innerHTML = '<div class="message error">Ошибка</div>';
                    }
                }
                
                function startEditReview(reviewId) {
                    document.getElementById(`review-view-${reviewId}`).style.display = 'none';
                    document.getElementById(`review-edit-${reviewId}`).style.display = 'block';
                }
                
                function cancelEditReview(reviewId) {
                    document.getElementById(`review-view-${reviewId}`).style.display = 'block';
                    document.getElementById(`review-edit-${reviewId}`).style.display = 'none';
                }
                
                async function saveReviewEdit(reviewId) {
                    const rating = document.getElementById(`edit-rating-${reviewId}`).value;
                    const comment = document.getElementById(`edit-comment-${reviewId}`).value;
                    
                    try {
                        const response = await fetch(`/user/reviews/${reviewId}`, {
                            method: 'PUT',
                            headers: {
                                'Authorization': 'Bearer ' + token,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                rating: parseInt(rating),
                                comment: comment
                            })
                        });
                        
                        if (response.ok) {
                            alert('Отзыв обновлен');
                            loadMyReviews();
                        } else {
                            const error = await response.json();
                            alert('Ошибка: ' + error.detail);
                        }
                    } catch (error) {
                        alert('Ошибка сети');
                    }
                }
                
                async function deleteMyReview(reviewId) {
                    if (!confirm('Удалить отзыв?')) return;
                    
                    try {
                        const response = await fetch(`/user/reviews/${reviewId}`, {
                            method: 'DELETE',
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        
                        if (response.ok) {
                            alert('Отзыв удален');
                            loadMyReviews();
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

@app.post("/auth/register", response_model=models.UserResponse)
async def register(user: models.UserCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_user(db, user)

@app.post("/auth/login", response_model=models.Token)
async def login(user_data: models.UserLogin, db: AsyncSession = Depends(get_db)):
    user = await auth.authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные данные"
        )
    
    from datetime import datetime
    user.last_login = datetime.utcnow()
    await db.commit()
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/movies/", response_model=List[models.MovieResponse])
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

@app.get("/movies/{movie_id}", response_model=models.MovieResponse)
async def read_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    return await crud.get_movie(db, movie_id)

@app.post("/reviews/", response_model=models.ReviewResponse)
async def create_review(
    review: models.ReviewCreate,
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await crud.create_review(db, review, current_user.id)

@app.get("/reviews/", response_model=List[models.ReviewResponse])
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

@app.get("/admin/reviews/", response_model=List[models.ReviewResponse])
async def get_all_reviews_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    movie_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    current_user = Depends(auth.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.future import select
    from app.schemas import ReviewDB
    
    query = select(ReviewDB)
    
    if movie_id:
        query = query.where(ReviewDB.movie_id == movie_id)
    
    if user_id:
        query = query.where(ReviewDB.user_id == user_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@app.delete("/admin/reviews/{review_id}")
async def delete_any_review(
    review_id: int,
    current_user = Depends(auth.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    return await crud.delete_review(db, review_id)

@app.get("/admin/movies/", response_model=List[models.MovieResponse])
async def get_all_movies_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user = Depends(auth.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.future import select
    from app.schemas import MovieDB
    
    query = select(MovieDB).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@app.delete("/admin/movies/{movie_id}")
async def delete_any_movie(
    movie_id: int,
    current_user = Depends(auth.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    return await crud.delete_movie(db, movie_id)

@app.get("/admin/users/", response_model=List[models.UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user = Depends(auth.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.future import select
    from app.schemas import UserDB
    
    query = select(UserDB).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@app.get("/user/reviews/", response_model=List[models.ReviewResponse])
async def get_my_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await crud.get_user_reviews(db, current_user.id)

@app.get("/user/reviews/{review_id}", response_model=models.ReviewResponse)
async def get_my_review(
    review_id: int,
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    review = await crud.get_review(db, review_id)
    
    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Не ваш отзыв"
        )
    
    return review

@app.put("/user/reviews/{review_id}", response_model=models.ReviewResponse)
async def update_my_review(
    review_id: int,
    review_update: models.ReviewUpdate,
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    review = await crud.get_review(db, review_id)
    
    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Не ваш отзыв"
        )
    
    return await crud.update_review(db, review_id, review_update)

@app.delete("/user/reviews/{review_id}")
async def delete_my_review(
    review_id: int,
    current_user = Depends(auth.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    review = await crud.get_review(db, review_id)
    
    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Не ваш отзыв"
        )
    
    return await crud.delete_review(db, review_id)