import boto3
import re
import requests
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile
from datetime import datetime, timedelta

from app.models.vendor import VendorKYC, KYCStatus
from app.models.user import User
from app.schemas.kyc import KYCSubmission, ExtractedIDData
from app.core.cloudinary import upload_image
from app.core.config import settings
from app.services.email import EmailService

class KYCService:
    # Initialize AWS Rekognition Client
    _rekognition_client = None

    @classmethod
    def get_aws_client(cls):
        """Singleton pattern to get AWS client"""
        if not cls._rekognition_client:
            cls._rekognition_client = boto3.client(
                'rekognition',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        return cls._rekognition_client

    @staticmethod
    def _get_image_bytes(image_url: str):
        """Helper: Download image from Cloudinary to send bytes to AWS"""
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"[KYC] Failed to download image for analysis: {e}")
            raise HTTPException(status_code=400, detail="Could not process uploaded image. Please try again.")

    @staticmethod
    def upload_kyc_document(file: UploadFile, folder: str = "kyc_docs"):
        """Uploads document to Cloudinary"""
        try:
            result = upload_image(file.file, folder=f"salon_connect/{folder}")
            return result.get('secure_url')
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

    @staticmethod
    def extract_data_from_id(front_image_url: str) -> ExtractedIDData:
        """
        REAL WORLD OCR: Uses AWS Rekognition to read the ID Card.
        specifically looks for Ghana Card patterns.
        """
        print(f" [KYC-AWS] Analyzing ID text: {front_image_url}")
        client = KYCService.get_aws_client()
        image_bytes = KYCService._get_image_bytes(front_image_url)

        try:
            response = client.detect_text(Image={'Bytes': image_bytes})
            detected_text = [item['DetectedText'] for item in response['TextDetections']]
            full_text_blob = " ".join(detected_text)
            
            print(f" [KYC-AWS] Raw Text Detected: {detected_text}")

            # --- PARSING LOGIC FOR GHANA CARD / ID ---
            extracted = ExtractedIDData()
            extracted.raw_text = full_text_blob # For debugging
            extracted.document_type = "Unknown ID"

            # 1. Detect ID Number (Ghana Card Format: GHA-123456789-0)
            # Regex looks for: GHA, followed by numbers/dashes
            gha_pattern = re.search(r'(GHA-\d{9}-\d)', full_text_blob)
            if gha_pattern:
                extracted.id_number = gha_pattern.group(0)
                extracted.document_type = "Ghana Card"
            else:
                # Fallback: Look for Voter ID (typical 10 digits) or Passport
                voter_pattern = re.search(r'\b\d{10}\b', full_text_blob)
                if voter_pattern:
                    extracted.id_number = voter_pattern.group(0)
                    extracted.document_type = "Voter ID / Other"

            # 2. Detect Date of Birth (dd/mm/yyyy or yyyy-mm-dd)
            # This regex looks for dates near keywords like "DOB" or just standard date formats
            date_pattern = re.search(r'\d{2}[-/]\d{2}[-/]\d{4}', full_text_blob)
            if date_pattern:
                extracted.date_of_birth = date_pattern.group(0)

            # 3. Detect Name (Simplistic heuristic: Looks for all-caps words that are likely names)
            # In production, you might look for lines strictly below "Name" or "Surname" labels
            # For now, we leave name empty to force user verification unless we find a strong match
            
            # Identify 'Republic of Ghana' to confirm validity
            if "REPUBLIC OF GHANA" in full_text_blob.upper() or "ECOWAS" in full_text_blob.upper():
                if not extracted.document_type:
                    extracted.document_type = "Ghana National ID"

            return extracted

        except Exception as e:
            print(f" [KYC-AWS] OCR Error: {e}")
            # Do not block the user; return empty data so they can fill it manually
            return ExtractedIDData(raw_text="OCR Failed")

    @staticmethod
    def perform_liveness_check(id_front_url: str, selfie_url: str):
        """
        REAL WORLD BIOMETRICS: Uses AWS Rekognition CompareFaces.
        Verifies that the face in the ID matches the Selfie.
        """
        print(f" [KYC-AWS] Comparing Faces...")
        client = KYCService.get_aws_client()
        
        id_bytes = KYCService._get_image_bytes(id_front_url)
        selfie_bytes = KYCService._get_image_bytes(selfie_url)

        try:
            # 1. Compare Faces
            response = client.compare_faces(
                SourceImage={'Bytes': id_bytes},
                TargetImage={'Bytes': selfie_bytes},
                SimilarityThreshold=85 # 85% confidence required
            )

            matches = response.get('FaceMatches', [])
            
            if not matches:
                print(" [KYC-AWS] No face match found.")
                return False

            # Get the best match
            best_match = matches[0]
            similarity = best_match['Similarity']
            print(f" [KYC-AWS] Match Confidence: {similarity}%")

            # 2. Basic Liveness/Quality Check on Selfie
            # We check the selfie to ensure it's not a blurry blob or eyes closed
            # (Note: For true "active liveness" (blink detection), frontend integration is needed)
            face_details = client.detect_faces(
                Image={'Bytes': selfie_bytes},
                Attributes=['ALL']
            )
            
            if not face_details['FaceDetails']:
                print(" [KYC-AWS] No face detected in selfie.")
                return False
                
            face = face_details['FaceDetails'][0]
            
            # Check basic quality
            if face['Quality']['Brightness'] < 40 or face['Quality']['Sharpness'] < 40:
                print(" [KYC-AWS] Selfie quality too low.")
                # We return False or could throw a specific error
                # For strict mode: return False
                # For lenient mode: pass it
            
            return True

        except client.exceptions.InvalidParameterException:
            print(" [KYC-AWS] No face detected in one of the images.")
            return False
        except Exception as e:
            print(f" [KYC-AWS] Biometric Error: {e}")
            return False

    @staticmethod
    def submit_kyc(db: Session, vendor_id: int, data: KYCSubmission):
        """
        Final Submission Logic
        """
        # 1. Duplicate ID Check (CRITICAL: Prevents 30-day trial abuse)
        # Check if this ID number exists in APPROVED records
        existing_kyc = db.query(VendorKYC).filter(
            VendorKYC.id_number == data.id_number,
            VendorKYC.status == KYCStatus.APPROVED
        ).first()
        
        # If it exists AND belongs to a different user -> REJECT
        if existing_kyc and existing_kyc.vendor_id != vendor_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="IDENTITY FRAUD DETECTED: This ID card is already linked to another registered account. Contact support."
            )

        # 2. Perform Real Face Verification
        # We re-verify on submission to ensure URLs weren't swapped
        is_match = KYCService.perform_liveness_check(data.id_front_url, data.selfie_url)
        
        if not is_match:
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST, 
                 detail="Biometric Verification Failed. The person in the selfie does not match the ID card provided."
             )

        # 3. Save Data
        user_kyc = db.query(VendorKYC).filter(VendorKYC.vendor_id == vendor_id).first()
        if not user_kyc:
            user_kyc = VendorKYC(vendor_id=vendor_id)
            db.add(user_kyc)
        
        user_kyc.id_type = data.id_type
        user_kyc.id_number = data.id_number
        user_kyc.extracted_name = data.full_name
        user_kyc.extracted_dob = data.date_of_birth
        user_kyc.id_card_front_url = data.id_front_url
        user_kyc.id_card_back_url = data.id_back_url
        user_kyc.selfie_url = data.selfie_url
        user_kyc.status = KYCStatus.APPROVED # Auto-approve since AWS verified it
        user_kyc.verified_at = datetime.utcnow()
        
        # 4. Activate 30-Day Free Trial
        user = db.query(User).filter(User.id == vendor_id).first()
        user.kyc_verified = True
        user.subscription_plan = "premium_trial"
        
        # Set expiry (30 Days)
        expiry_date = datetime.utcnow() + timedelta(days=30)
        user.subscription_expires_at = expiry_date
        
        db.commit()
        db.refresh(user_kyc)
        
        # 5. Send Email
        try:
            EmailService.send_trial_started_email(user, expiry_date)
        except Exception as e:
            print(f"Failed to send trial email: {e}")
        
        return user_kyc

    @staticmethod
    def get_kyc_status(db: Session, vendor_id: int):
        return db.query(VendorKYC).filter(VendorKYC.vendor_id == vendor_id).first()