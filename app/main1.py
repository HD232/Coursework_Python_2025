from fastapi import FastAPI, File, UploadFile, Form, Response, Cookie, Depends, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.models import Movietop, MOVIES, UserProfile, UserLogin, Token

from uuid import uuid4
from datetime import datetime, timedelta
import shutil
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

SECRET_KEY = "secret-keyz_123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 30

security = HTTPBearer()

fake_users_db = {
    "admin": "123",
    "user": "456"
}

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный токен",
            )
        return username
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия токена истек",
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )

@app.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    username = user_data.username
    password = user_data.password
    
    if username not in fake_users_db or fake_users_db[username] != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(seconds=ACCESS_TOKEN_EXPIRE)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")

@app.get("/login")
def login_form():
    return HTMLResponse("""
    <h2>Вход в систему</h2>
    <form method="post" action="/login_form">
        <label>Имя пользователя:</label>
        <input type="text" name="username" required><br><br>
        <label>Пароль:</label>
        <input type="password" name="password" required><br><br>
        <button type="submit">Войти</button>
    </form>
    <p><a href="/">На главную</a></p>
    """)

@app.post("/login_form")
async def login_form_post(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    if username not in fake_users_db or fake_users_db[username] != password:
        return HTMLResponse("""
        <h2>Ошибка: Неверное имя пользователя или пароль</h2>
        <a href="/login">Попробовать снова</a><br>
        <a href="/">На главную</a>
        """)
    
    access_token_expires = timedelta(seconds=ACCESS_TOKEN_EXPIRE)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    return HTMLResponse(f"""
    <h2>Успешный вход!</h2>
    <p>Токен сохранен. Теперь вы можете:</p>
    <p><a href="/add_film_form">Добавить фильм</a></p>
    
    <script>
        localStorage.setItem('jwt_token', '{access_token}');
    </script>

    <br>
    <a href="/">На главную</a>
    """)

@app.get("/exit")
async def exit():
    return HTMLResponse("""
    <h3>Выход из системы</h3>
    <script>
        localStorage.removeItem('jwt_token');
    </script>
    <p>Токен удален. <a href="/">На главную</a></p>
    """)

@app.get("/add_film_form")
def add_film_form():
    return HTMLResponse("""
    <h2>Добавить фильм (защищено JWT)</h2>
    <div id="userInfo"></div>
    
    <form id="filmForm" enctype="multipart/form-data">
        <label>Название:</label>
        <input type="text" name="name" id="name" required><br><br>
        
        <label>Режиссёр:</label>
        <input type="text" name="director" id="director" required><br><br>
        
        <label>Стоимость:</label>
        <input type="number" name="cost" id="cost" required><br><br>
        
        <label>
            <input type="checkbox" name="good" id="good" value="true">
            Рекомендуется
        </label><br><br>
        
        <label>Обложка:</label>
        <input type="file" name="photo" id="photo" accept="image/*"><br><br>
        
        <button type="submit">Добавить фильм</button>
    </form>
    
    <div id="message"></div>
    
    <p><a href="/logout">Выйти</a> | <a href="/">На главную</a></p>

    <script>
        const token = localStorage.getItem('jwt_token');
        const userInfo = document.getElementById('userInfo');
        const messageDiv = document.getElementById('message');
        
        if (!token) {
            userInfo.innerHTML = '<p>Ошибка: Токен не найден. <a href="/login">Войдите снова</a></p>';
            document.getElementById('filmForm').style.display = 'none';
        } else {
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                userInfo.innerHTML = `<p>Пользователь: <strong>${payload.sub}</strong></p>`;
            } catch (e) {
                userInfo.innerHTML = '<p>Пользователь: Неизвестен</p>';
            }
        }

        document.getElementById('filmForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const token = localStorage.getItem('jwt_token');
            if (!token) {
                messageDiv.innerHTML = '<p style="color: red;">Ошибка: Токен не найден</p>';
                return;
            }
            
            const formData = new FormData();
            formData.append('name', document.getElementById('name').value);
            formData.append('director', document.getElementById('director').value);
            formData.append('cost', document.getElementById('cost').value);
            formData.append('good', document.getElementById('good').checked);
            
            const photoFile = document.getElementById('photo').files[0];
            if (photoFile) {
                formData.append('photo', photoFile);
            }
            
            try {
                const response = await fetch('/add_film', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + token
                    },
                    body: formData
                });
                
                if (response.ok) {
                    const result = await response.json();
                    messageDiv.innerHTML = `
                        <div style="color: green;">
                            <h3>Фильм успешно добавлен!</h3>
                            <p><strong>Название:</strong> ${result.film.name}</p>
                            <p><strong>Режиссёр:</strong> ${result.film.director}</p>
                            <p><strong>Стоимость:</strong> ${result.film.cost} руб.</p>
                            <p><strong>Рекомендуется:</strong> ${result.film.good ? 'Да' : 'Нет'}</p>
                            <p><strong>Добавлено:</strong> ${result.film.added_by}</p>
                        </div>
                    `;
                    // Очищаем форму
                    document.getElementById('filmForm').reset();
                } else {
                    const error = await response.json();
                    messageDiv.innerHTML = `<p style="color: red;">Ошибка: ${error.detail}</p>`;
                }
            } catch (error) {
                messageDiv.innerHTML = '<p style="color: red;">Ошибка сети</p>';
            }
        });
    </script>
    """)

@app.post("/add_film")
async def protected_add_movie(
    name: str = Form(...),
    director: str = Form(...),
    cost: float = Form(...),
    good: bool = Form(False),
    photo: UploadFile = File(None),
    current_user: str = Depends(verify_token)
):
    photo_path = "static/default_movie.jpg"
    if photo and photo.filename:
        photo_path = f"static/{photo.filename}"
        with open(photo_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

    new_id = len(MOVIES) + 1
    
    new_movie = Movietop(
        name=name, 
        director=director, 
        cost=cost, 
        good=good, 
        id=new_id, 
        photo=photo_path
    )
    MOVIES.append(new_movie)
    
    return JSONResponse({
        "message": "Фильм успешно добавлен",
        "film": {
            "name": name,
            "director": director,
            "cost": cost,
            "good": good,
            "added_by": current_user,
            "photo": photo_path
        }
    })

@app.get("/")
def home():
    return HTMLResponse("""
    <h1>Система управления фильмами</h1>
    <ul>
        <li><a href="/login">Вход с JWT</a></li>
        <li><a href="/add_film_form">Добавить фильм (требуется JWT)</a></li>
        <li><a href="/study">Информация о БГИТУ</a></li>
        <li><a href="/movietop">Список всех фильмов</a></li>
    </ul>
    
    <script>
        // Проверяем авторизацию на главной странице
        const token = localStorage.getItem('jwt_token');
        if (token) {
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                document.body.innerHTML += '<p style="color: green;">✓ Вы авторизованы как: ' + payload.sub + '</p>';
            } catch (e) {
                console.log('Ошибка декодирования токена');
            }
        }
    </script>
    """)

@app.get("/study", response_class=HTMLResponse)
def study_info():
    return HTMLResponse("""
    <html>
        <head><title>БГИТУ</title></head>
        <body style="text-align: center; padding: 20px;">
            <h1>Брянский государственный инженерно-технологический университет</h1>
            <h2>Год основания: 1930</h2>
            <h3>Местоположение: Брянск</h3>
            <img src="/static/BGITU.jpg" style="max-width: 100%; height: 85%;">
            <br><br>
            <a href="/">На главную</a>
        </body>
    </html>
""")

@app.get("/movietop/{film_name}", response_model=Movietop)
def get_movie(film_name: str):
    for movie in MOVIES:
        if movie.name == film_name:
            return movie
    raise HTTPException(status_code=404, detail="Фильм не найден")

@app.get("/movietop")
def get_all_movies():
    return HTMLResponse(f"""
    <h2>Список всех фильмов ({len(MOVIES)}):</h2>
    <ul>
        {"".join([f'<li>{movie.name} - {movie.director} - {movie.cost} руб.</li>' for movie in MOVIES])}
    </ul>
    <a href="/">На главную</a>
    """)