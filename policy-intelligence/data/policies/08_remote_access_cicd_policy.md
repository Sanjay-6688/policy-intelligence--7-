---
policy_id: POL-008
title: Remote Access & CI/CD Exception Policy
team: DevOps
owner: Head of Platform Engineering
version: 1.0
effective_date: 2024-03-18
last_reviewed: 2024-03-18
references: [Network Security Policy POL-007]
---

# Remote Access & CI/CD Exception Policy

## 1. Purpose
Defines a scoped exception to VPN requirements for automated CI/CD pipelines.

## 2. Scope
Applies exclusively to non-human, automated CI/CD pipeline service accounts. Does not apply to human/interactive access.

## 3. Requirements

### 2.1 CI/CD VPN Exception
CI/CD pipelines are exempt from the corporate VPN requirement defined in the Network Security Policy when connecting to deployment targets, provided that connections are authenticated via short-lived, scoped service credentials and originate from an allow-listed CI/CD IP range.

### 2.2 Compensating Controls
All CI/CD pipeline traffic exempted under this policy must be logged and reviewed weekly by the Platform Security team.
