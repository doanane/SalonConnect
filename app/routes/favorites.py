from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.salon import SalonResponse
from app.core.security import verify_token
from app.models.user import User, user_favorites
from app.models.salon import Salon
from sqlalchemy import and_

router = APIRouter()
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

@router.get("/favorites", response_model=List[SalonResponse])
def get_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's favorite salons"""
    # Get favorite salons using the association table
    favorite_salons = db.query(Salon).join(
        user_favorites, Salon.id == user_favorites.c.salon_id
    ).filter(
        user_favorites.c.user_id == current_user.id
    ).all()
    
    # Add is_favorited field
    for salon in favorite_salons:
        salon.is_favorited = True
    
    return favorite_salons

@router.post("/favorites/{salon_id}")
def add_to_favorites(
    salon_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add salon to favorites"""
    salon = db.query(Salon).filter(Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    
    # Check if already favorited
    existing = db.execute(
        user_favorites.select().where(
            and_(
                user_favorites.c.user_id == current_user.id,
                user_favorites.c.salon_id == salon_id
            )
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Salon already in favorites")
    
    # Add to favorites
    db.execute(
        user_favorites.insert().values(
            user_id=current_user.id,
            salon_id=salon_id
        )
    )
    db.commit()
    
    return {"message": "Salon added to favorites"}

@router.delete("/favorites/{salon_id}")
def remove_from_favorites(
    salon_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove salon from favorites"""
    # Remove from favorites
    result = db.execute(
        user_favorites.delete().where(
            and_(
                user_favorites.c.user_id == current_user.id,
                user_favorites.c.salon_id == salon_id
            )
        )
    )
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Salon not in favorites")
    
    return {"message": "Salon removed from favorites"}