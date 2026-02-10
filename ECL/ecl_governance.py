#!/usr/bin/env python3
"""
ECL Governance Module - Data Retention & Lifecycle Policies
Implements configurable data retention, deletion, and audit policies.

Lyzr Criteria Addressed:
  - Data retention and deletion policies
  - Audit trail preservation
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime, timedelta


# ============================================================
# SECTION 1: GOVERNANCE POLICIES
# ============================================================

@dataclass
class RetentionPolicy:
    """Defines how long data is retained and when it's purged."""
    policy_name: str
    retention_days: int = 365           # Default: keep 1 year
    audit_retention_days: int = 2555    # Default: keep audit trails 7 years
    trace_retention_days: int = 730     # Default: keep traces 2 years
    auto_purge: bool = False            # Auto-delete expired data
    require_approval_for_deletion: bool = True
    encrypted_at_rest: bool = False     # Flag for encryption enforcement
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DeletionRecord:
    """Records a data deletion event for compliance."""
    record_id: str
    deleted_at: str
    deleted_by: str = "system"
    policy_name: str = ""
    items_deleted: int = 0
    item_type: str = ""
    reason: str = ""


# ============================================================
# SECTION 2: GOVERNANCE ENGINE
# ============================================================

class GovernanceEngine:
    """
    Manages data lifecycle, retention policies, and compliance records.
    """

    def __init__(self, policy: RetentionPolicy = None, governance_dir: str = "governance"):
        self.policy = policy or RetentionPolicy(policy_name="default")
        self.governance_dir = governance_dir
        self.deletion_log: List[DeletionRecord] = []
        os.makedirs(governance_dir, exist_ok=True)

    def get_policy(self) -> Dict:
        """Return current retention policy as dict."""
        return asdict(self.policy)

    def set_policy(self, **kwargs):
        """Update policy fields."""
        for k, v in kwargs.items():
            if hasattr(self.policy, k):
                setattr(self.policy, k, v)
        self._save_policy()

    def _save_policy(self):
        """Persist policy to disk."""
        filepath = os.path.join(self.governance_dir, "retention_policy.json")
        with open(filepath, 'w') as f:
            json.dump(asdict(self.policy), f, indent=2)

    def check_retention(self, item_timestamp: str, item_type: str = "data") -> Dict:
        """
        Check if an item should be retained or can be purged.
        """
        item_dt = datetime.fromisoformat(item_timestamp)
        now = datetime.now()
        age_days = (now - item_dt).days

        if item_type == "audit" or item_type == "trace":
            max_days = self.policy.audit_retention_days
        elif item_type == "trace":
            max_days = self.policy.trace_retention_days
        else:
            max_days = self.policy.retention_days

        expired = age_days > max_days

        return {
            "item_timestamp": item_timestamp,
            "item_type": item_type,
            "age_days": age_days,
            "max_retention_days": max_days,
            "expired": expired,
            "action": "PURGE" if expired else "RETAIN",
        }

    def purge_expired_traces(self, traces_dir: str = "traces", dry_run: bool = True) -> Dict:
        """
        Scan traces directory and purge expired trace files.
        In dry_run mode, only reports what would be deleted.
        """
        if not os.path.isdir(traces_dir):
            return {"purged": 0, "retained": 0, "dry_run": dry_run}

        purged = 0
        retained = 0

        for fname in os.listdir(traces_dir):
            if not fname.endswith('.json'):
                continue

            fpath = os.path.join(traces_dir, fname)
            stat = os.stat(fpath)
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            age_days = (datetime.now() - mod_time).days

            if age_days > self.policy.trace_retention_days:
                if not dry_run:
                    os.remove(fpath)
                    self.deletion_log.append(DeletionRecord(
                        record_id=f"del_{int(time.time() * 1000)}",
                        deleted_at=datetime.now().isoformat(),
                        policy_name=self.policy.policy_name,
                        items_deleted=1,
                        item_type="trace",
                        reason=f"Expired: {age_days} days > {self.policy.trace_retention_days} max",
                    ))
                purged += 1
            else:
                retained += 1

        result = {"purged": purged, "retained": retained, "dry_run": dry_run}

        if not dry_run:
            self._save_deletion_log()

        return result

    def _save_deletion_log(self):
        """Persist deletion log."""
        filepath = os.path.join(self.governance_dir, "deletion_log.json")
        existing = []
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                existing = json.load(f)

        existing.extend([asdict(r) for r in self.deletion_log])
        with open(filepath, 'w') as f:
            json.dump(existing, f, indent=2)
        self.deletion_log.clear()

    def compliance_report(self) -> Dict:
        """Generate a compliance status report."""
        deletion_count = 0
        deletion_log_path = os.path.join(self.governance_dir, "deletion_log.json")
        if os.path.exists(deletion_log_path):
            with open(deletion_log_path, 'r') as f:
                deletion_count = len(json.load(f))

        return {
            "policy": asdict(self.policy),
            "total_deletions_logged": deletion_count,
            "governance_dir": self.governance_dir,
            "generated_at": datetime.now().isoformat(),
        }


# ============================================================
# SECTION 3: SELF-TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  ECL Governance Engine")
    print("=" * 60)

    engine = GovernanceEngine()
    policy = engine.get_policy()
    print(f"\n  Policy: {policy['policy_name']}")
    print(f"  Data retention: {policy['retention_days']} days")
    print(f"  Audit retention: {policy['audit_retention_days']} days")
    print(f"  Trace retention: {policy['trace_retention_days']} days")
    print(f"  Auto-purge: {policy['auto_purge']}")

    # Check retention on a hypothetical item
    check = engine.check_retention(datetime.now().isoformat(), "data")
    print(f"\n  Retention check: {check['action']} (age: {check['age_days']} days)")

    report = engine.compliance_report()
    print(f"  Compliance report generated at: {report['generated_at']}")
    print("=" * 60)
