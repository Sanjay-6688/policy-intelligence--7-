---
policy_id: POL-002
title: Cloud Security Policy
team: Cloud Engineering
owner: VP Cloud Platform
version: 3.0
effective_date: 2024-01-10
last_reviewed: 2024-01-10
references: [CIS Benchmarks, NIST SP 800-53 Rev 5]
---

# Cloud Security Policy

## 1. Purpose
Defines security control requirements for AWS and Azure environments.

## 2. Scope
Applies to all cloud-hosted infrastructure, workloads, and identity systems.

## 3. Requirements

### 5.1 Encryption at Rest
All cloud-hosted data stores must use AES-256 encryption at rest. No exceptions.

### 5.2 Authentication
Cloud accounts shall not require periodic password rotation. Instead, multi-factor authentication (MFA) must be enforced on all cloud accounts as the primary defense against credential compromise. Forced password rotation is deprecated as a control in favor of MFA and will not be required for cloud-hosted systems.

### 5.3 Logging
CloudTrail (or equivalent audit logging) must be enabled at all times on every account and region. Logging must not be disabled outside of an approved, time-boxed exception under the Incident Response Policy.

### 5.4 Network Exposure
Security groups and equivalent network controls must default to deny-all inbound, with exceptions requiring documented business justification and expiration date.
