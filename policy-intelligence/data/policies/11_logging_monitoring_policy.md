---
policy_id: POL-011
title: Logging & Monitoring Policy
team: Security Operations
owner: Director of Security Operations
version: 1.5
effective_date: 2021-04-22
last_reviewed: 2021-04-22
references: [NIST SP 800-53 Rev 4, SI-4]
---

# Logging & Monitoring Policy

## 1. Purpose
Ensures continuous visibility into system and account activity.

## 2. Scope
Applies to all production systems, cloud accounts, and identity platforms.

## 3. Requirements

### 3.1 Continuous Logging
Audit logging (including CloudTrail or equivalent) must remain enabled at all times on all production systems. Logging must not be manually disabled by an engineer for debugging or any other ad hoc purpose.

### 3.2 Retention
Log data must be retained for a minimum of 1 year in an immutable store.

### 3.3 Alerting
Security-relevant log events must generate alerts routed to the Security Operations Center within 5 minutes.
