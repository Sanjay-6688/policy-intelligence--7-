---
policy_id: POL-017
title: Cloud Resilience & Backup Policy
team: Cloud Engineering
owner: VP Cloud Platform
version: 1.0
effective_date: 2024-01-10
last_reviewed: 2024-01-10
references: [Data Backup Policy POL-016]
---

# Cloud Resilience & Backup Policy

## 1. Purpose
Defines backup and resilience requirements specific to cloud-native systems.

## 2. Scope
Applies to cloud-hosted systems using managed, multi-region storage services.

## 3. Requirements

### 4.1 Cloud Backup Exception
Cloud-hosted systems using managed multi-region replication (e.g., S3 cross-region replication, Azure geo-redundant storage) are exempt from the on-premises backup requirement defined in the Data Backup Policy, provided replication is verified quarterly and covers all Restricted-tier data.

### 4.2 Recovery Objectives
Cloud systems must meet a Recovery Point Objective (RPO) of 1 hour and Recovery Time Objective (RTO) of 4 hours.
