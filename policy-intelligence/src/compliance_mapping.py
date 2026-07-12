"""
compliance_mapping.py
----------------------
Translates drift/conflict/staleness findings into concrete regulatory
and framework citations, as required by the Framework Alignment section
of the problem statement (ISO 27001, NIST SP 800-53, GDPR, COBIT 2019).
"""
from __future__ import annotations

# Governance topic -> most relevant control citations.
TOPIC_CONTROLS = {
    "password_rotation": ["NIST SP 800-53 IA-5 (Authenticator Management)"],
    "mfa": ["NIST SP 800-53 IA-2 (Identification and Authentication)"],
    "encryption_at_rest": ["NIST SP 800-53 SC-28 (Protection of Information at Rest)", "GDPR Article 32"],
    "encryption_in_transit": ["NIST SP 800-53 SC-8 (Transmission Confidentiality and Integrity)", "GDPR Article 32"],
    "logging_monitoring": ["NIST SP 800-53 SI-4 (System Monitoring)", "NIST SP 800-53 AU-2 (Audit Events)"],
    "log_retention": ["NIST SP 800-53 AU-11 (Audit Record Retention)"],
    "vpn_remote_access": ["NIST SP 800-53 AC-17 (Remote Access)"],
    "data_retention": ["GDPR Article 5 (Storage Limitation)", "SOX §802"],
    "data_deletion": ["GDPR Article 17 (Right to Erasure)"],
    "backup": ["NIST SP 800-53 CP-9 (System Backup)"],
    "firewall_network": ["NIST SP 800-53 SC-7 (Boundary Protection)", "CIS Control 12 (Network Infrastructure)"],
    "admin_console_auth": ["NIST SP 800-53 IA-2(1) (MFA for Privileged Accounts)"],
    "vendor_risk": ["NIST SP 800-53 SR-6 (Supplier Assessments)"],
    "legacy_crypto": ["NIST SP 800-53 SC-13 (Cryptographic Protection)"],
    "cloud_storage_access": ["CIS Benchmarks - Cloud Storage", "GDPR Article 32"],
    "key_management": ["NIST SP 800-53 SC-12 (Cryptographic Key Establishment and Management)"],
    "access_review": ["NIST SP 800-53 AC-2 (Account Management)"],
}

# Finding-type -> governance-process citations (applies regardless of topic).
RELATIONSHIP_GOVERNANCE_CONTROLS = {
    "CONFLICT": ["ISO 27001 A.5.1 (Policies for Information Security)", "COBIT 2019 APO03 (Maintain Policy Framework)"],
    "REDUNDANT": ["COBIT 2019 APO03 (Maintain Policy Framework)"],
    "COMPLEMENTARY": [],
    "UNRELATED": [],
}

STALENESS_CONTROLS = ["ISO 27001 A.5.2 / Clause 5.2 (Review of Policies)", "NIST SP 800-53 PL-1 (Policy and Procedures)"]


def map_relationship(topic: str, relationship: str) -> list[str]:
    controls = set()
    for t in topic.split("/"):
        controls.update(TOPIC_CONTROLS.get(t, []))
    controls.update(RELATIONSHIP_GOVERNANCE_CONTROLS.get(relationship, []))
    return sorted(controls)


def map_staleness() -> list[str]:
    return list(STALENESS_CONTROLS)
