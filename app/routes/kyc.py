from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database import get_db
from app.models.user import User, UserRole
from app.models.kyc import VendorKYC, KYCAuditLog
from app.schemas.kyc import *
from app.services.kyc_service import KYCService
from app.core.dependencies import get_current_user
from app.core.config import settings

router = APIRouter()
kyc_service = KYCService()
logger = logging.getLogger(__name__)

@router.get("/portal", response_class=HTMLResponse)
async def kyc_portal(request: Request):
    """Serve KYC portal HTML"""
    with open("app/templates/kyc_portal.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = "front",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload KYC document"""
    try:
        # Check if user is vendor
        if current_user.role != UserRole.VENDOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only vendors can upload KYC documents"
            )
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # Upload to S3
        file_url = await kyc_service.upload_document_to_s3(
            file.file,
            current_user.id,
            doc_type
        )
        
        # Extract data if it's ID front
        extracted_data = {}
        if doc_type == "front":
            extracted_data = await kyc_service.extract_document_data(file_url)
        
        # Create or update KYC record
        kyc_record = db.query(VendorKYC).filter(
            VendorKYC.vendor_id == current_user.id
        ).first()
        
        if not kyc_record:
            kyc_record = VendorKYC(vendor_id=current_user.id)
            db.add(kyc_record)
        
        # Update document URL
        if doc_type == "front":
            kyc_record.id_front_url = file_url
        elif doc_type == "back":
            kyc_record.id_back_url = file_url
        elif doc_type == "selfie":
            kyc_record.selfie_url = file_url
        
        if extracted_data:
            kyc_record.ocr_extracted_data = extracted_data
        
        db.commit()
        db.refresh(kyc_record)
        
        # Log action
        audit_log = KYCAuditLog(
            kyc_id=kyc_record.id,
            action="document_upload",
            performed_by=current_user.id,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            details={"doc_type": doc_type, "file_size": file.size}
        )
        db.add(audit_log)
        db.commit()
        
        return {
            "message": "Document uploaded successfully",
            "url": file_url,
            "extracted_data": extracted_data
        }
        
    except Exception as e:
        logger.error(f"Document upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.post("/submit", response_model=KYCResponse)
async def submit_kyc(
    request: KYCVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit KYC for verification"""
    try:
        # Check if user is vendor
        if current_user.role != UserRole.VENDOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only vendors can submit KYC"
            )
        
        # Check if already submitted
        existing_kyc = db.query(VendorKYC).filter(
            VendorKYC.vendor_id == current_user.id,
            VendorKYC.status.in_(["processing", "approved"])
        ).first()
        
        if existing_kyc and existing_kyc.status == "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KYC already approved"
            )
        elif existing_kyc and existing_kyc.status == "processing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KYC is already being processed"
            )
        
        # Create KYC record
        kyc_record = db.query(VendorKYC).filter(
            VendorKYC.vendor_id == current_user.id
        ).first()
        
        if not kyc_record:
            kyc_record = VendorKYC(vendor_id=current_user.id)
            db.add(kyc_record)
        
        # Update with submitted data
        kyc_record.id_type = request.id_type
        kyc_record.id_number = request.id_number
        kyc_record.full_name = request.full_name
        kyc_record.date_of_birth = datetime.strptime(request.date_of_birth, '%Y-%m-%d')
        kyc_record.id_front_url = request.id_front_url
        kyc_record.id_back_url = request.id_back_url
        kyc_record.selfie_url = request.selfie_url
        kyc_record.status = "processing"
        
        # Perform KYC analysis
        analysis_data = {
            'id_front_url': request.id_front_url,
            'id_back_url': request.id_back_url,
            'selfie_url': request.selfie_url
        }
        
        analysis = await kyc_service.perform_full_kyc_analysis(analysis_data)
        
        # Update with analysis results
        kyc_record.face_match_score = analysis.get('face_comparison', {}).get('score')
        kyc_record.face_match_status = "verified" if analysis.get('face_comparison', {}).get('is_match') else "failed"
        kyc_record.document_verification_status = "verified" if analysis.get('document_verification', {}).get('is_valid') else "failed"
        kyc_record.is_document_valid = analysis.get('document_verification', {}).get('is_valid')
        kyc_record.is_live_selfie = analysis.get('liveness_check', {}).get('is_live')
        kyc_record.risk_score = analysis.get('risk_score', 1.0)
        kyc_record.ai_analysis = analysis
        
        # Auto-approve if all checks pass
        if analysis.get('is_approved'):
            kyc_record.status = "approved"
            # Start vendor's 30-day trial
            current_user.kyc_verified = True
            current_user.subscription_plan = "premium_trial"
            current_user.subscription_expires_at = datetime.now() + timedelta(days=30)
            
            # Send trial started email
            from app.services.email import EmailService
            EmailService.send_trial_started_email(
                email=current_user.email,
                first_name=current_user.first_name,
                expiry_date=current_user.subscription_expires_at
            )
        else:
            kyc_record.status = "rejected"
            kyc_record.rejection_reason = analysis.get('recommendations', 'KYC verification failed')
        
        db.commit()
        db.refresh(kyc_record)
        
        # Log action
        audit_log = KYCAuditLog(
            kyc_id=kyc_record.id,
            action="kyc_submitted",
            performed_by=current_user.id,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            details={"status": kyc_record.status, "risk_score": kyc_record.risk_score}
        )
        db.add(audit_log)
        db.commit()
        
        return kyc_record
        
    except Exception as e:
        logger.error(f"KYC submission failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"KYC submission failed: {str(e)}"
        )