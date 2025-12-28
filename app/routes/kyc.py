from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from fastapi.responses import HTMLResponse
import os

from app.database import get_db
from app.models.user import User
from app.services.auth import AuthService
from app.services.kyc_service import KYCService
from app.schemas.kyc import KYCSubmission, KYCResponse, ExtractedIDData
from app.core.security import verify_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()

async def get_current_vendor(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or user.role.value != "vendor":
        raise HTTPException(status_code=403, detail="Vendor access required")
    return user

@router.get("/portal", response_class=HTMLResponse)
def get_kyc_portal():
    """Serves the KYC HTML Interface"""
    with open(os.path.join("app", "templates", "kyc_portal.html"), "r") as f:
        return f.read()
        
@router.post("/upload-document", response_model=dict)
async def upload_document_step(
    file: UploadFile = File(...),
    doc_type: str = Form(...), # "front", "back", or "selfie"
    current_user: User = Depends(get_current_vendor)
):
    """
    Step 1 & 2: Upload ID images and Selfie. 
    Returns the URL and (if front ID) extracted text.
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
        
    url = KYCService.upload_kyc_document(file, folder=f"kyc/{current_user.id}")
    
    response = {"url": url, "type": doc_type}
    
    # If it's the front of the ID, try to extract data (Binance auto-fill style)
    if doc_type == "front":
        extracted_data = KYCService.extract_data_from_id(url)
        response["extracted_data"] = extracted_data
        
    return response

@router.post("/submit", response_model=KYCResponse)
def submit_kyc_application(
    submission: KYCSubmission,
    current_user: User = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """
    Final Step: User confirms the auto-filled data.
    Backend checks for duplicates, verifies face, and grants 30-day trial.
    """
    return KYCService.submit_kyc(db, current_user.id, submission)

@router.get("/status", response_model=Optional[KYCResponse])
def get_my_kyc_status(
    current_user: User = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    """Check if vendor is verified"""
    kyc = KYCService.get_kyc_status(db, current_user.id)
    if not kyc:
        # Return 204 or specific message if no KYC found
        return None 
    return kyc