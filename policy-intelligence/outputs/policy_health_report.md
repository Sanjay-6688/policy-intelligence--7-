# Policy Governance Health Report

*Generated 2026-07-11T02:52:25Z · mode: `offline` · as-of: 2025-06-01*

## Summary

- Policies analyzed: **17**
- Obligations extracted: **56**
- Candidate pairs evaluated: **57**
- Conflicts: **8** · Redundant: **8** · Complementary: **32**
- Policies stale or critical: **13** / 17

## Top Conflicts (unreconciled)

**CONFLICT** — POL-001 §3.1 vs POL-002 §5.2  (topic: `password_rotation`, confidence: 88%)

> **A.** "All employees must rotate passwords every 90 days for all corporate accounts, including cloud-hosted systems."
>
> **B.** "Forced password rotation is deprecated as a control in favor of MFA and will not be required for cloud-hosted systems."

POL-001 §3.1 ('All employees must rotate passwords every 90 days for all corporate accounts, including cloud-hosted systems.') requires 'password_rotation', while POL-002 §5.2 ('Forced password rotation is deprecated as a control in favor of MFA and will not be required for cloud-hosted systems.') prohibits or exempts the same obligation. Both apply to overlapping scope ('cloud_accounts' vs 'cloud_accounts'). These are both active, approved policies.

*Controls:* COBIT 2019 APO03 (Maintain Policy Framework), ISO 27001 A.5.1 (Policies for Information Security), NIST SP 800-53 IA-5 (Authenticator Management)

---
**CONFLICT** — POL-005 §3.1 vs POL-006 §4.2  (topic: `data_retention`, confidence: 88%)

> **A.** "Financial and transactional records must be retained for a minimum of 7 years from the date of creation, in accordance with SOX requirements."
>
> **B.** "Personal data must not be retained longer than necessary for the purpose for which it was collected."

POL-005 §3.1 ('Financial and transactional records must be retained for a minimum of 7 years from the date of creation, in accordance with SOX requirements.') requires 'data_retention', while POL-006 §4.2 ('Personal data must not be retained longer than necessary for the purpose for which it was collected.') prohibits or exempts the same obligation. Both apply to overlapping scope ('general' vs 'general'). These are both active, approved policies.

*Controls:* COBIT 2019 APO03 (Maintain Policy Framework), GDPR Article 5 (Storage Limitation), ISO 27001 A.5.1 (Policies for Information Security), SOX §802

---
**CONFLICT** — POL-005 §3.2 vs POL-011 §3.2  (topic: `log_retention`, confidence: 80%)

> **A.** "Security and access audit logs must be retained for a minimum of 3 years."
>
> **B.** "Log data must be retained for a minimum of 1 year in an immutable store."

POL-005 §3.2 specifies '3_years' while POL-011 §3.2 specifies '1_years' for the same 'log_retention' obligation and overlapping scope ('general'). These parameters cannot both be satisfied simultaneously.

*Controls:* COBIT 2019 APO03 (Maintain Policy Framework), ISO 27001 A.5.1 (Policies for Information Security), NIST SP 800-53 AU-11 (Audit Record Retention)

---
**CONFLICT** — POL-007 §3.2 vs POL-009 §3.2  (topic: `encryption_in_transit`, confidence: 74%)

> **A.** "TLS 1.0 and SHA-1 remain an approved, recommended fallback for backward compatibility with legacy vendor appliances until those appliances are decommissioned."
>
> **B.** "TLS 1.0 and TLS 1.1 are prohibited for any new system."

POL-007 §3.2 ('TLS 1.0 and SHA-1 remain an approved, recommended fallback for backward compatibility with legacy vendor appliances until those appliances are decommissioned.') requires 'encryption_in_transit', while POL-009 §3.2 ('TLS 1.0 and TLS 1.1 are prohibited for any new system.') prohibits or exempts the same obligation. Scopes differ ('vendors' vs 'general') but no exception clause reconciles them — this looks like an unaddressed gap rather than an intentional carve-out. These are both active, approved policies.

*Controls:* COBIT 2019 APO03 (Maintain Policy Framework), GDPR Article 32, ISO 27001 A.5.1 (Policies for Information Security), NIST SP 800-53 SC-8 (Transmission Confidentiality and Integrity)

---
**CONFLICT** — POL-013 §3.1 vs POL-014 §3.1  (topic: `mfa`, confidence: 74%)

> **A.** "Multi-factor authentication (MFA) must be enforced for all privileged and administrative accounts on all systems, with no exceptions."
>
> **B.** "The legacy administrative console for on-prem systems may be accessed using a strong password alone; MFA is not required for these consoles due to compatibility limitations with the legacy authentication module."

POL-013 §3.1 ('Multi-factor authentication (MFA) must be enforced for all privileged and administrative accounts on all systems, with no exceptions.') requires 'mfa', while POL-014 §3.1 ('The legacy administrative console for on-prem systems may be accessed using a strong password alone; MFA is not required for these consoles due to compatibility limitations with the legacy authentication module.') prohibits or exempts the same obligation. Scopes differ ('privileged_accounts' vs 'legacy_admin_console') but no exception clause reconciles them — this looks like an unaddressed gap rather than an intentional carve-out. These are both active, approved policies.

*Controls:* COBIT 2019 APO03 (Maintain Policy Framework), ISO 27001 A.5.1 (Policies for Information Security), NIST SP 800-53 IA-2 (Identification and Authentication)

---
**CONFLICT** — POL-002 §5.2 vs POL-014 §3.1  (topic: `mfa`, confidence: 74%)

> **A.** "Instead, multi-factor authentication (MFA) must be enforced on all cloud accounts as the primary defense against credential compromise."
>
> **B.** "The legacy administrative console for on-prem systems may be accessed using a strong password alone; MFA is not required for these consoles due to compatibility limitations with the legacy authentication module."

POL-002 §5.2 ('Instead, multi-factor authentication (MFA) must be enforced on all cloud accounts as the primary defense against credential compromise.') requires 'mfa', while POL-014 §3.1 ('The legacy administrative console for on-prem systems may be accessed using a strong password alone; MFA is not required for these consoles due to compatibility limitations with the legacy authentication module.') prohibits or exempts the same obligation. Scopes differ ('cloud_accounts' vs 'legacy_admin_console') but no exception clause reconciles them — this looks like an unaddressed gap rather than an intentional carve-out. These are both active, approved policies.

*Controls:* COBIT 2019 APO03 (Maintain Policy Framework), ISO 27001 A.5.1 (Policies for Information Security), NIST SP 800-53 IA-2 (Identification and Authentication)

---

## Top Redundancies (consolidation candidates)

**REDUNDANT** — POL-009 §3.1 vs POL-010 §4.1  (topic: `encryption_at_rest`, confidence: 80%)

> **A.** "All Confidential and Restricted data must be encrypted at rest using AES-256 or stronger."
>
> **B.** "All cloud object and block storage containing Confidential or Restricted data must be encrypted at rest using AES-256 encryption."

POL-009 §3.1 and POL-010 §4.1 impose the same 'encryption_at_rest' obligation ('mandatory') on the same scope ('confidential_restricted_data') in different wording. Consider consolidating ownership or cross-referencing one policy from the other to reduce maintenance burden.

*Controls:* COBIT 2019 APO03 (Maintain Policy Framework), GDPR Article 32, NIST SP 800-53 SC-28 (Protection of Information at Rest)

---
**REDUNDANT** — POL-004 §3.2 vs POL-009 §3.1  (topic: `encryption_at_rest`, confidence: 80%)

> **A.** "Confidential and Restricted data must be encrypted at rest using industry-standard encryption (minimum AES-256) and in transit using TLS 1.2 or higher."
>
> **B.** "All Confidential and Restricted data must be encrypted at rest using AES-256 or stronger."

POL-004 §3.2 and POL-009 §3.1 impose the same 'encryption_at_rest' obligation ('mandatory') on the same scope ('confidential_restricted_data') in different wording. Consider consolidating ownership or cross-referencing one policy from the other to reduce maintenance burden.

*Controls:* COBIT 2019 APO03 (Maintain Policy Framework), GDPR Article 32, NIST SP 800-53 SC-28 (Protection of Information at Rest)

---
**REDUNDANT** — POL-004 §3.2 vs POL-010 §4.1  (topic: `encryption_at_rest`, confidence: 80%)

> **A.** "Confidential and Restricted data must be encrypted at rest using industry-standard encryption (minimum AES-256) and in transit using TLS 1.2 or higher."
>
> **B.** "All cloud object and block storage containing Confidential or Restricted data must be encrypted at rest using AES-256 encryption."

POL-004 §3.2 and POL-010 §4.1 impose the same 'encryption_at_rest' obligation ('mandatory') on the same scope ('confidential_restricted_data') in different wording. Consider consolidating ownership or cross-referencing one policy from the other to reduce maintenance burden.

*Controls:* COBIT 2019 APO03 (Maintain Policy Framework), GDPR Article 32, NIST SP 800-53 SC-28 (Protection of Information at Rest)

---
**REDUNDANT** — POL-002 §5.4 vs POL-007 §3.3  (topic: `firewall_network`, confidence: 80%)

> **A.** "Security groups and equivalent network controls must default to deny-all inbound, with exceptions requiring documented business justification and expiration date."
>
> **B.** "All inbound firewall rules must be reviewed quarterly and documented with business justification."

POL-002 §5.4 and POL-007 §3.3 impose the same 'firewall_network' obligation ('mandatory') on the same scope ('general') in different wording. Consider consolidating ownership or cross-referencing one policy from the other to reduce maintenance burden.

*Controls:* CIS Control 12 (Network Infrastructure), COBIT 2019 APO03 (Maintain Policy Framework), NIST SP 800-53 SC-7 (Boundary Protection)

---
**REDUNDANT** — POL-002 §5.3 vs POL-011 §3.1  (topic: `logging_monitoring`, confidence: 80%)

> **A.** "Logging must not be disabled outside of an approved, time-boxed exception under the Incident Response Policy."
>
> **B.** "Logging must not be manually disabled by an engineer for debugging or any other ad hoc purpose."

POL-002 §5.3 and POL-011 §3.1 impose the same 'logging_monitoring' obligation ('prohibited') on the same scope ('general') in different wording. Consider consolidating ownership or cross-referencing one policy from the other to reduce maintenance burden.

*Controls:* COBIT 2019 APO03 (Maintain Policy Framework), NIST SP 800-53 AU-2 (Audit Events), NIST SP 800-53 SI-4 (System Monitoring)

---
**REDUNDANT** — POL-009 §3.3 vs POL-016 §3.3  (topic: `encryption_at_rest`, confidence: 80%)

> **A.** "Encryption keys must be rotated at least annually and stored in an approved key management system (KMS/HSM)."
>
> **B.** "Backup media must be encrypted at rest."

POL-009 §3.3 and POL-016 §3.3 impose the same 'encryption_at_rest' obligation ('mandatory') on the same scope ('general') in different wording. Consider consolidating ownership or cross-referencing one policy from the other to reduce maintenance burden.

*Controls:* COBIT 2019 APO03 (Maintain Policy Framework), GDPR Article 32, NIST SP 800-53 SC-28 (Protection of Information at Rest)

---

## Stalest Policies

| Policy | Last Reviewed | Months Since | Status | Deprecated References |
|---|---|---|---|---|
| Network Security Policy (POL-007) | 2021-09-01 | 45.0 | critical | TLS 1.0, SHA-1 |
| Legacy Systems Support Policy (POL-014) | 2019-05-08 | 72.8 | critical | SHA-1, Windows Server 2012 |
| Encryption Standards Policy (POL-009) | 2022-11-05 | 30.9 | critical | TLS 1.0, TLS 1.1 |
| Acceptable Use Policy (POL-003) | 2020-06-01 | 60.0 | critical | TLS 1.0 |
| Vendor & Third-Party Risk Policy (POL-015) | 2020-11-11 | 54.7 | critical | NIST SP 800-53 Rev 4 |
| Password Policy (POL-001) | 2021-03-15 | 50.5 | critical | — |
| Data Classification Policy (POL-004) | 2022-02-20 | 39.4 | stale | — |
| Logging & Monitoring Policy (POL-011) | 2021-04-22 | 49.3 | critical | — |
| Data Backup Policy (POL-016) | 2021-09-01 | 45.0 | stale | — |
| Identity & Access Management Policy (POL-013) | 2022-07-19 | 34.4 | stale | — |

## Policy Health Scores (lowest first)

| Policy | Team | Conflicts | Redundant | Review Status | Health |
|---|---|---|---|---|---|
| Cloud Security Policy (POL-002) | Cloud Engineering | 3 | 4 | aging | 0/100 |
| Encryption Standards Policy (POL-009) | Security Architecture | 1 | 3 | critical | 19/100 |
| Legacy Systems Support Policy (POL-014) | Infrastructure | 2 | 0 | critical | 20/100 |
| Data Retention Policy (POL-005) | Legal | 3 | 0 | stale | 24/100 |
| Network Security Policy (POL-007) | Infrastructure | 1 | 1 | critical | 32/100 |
| Logging & Monitoring Policy (POL-011) | Security Operations | 1 | 3 | critical | 32/100 |
| Password Policy (POL-001) | IT Security | 2 | 0 | critical | 36/100 |
| Data Subject Rights & Privacy Policy (POL-006) | Legal | 2 | 0 | stale | 45/100 |
| Identity & Access Management Policy (POL-013) | Identity & Access Management | 1 | 0 | stale | 57/100 |
| Data Classification Policy (POL-004) | Compliance | 0 | 2 | stale | 60/100 |
| Acceptable Use Policy (POL-003) | Human Resources | 0 | 0 | critical | 68/100 |
| Vendor & Third-Party Risk Policy (POL-015) | Procurement | 0 | 0 | critical | 68/100 |
| Data Backup Policy (POL-016) | Infrastructure | 0 | 1 | stale | 68/100 |
| Cloud Storage Security Policy (POL-010) | Cloud Engineering | 0 | 2 | aging | 73/100 |
| Incident Response Policy (POL-012) | Security Operations | 0 | 0 | stale | 81/100 |
| Cloud Resilience & Backup Policy (POL-017) | Cloud Engineering | 0 | 0 | aging | 89/100 |
| Remote Access & CI/CD Exception Policy (POL-008) | DevOps | 0 | 0 | aging | 90/100 |
