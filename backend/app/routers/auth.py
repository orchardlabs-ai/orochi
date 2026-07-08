from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from .. import db
from ..config import settings
from ..deps import current_user
from ..security import make_session, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginRequest, response: Response):
    user = db.get_user(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    token = make_session(user["email"])
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.COOKIE_MAX_AGE,
        path="/",
    )
    return {"user": {"email": user["email"]}}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=settings.COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/me")
def me(user=Depends(current_user)):
    return {"user": {"email": user["email"]}}
