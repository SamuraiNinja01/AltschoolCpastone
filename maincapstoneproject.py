from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = "sqlite:///movies.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)

class Movie(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", backref="movies")

class Rating(Base):
    __tablename__ = "ratings"
    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.id"))
    movie = relationship("Movie", backref="ratings")
    rating = Column(Float)

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.id"))
    movie = relationship("Movie", backref="comments")
    text = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", backref="comments")
    parent_id = Column(Integer, ForeignKey("comments.id"))
    parent = relationship("Comment", backref="replies")

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = Response("Internal server error", status_code=500)
    try:
        request.state.db = SessionLocal()
        response = await call_next(request)
    finally:
        request.state.db.close()
    return response

def get_db(request: Request):
    return request.state.db

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        user = db.query(User).get(user_id)
    except JWTError:
        raise credentials_exception
    if user is None:
        raise credentials_exception
    return user

@app.post("/register")
async def register_user(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=username).first()
    if user is not None:
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed_password = get_password_hash(password)
    user = User(username=username, password=hashed_password)
    db.add(user)
    db.commit()
    return {"message": "User created successfully"}

@app.post("/token")
async def login_for_access_token(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=username).first()
    if user is None or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"user_id": user.id}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/movies/")
async def get_movies(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    movies = db.query(Movie).offset(skip).limit(limit).all()
    return [{"id": movie.id, "title": movie.title, "description": movie.description} for movie in movies]

@app.post("/movies/")
async def create_movie(title: str, description: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    movie = Movie(title=title, description=description, user_id=user.id)
    db.add(movie)
    db.commit()
    return {"id": movie.id, "title": movie.title, "description": movie.description}

@app.get("/movies/{movie_id}")
async def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).get(movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return {"id": movie.id, "title": movie.title, "description": movie.description}

@app.put("/movies/{movie_id}")
async def update_movie(movie_id: int, title: str, description: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    movie = db.query(Movie).get(movie_id)
    if movie is None or movie.user_id != user.id:
        raise HTTPException(status_code=404, detail="Movie not found or not authorized")
    movie.title = title
    movie.description = description
    db.commit()
    return {"id": movie.id, "title": movie.title, "description": movie.description}

@app.delete("/movies/{movie_id}")
async def delete_movie(movie_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    movie = db.query(Movie).get(movie_id)
    if movie is None or movie.user_id != user.id:
        raise HTTPException(status_code=404, detail="Movie not found or not authorized")
    db.delete(movie)
    db.commit()
    return {"message": "Movie deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
