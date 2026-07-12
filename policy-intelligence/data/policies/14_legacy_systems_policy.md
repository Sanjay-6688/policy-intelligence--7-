---
policy_id: POL-014
title: Legacy Systems Support Policy
team: Infrastructure
owner: Director of Infrastructure
version: 1.0
effective_date: 2019-05-08
last_reviewed: 2019-05-08
references: [Internal IT Standards v1]
---

# Legacy Systems Support Policy

## 1. Purpose
Defines interim support standards for legacy systems pending decommission.

## 2. Scope
Applies to systems running Windows Server 2012 or earlier and associated legacy admin consoles.

## 3. Requirements

### 3.1 Legacy Admin Console Access
The legacy administrative console for on-prem systems may be accessed using a strong password alone; MFA is not required for these consoles due to compatibility limitations with the legacy authentication module.

### 3.2 Cryptography
Legacy systems may continue to use SHA-1 for internal integrity checks where AES-256/SHA-256 upgrades are not yet supported by the vendor.

### 3.3 Decommission Timeline
Legacy systems should be decommissioned or upgraded "as soon as practicable."
