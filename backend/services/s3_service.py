"""S3 service for uploading and managing images in AWS S3."""

import os
import logging
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class S3Service:
    """Service for managing images in AWS S3.
    
    Uses AWS IRSA (IAM Roles for Service Accounts) for authentication
    when running in Kubernetes, or local AWS credentials otherwise.
    """
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region: str = "us-east-1"
    ):
        """Initialize S3 service.
        
        Args:
            bucket_name: S3 bucket name (from env var if not provided)
            region: AWS region
        """
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME")
        self.region = region
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME must be set in environment or passed to constructor")
        
        # Initialize S3 client (uses IRSA in K8s, credentials file locally)
        self.s3_client = boto3.client('s3', region_name=self.region)
        
        logger.info(f"S3Service initialized for bucket: {self.bucket_name}")
    
    def upload_image(
        self,
        local_path: Path,
        s3_key: str,
        content_type: str = "image/jpeg"
    ) -> Optional[str]:
        """Upload an image to S3 with public-read ACL.
        
        Args:
            local_path: Path to local image file
            s3_key: S3 object key (path within bucket)
            content_type: MIME type of the image
            
        Returns:
            S3 URL if successful, None otherwise
        """
        try:
            if not local_path.exists():
                logger.error(f"Local file not found: {local_path}")
                return None
            
            # Upload file with public-read ACL (simple demo approach)
            self.s3_client.upload_file(
                str(local_path),
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'CacheControl': 'max-age=31536000',  # 1 year cache
                    'ACL': 'public-read'  # Make object publicly readable
                }
            )
            
            # Construct S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            logger.info(f"Uploaded {local_path.name} to S3: {s3_key}")
            return s3_url
            
        except ClientError as e:
            logger.error(f"Failed to upload {local_path} to S3: {e}")
            return None
    
    def upload_image_from_path(
        self,
        image_path: str,
        images_base_dir: Path,
        domain: str = "adas"
    ) -> Optional[str]:
        """Upload an image using its relative path.
        
        Args:
            image_path: Relative path (e.g., "adas/mist_00001.jpg")
            images_base_dir: Base directory for images
            domain: Domain name
            
        Returns:
            S3 URL if successful, None otherwise
        """
        local_path = images_base_dir / image_path
        # Use same path structure in S3
        s3_key = image_path
        
        return self.upload_image(local_path, s3_key)
    
    def check_bucket_exists(self) -> bool:
        """Check if the S3 bucket exists and is accessible.
        
        Returns:
            True if bucket exists and is accessible
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' is accessible")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"S3 bucket '{self.bucket_name}' does not exist")
            elif error_code == '403':
                logger.error(f"Access denied to S3 bucket '{self.bucket_name}'")
            else:
                logger.error(f"Error accessing S3 bucket: {e}")
            return False
    
    def delete_image(self, s3_key: str) -> bool:
        """Delete an image from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted S3 object: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete {s3_key} from S3: {e}")
            return False
