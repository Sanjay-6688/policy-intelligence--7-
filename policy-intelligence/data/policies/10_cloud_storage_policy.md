---
policy_id: POL-010
title: Cloud Storage Security Policy
team: Cloud Engineering
owner: VP Cloud Platform
version: 1.0
effective_date: 2024-01-10
last_reviewed: 2024-01-10
references: [Encryption Standards Policy POL-009]
---

# Cloud Storage Security Policy

## 1. Purpose
Defines storage-layer security requirements for cloud object and block storage.

## 2. Scope
Applies to S3, Azure Blob Storage, and equivalent managed storage services.

## 3. Requirements

### 4.1 Encryption
All cloud object and block storage containing Confidential or Restricted data must be encrypted at rest using AES-256 encryption.

### 4.2 Public Access
Cloud storage buckets/containers must not be publicly accessible unless explicitly approved and documented as a Public-tier exception.

### 4.3 Versioning
Object versioning must be enabled on storage containing Restricted data to protect against accidental or malicious deletion.
