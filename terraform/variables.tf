# =============================================================================
# CyberRisk Dashboard - Terraform Variables
# =============================================================================

# -----------------------------------------------------------------------------
# General Configuration
# -----------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-west-2"
}

variable "name_suffix" {
  description = "Suffix to append to resource names (e.g., -kh)"
  type        = string
  default     = "-kh"
}

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "class"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

# -----------------------------------------------------------------------------
# VPC Configuration
# -----------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# -----------------------------------------------------------------------------
# RDS Configuration
# -----------------------------------------------------------------------------

variable "db_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "cyberrisk"
}

variable "db_username" {
  description = "Master username for RDS"
  type        = string
  default     = "cyberrisk_admin"
}

variable "db_password" {
  description = "Master password for RDS (use environment variable TF_VAR_db_password)"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

# -----------------------------------------------------------------------------
# EC2 Configuration
# -----------------------------------------------------------------------------

variable "ec2_instance_type" {
  description = "EC2 instance type for Flask backend"
  type        = string
  default     = "t2.micro"
}

variable "ec2_key_name" {
  description = "Name of existing EC2 key pair for SSH access"
  type        = string
}

# -----------------------------------------------------------------------------
# Source Data Configuration (for migration)
# -----------------------------------------------------------------------------

variable "source_s3_bucket" {
  description = "Source S3 bucket containing artifacts (cyber-risk profile)"
  type        = string
  default     = "cyber-risk-artifacts"
}

variable "source_aws_profile" {
  description = "AWS profile for source S3 bucket"
  type        = string
  default     = "cyber-risk"
}
