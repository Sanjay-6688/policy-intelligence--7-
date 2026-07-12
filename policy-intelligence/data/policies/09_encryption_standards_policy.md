---
policy_id: POL-009
title: Encryption Standards Policy
team: Security Architecture
owner: Chief Information Security Officer
version: 2.2
effective_date: 2022-11-05
last_reviewed: 2022-11-05
references: [NIST SP 800-53 Rev 5, FIPS 140-2]
---

# Encryption Standards Policy

## 1. Purpose
Sets the corporate standard for encryption algorithms and key strength.

## 2. Scope
Applies to all systems storing or transmitting Confidential or Restricted data.

## 3. Requirements

### 3.1 Data at Rest
All Confidential and Restricted data must be encrypted at rest using AES-256 or stronger.

### 3.2 Data in Transit
All data in transit must use TLS 1.2 or higher. TLS 1.0 and TLS 1.1 are prohibited for any new system.

### 3.3 Key Management
Encryption keys must be rotated at least annually and stored in an approved key management system (KMS/HSM).
