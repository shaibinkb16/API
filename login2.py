from datetime import datetime, timedelta
from typing import Annotated
from contextlib import asynccontextmanager
import jwt
from fastapi import Depends, FastAPI, HTTPException, status, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import uuid
import os
import re

# ==============================
# MongoDB Atlas Connection
# ==============================
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://shaibinkb16_db_user:Shaibin@cluster0.rpxtsc4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(MONGO_URI)
db = client["posh"]
users_collection = db["users"]
authorized_emails_collection = db["authorized_emails"]

# ==============================
# JWT Config
# ==============================
SECRET_KEY = "e4e85ad2eb8a95e9b2a4afb9068c8ca91c90916f206fd35101a23bd7f70e438d"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        client.admin.command("ping")
        print("Successfully connected to MongoDB Atlas!")
    except ConnectionFailure as e:
        print("MongoDB connection failed:", e)
    yield

app = FastAPI(title="POSH Training Auth API", lifespan=lifespan)

# ==============================
# Custom Exception Handler
# ==============================
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom exception handler to return consistent error format
    """
    if exc.status_code == 401:
        return JSONResponse(
            status_code=401,
            content={
                "error": True,
                "error_code": "UNAUTHORIZED",
                "message": "Unauthorized Access",
                "details": exc.detail,
                "suggestions": [
                    "Ensure you are logged in with a valid token",
                    "Your session may have expired - please login again",
                    "Check that the Authorization header is properly set"
                ]
            }
        )
    elif exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={
                "error": True,
                "error_code": "NOT_FOUND",
                "message": "Resource Not Found",
                "details": exc.detail,
                "suggestions": [
                    "Check the URL you are trying to access",
                    "Ensure the resource exists"
                ]
            }
        )
    else:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "error_code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": exc.detail,
                "suggestions": []
            }
        )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*",
        "http://localhost:3000",  # For local development
        "https://posh-training.s3.eu-north-1.amazonaws.com",  # Your frontend URL
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ==============================
# Security
# ==============================
security = HTTPBearer()

class Token(BaseModel):
    access_token: str
    token_type: str
    email: str
    login_count: int

class TokenData(BaseModel):
    email: str | None = None

class Progress(BaseModel):
    completed_slides: int
    total_login_time: float
    login_count: int
    status: str

class ErrorResponse(BaseModel):
    error: bool
    error_code: str
    message: str
    details: str
    suggestions: list[str]

# ==============================
# Utility Functions
# ==============================
def is_valid_email(email: str) -> bool:
    """
    Validate email format using regex
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def is_email_authorized(email: str) -> tuple[bool, str]:
    """
    Check if an email is in the authorized_emails collection
    Returns: (is_authorized: bool, name: str)
    """
    try:
        result = authorized_emails_collection.find_one({"email": email.lower()})
        if result:
            return True, result["name"]
        else:
            return False, ""
    except Exception as e:
        print(f"Error checking email authorization: {e}")
        return False, ""

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
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
        return TokenData(email=email)
    except jwt.PyJWTError:
        raise credentials_exception

# ==============================
# Health Check Endpoint
# ==============================
@app.get("/health")
async def health_check():
    try:
        client.admin.command("ping")
        return {"status": "ok", "message": "MongoDB connected"}
    except ConnectionFailure:
        raise HTTPException(status_code=500, detail="MongoDB not connected")

# ==============================
# Endpoints
# ==============================
@app.post("/auth")
async def authenticate_user(email: Annotated[str, Form()]):
    # First, validate email format
    if not is_valid_email(email):
        return {
            "error": True,
            "error_code": "INVALID_EMAIL_FORMAT",
            "message": "Invalid Email Format",
            "details": f"The email '{email}' is not in a valid format.",
            "suggestions": [
                "Please enter a valid email address (e.g., user@example.com)",
                "Check for typos in your email address",
                "Ensure the email contains '@' and a valid domain"
            ]
        }

    # Check if email is authorized
    is_authorized, name = is_email_authorized(email)
    if not is_authorized:
        return {
            "error": True,
            "error_code": "EMAIL_NOT_AUTHORIZED",
            "message": "Access Denied",
            "details": f"The email '{email}' is not authorized to access this POSH training system.",
            "suggestions": [
                "Please check if you entered the correct email address",
                "Contact your HR department or training administrator",
                "Ensure you are using your official company email",
                "If you believe this is an error, please contact support"
            ]
        }

    # Proceed with existing logic if email is authorized
    user = users_collection.find_one({"email": email})
    if user:
        login_count = user["login_count"] + 1
        users_collection.update_one({"email": email}, {"$set": {"login_count": login_count}})
    else:
        user_id = str(uuid.uuid4())
        user = {
            "_id": user_id,
            "email": email,
            "name": name,  # Add the name from authorized_emails
            "completed_slides": 0,  # start with 0
            "total_login_time": 0.0,
            "login_count": 1,
            "status": "in_progress",
            "start_time": None
        }
        users_collection.insert_one(user)
        login_count = 1

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"email": email}, expires_delta=access_token_expires
    )
    return {
        "error": False,
        "access_token": access_token,
        "token_type": "bearer",
        "email": email,
        "login_count": login_count,
        "message": "Authentication successful",
        "user_name": name
    }

@app.post("/progress/start")
async def start_slide(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    slide_id: Annotated[int, Form()]
):
    user = users_collection.find_one({"email": current_user.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    start_time = datetime.utcnow()
    users_collection.update_one(
        {"email": current_user.email},
        {"$set": {"current_slide": slide_id, "start_time": start_time}}
    )
    return {"message": f"Slide {slide_id} started at {start_time}"}

@app.post("/progress/end")
async def end_slide(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    slide_id: Annotated[int, Form()]
):
    user = users_collection.find_one({"email": current_user.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    end_time = datetime.utcnow()
    
    # Calculate login time automatically
    start_time = user.get("start_time")
    if start_time:
        login_time = (end_time - start_time).total_seconds() / 60  # in minutes
    else:
        login_time = 0.0

    total_time = user.get("total_login_time", 0.0) + login_time

    # ✅ Only keep the maximum slide number
    current_max = user.get("completed_slides", 0)
    if slide_id > current_max:
        completed_slides = slide_id
    else:
        completed_slides = current_max

    users_collection.update_one(
        {"email": current_user.email},
        {"$set": {
            "completed_slides": completed_slides,
            "total_login_time": total_time,
            "end_time": end_time
        }}
    )
    return {"message": f"Slide {slide_id} ended at {end_time}", "total_time": total_time}

@app.post("/progress/finish")
async def finish_training(current_user: Annotated[TokenData, Depends(get_current_user)]):
    user = users_collection.find_one({"email": current_user.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    users_collection.update_one(
        {"email": current_user.email},
        {"$set": {"status": "completed", "finished_at": datetime.utcnow()}}
    )
    return {"message": "Training completed ✅"}

@app.get("/progress", response_model=Progress)
async def get_progress(current_user: Annotated[TokenData, Depends(get_current_user)]):
    user = users_collection.find_one({"email": current_user.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return Progress(
        completed_slides=user.get("completed_slides", 0),
        total_login_time=user.get("total_login_time", 0.0),
        login_count=user.get("login_count", 0),
        status=user.get("status", "in_progress")
    )

@app.get("/check-email/{email}")
async def check_email_authorization(email: str):
    """Check if an email is authorized (for admin purposes)"""
    is_authorized, name = is_email_authorized(email)
    return {
        "email": email,
        "is_authorized": is_authorized,
        "name": name if is_authorized else None
    }

# ==============================
# Run App
# ==============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
