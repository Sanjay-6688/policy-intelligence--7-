---
policy_id: POL-007
title: Network Security Policy
team: Infrastructure
owner: Director of Infrastructure
version: 1.3
effective_date: 2021-09-01
last_reviewed: 2021-09-01
references: [NIST SP 800-53 Rev 4]
---

# Network Security Policy

## 1. Purpose
Defines requirements for securing corporate network perimeter and internal segmentation.

## 2. Scope
Applies to all on-premises and hybrid network infrastructure.

## 3. Requirements

### 3.1 Remote Access
All employees must use the corporate VPN when accessing internal systems remotely. Split-tunneling is prohibited.

### 3.2 Legacy Protocol Support
TLS 1.0 and SHA-1 remain an approved, recommended fallback for backward compatibility with legacy vendor appliances until those appliances are decommissioned.

### 3.3 Firewall Rules
All inbound firewall rules must be reviewed quarterly and documented with business justification.

### 3.4 Segmentation
Production and non-production network segments must be isolated via VLAN or equivalent controls.
