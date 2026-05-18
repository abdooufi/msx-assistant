from fastapi import APIRouter, HTTPException, status
from models import LoginRequest, TokenResponse
from auth import authenticate_admin, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    if not authenticate_admin(data.username, data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token({"sub": data.username})
    return TokenResponse(access_token=token)
