#!/bin/bash
# SIMPLE S3 setup for demo (100 images, public read via object ACLs)
# 
# SECURITY: Uses IRSA for uploads, public-read ACL for serving
# Trade-off: Simpler setup, appropriate for demo scale

set -e

BUCKET_PREFIX="manu-multimodal-event-explorer-images"
REGION="us-east-1"
IRSA_ROLE_ARN="arn:aws:iam::275662791714:role/kanopy-staging-cicd-irsa"
TAGS="TagSet=[{Key=Project,Value=multimodal-event-explorer},{Key=Environment,Value=staging},{Key=Owner,Value=IST},{Key=purpose,Value=demo-image-storage},{Key=managed-by,Value=kanopy}]"

STAGING_BUCKET="${BUCKET_PREFIX}-staging"
echo "Creating S3 bucket (simple demo setup): $STAGING_BUCKET"

aws s3 mb s3://$STAGING_BUCKET --region $REGION
aws s3api put-bucket-tagging --bucket $STAGING_BUCKET --tagging "$TAGS"

# Allow public-read ACLs (for individual objects, not whole bucket)
aws s3api put-public-access-block \
    --bucket $STAGING_BUCKET \
    --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Bucket policy: IRSA can upload with public-read ACL
cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KanopyIRSAAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "${IRSA_ROLE_ARN}"
      },
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${STAGING_BUCKET}",
        "arn:aws:s3:::${STAGING_BUCKET}/*"
      ]
    }
  ]
}
EOF

aws s3api put-bucket-policy --bucket $STAGING_BUCKET --policy file:///tmp/bucket-policy.json

# Enable encryption
aws s3api put-bucket-encryption \
    --bucket $STAGING_BUCKET \
    --server-side-encryption-configuration '{
      "Rules": [{
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }]
    }'

echo ""
echo "✓ S3 bucket created: $STAGING_BUCKET"
echo ""
echo "Setup: Simple demo approach (public-read ACL per object)"
echo "Scale: Appropriate for 100 images, demo traffic"
echo ""
echo "Add to environment/staging.yaml:"
echo "  S3_BUCKET_NAME: $STAGING_BUCKET"
echo "  S3_REGION: $REGION"
