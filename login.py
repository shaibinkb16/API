from datetime import datetime, timedelta
from typing import Annotated, List
import jwt
from fastapi import Depends, FastAPI, HTTPException, status, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import uuid
import json

# Configuration
SECRET_KEY = "e4e85ad2eb8a95e9b2a4afb9068c8ca91c90916f206fd35101a23bd7f70e438d"  # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# SQLite Database Setup
DATABASE_URL = "sqlite:///./posh.db"  
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    _completed_slides = Column(String, default="[]")  # JSON string to store list of slide IDs
    total_login_time = Column(Float, default=0.0)
    login_count = Column(Integer, default=0)
    
    @property
    def completed_slides(self):
        return json.loads(self._completed_slides or "[]")
    
    @completed_slides.setter
    def completed_slides(self, value):
        self._completed_slides = json.dumps(value or [])

Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="POSH Training Auth API")

# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"\nIncoming request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")

    response = await call_next(request)
    print(f"Response status: {response.status_code}")
    return response

# Security scheme
security = HTTPBearer()

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    login_count: int

class TokenData(BaseModel):
    user_id: str | None = None

class Progress(BaseModel):
    completed_slides: List[int]
    total_login_time: float
    login_count: int

# Utility functions
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        return TokenData(user_id=user_id)
    except jwt.PyJWTError:
        raise credentials_exception

# Endpoints

# Simple test endpoint
@app.post("/test")
async def test_form(name: str = Form()):
    return {"received_name": name}

@app.post("/auth", response_model=Token)
async def authenticate_user(name: Annotated[str, Form()], db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == name).first()
    if user:
        user.login_count += 1
    else:
        user_id = str(uuid.uuid4())
        user = User(user_id=user_id, name=name, completed_slides=[], total_login_time=0.0, login_count=1)
        db.add(user)
    
    db.commit()
    db.refresh(user)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.user_id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.user_id, "login_count": user.login_count}

@app.post("/progress")
async def update_progress(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    db: Session = Depends(get_db),
    slide_id: Annotated[int | None, Form()] = None,
    login_time: Annotated[float | None, Form()] = None
):
    user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated = False
    if slide_id is not None and slide_id not in user.completed_slides:
        current_slides = user.completed_slides
        current_slides.append(slide_id)
        user.completed_slides = current_slides
        updated = True
    if login_time is not None:
        user.total_login_time += login_time
        updated = True
    
    if updated:
        db.commit()
        db.refresh(user)
    
    return Progress(completed_slides=user.completed_slides, total_login_time=user.total_login_time, login_count=user.login_count)

@app.get("/progress", response_model=Progress)
async def get_progress(current_user: Annotated[TokenData, Depends(get_current_user)], db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return Progress(completed_slides=user.completed_slides, total_login_time=user.total_login_time, login_count=user.login_count)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
