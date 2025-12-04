from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional

class Movietop(BaseModel):
    name: str
    id: int
    cost: int
    director: str
    good: bool = False
    photo: str = ""

class UserProfile(BaseModel):
    username: str
    last_login: datetime
    last_login: List[datetime]
    movies: List[Movietop]

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

MOVIES = [
    Movietop(name="Интерстеллар", id=1, cost=165000000, director="Кристофер Нолан"),
    Movietop(name="Начало", id=2, cost=160000000, director="Кристофер Нолан"),
    Movietop(name="Побег из Шоушенка", id=3, cost=25000000, director="Фрэнк Дарабонт"),
    Movietop(name="Крёстный отец", id=4, cost=6000000, director="Фрэнсис Форд Коппола"),
    Movietop(name="Темный рыцарь", id=5, cost=185000000, director="Кристофер Нолан"),
    Movietop(name="Форрест Гамп", id=6, cost=55000000, director="Роберт Земекис"),
    Movietop(name="Матрица", id=7, cost=63000000, director="Вачовски"),
    Movietop(name="Гладиатор", id=8, cost=103000000, director="Ридли Скотт"),
    Movietop(name="Властелин колец", id=9, cost=93000000, director="Питер Джексон"),
    Movietop(name="Паразиты", id=10, cost=11400000, director="Пон Джун-хо"),
]