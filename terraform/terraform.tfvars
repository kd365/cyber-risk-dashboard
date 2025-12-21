
# AWS Configuration
aws_region  = "us-west-2"
aws_profile = "class"
environment = "dev"
name_suffix = "-kh"  # Suffix appended to all resource names

# VPC Configuration
vpc_cidr = "10.0.0.0/16"

# RDS Configuration
db_name           = "cyberrisk"
db_username       = "cyberrisk_admin"
db_password       = "CHANGE_ME_SECURE_PASSWORD"
db_instance_class = "db.t3.micro"

# EC2 Configuration
ec2_instance_type = "t3.small"  # 2GB RAM - needed for sentiment analysis
ec2_key_name      = "try2-kh"   # Name of your EC2 key pair (without .pem)

# Source S3 Configuration (for data migration)
source_s3_bucket   = "cyber-risk-artifacts"
source_aws_profile = "cyber-risk"
