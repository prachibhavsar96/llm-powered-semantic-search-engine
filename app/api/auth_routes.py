from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import GoogleLogin, TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.
    """
    existing_user = db.query(User).filter(User.email == user_data.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered.")

    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Log in and receive a JWT access token.
    """
    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not user.hashed_password or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/google", response_model=TokenResponse)
def google_login(user_data: GoogleLogin, db: Session = Depends(get_db)):
    """
    Verify a Google ID token and return this app's JWT.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Google OAuth is not configured.")

    try:
        token_data = id_token.verify_oauth2_token(
            user_data.credential,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Google credential.") from exc

    email = token_data.get("email")

    if not email:
        raise HTTPException(status_code=401, detail="Google account email is missing.")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(email=email, hashed_password=None)
        db.add(user)
        db.commit()
        db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id))
