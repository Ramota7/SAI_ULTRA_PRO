#!/usr/bin/env python3
"""SAFE_WRITE local tool

Usage:
  python tools/safe_write.py --plan plan.json

Plan format (JSON): {"changes": [{"path": "relative/or/absolute/path","content": "..."}, ...]}

This tool enforces the guards described in the ORDER: supervisor token validation,
allowed/deny patterns, path confinement to root_dir, no remote pushes, preview diffs,
and writes artifacts/change_log.json with before/after hashes and unified diffs.

It will only write files if all guards pass.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import hashlib
import fnmatch
import difflib
from pathlib import Path
from datetime import datetime


ROOT_DIR = Path(r"C:\Proyectos\SAI_ULTRA_PRO II").resolve()
ALLOW_PATTERNS = ["*.py", "*.ps1", "*.json", "*.csv", "*.txt", "*.zip", "*.sha256"]
DENY_PATTERNS = ["*.key", "*.pem", ".env", "secrets/*", "config/keys/*"]

SCHEDULER_CONFIG = {
    "enable": True,
    "level": "user",
    "create": ["Operator 15m", "Hourly Drift", "Daily Audit", "Weekly Maintenance"],
}

NETWORK_POLICY = {"open_ports": False, "localhost_only": True}
TRADING_POLICY = {"live_orders": False, "shadow_only": True}

SUPERVISOR_TOKEN_PATH = ROOT_DIR / "sai_ultra_pro" / "config" / ".supervisor_token.ps1"
CHANGE_LOG = ROOT_DIR / "artifacts" / "change_log.json"


def sha256_text(s: bytes) -> str:
    h = hashlib.sha256()
    h.update(s)
    return h.hexdigest()


def read_supervisor_token_value() -> str | None:
    """Extract token string from .supervisor_token.ps1 if present (best-effort)."""
    try:
        txt = SUPERVISOR_TOKEN_PATH.read_text(encoding="utf-8")
        # try to extract quoted token or hex
        m = re.search(r"['\"]([A-Za-z0-9_\-]{8,})['\"]", txt)
        if m:
            return m.group(1)
        # fallback: look for 64 hex
        m2 = re.search(r"([a-fA-F0-9]{64})", txt)
        if m2:
            return m2.group(1)
        # otherwise return trimmed content
        return txt.strip()
    except Exception:
        return None


def validate_supervisor_token() -> bool:
    """Require env var SUPERVISOR_CONTROL_TOKEN and compare hashes; do not print secrets."""
    stored = read_supervisor_token_value()
    if not stored:
        print("[SAFE_WRITE] supervisor token file missing or unreadable; aborting guard")
        return False
    provided = os.environ.get("SUPERVISOR_CONTROL_TOKEN")
    if not provided:
        print("[SAFE_WRITE] SUPERVISOR_CONTROL_TOKEN env var not set; aborting")
        return False
    # compare hashes (sha256) to avoid exposing raw tokens
    if sha256_text(stored.encode("utf-8")) == sha256_text(provided.encode("utf-8")):
        return True
    # also accept raw equality (best-effort)
    if stored == provided:
        return True
    print("[SAFE_WRITE] supervisor token validation failed")
    return False


def allowed_path(p: Path) -> bool:
    """Check allow/deny patterns and confinement to ROOT_DIR"""
    try:
        p = p.resolve()
    except Exception:
        return False
    try:
        p.relative_to(ROOT_DIR)
    except Exception:
        print(f"[SAFE_WRITE] Path {p} is outside root dir {ROOT_DIR}")
        return False
    name = p.name
    # deny first
    for pattern in DENY_PATTERNS:
        if fnmatch.fnmatch(str(p.relative_to(ROOT_DIR)), pattern) or fnmatch.fnmatch(name, pattern):
            print(f"[SAFE_WRITE] Path {p} matched deny pattern {pattern}")
            return False
    # allow if any match
    for pattern in ALLOW_PATTERNS:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(p.relative_to(ROOT_DIR)), pattern):
            return True
    print(f"[SAFE_WRITE] Path {p} did not match allow patterns")
    return False


def compute_diff(old: str | None, new: str, path: str) -> str:
    old_lines = (old or "").splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile=path + ".old", tofile=path + ".new")
    return ''.join(diff)


def apply_plan(plan_path: Path):
    try:
        plan = json.loads(plan_path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"[SAFE_WRITE] Failed to read plan: {e}")
        return 2
    changes = plan.get('changes') or []
    if not isinstance(changes, list) or not changes:
        print("[SAFE_WRITE] No changes in plan")
        return 1

    # Guards
    if not validate_supervisor_token():
        print('[SAFE_WRITE] Guard failed: supervisor token')
        return 3

    # Validate all targets first
    previews = []
    for ch in changes:
        p = Path(ch.get('path'))
        if not p.is_absolute():
            p = (ROOT_DIR / p)
        if not allowed_path(p):
            print(f"[SAFE_WRITE] Guard failed for path {p}")
            return 4
        content = ch.get('content', '')
        old = None
        if p.exists():
            try:
                old = p.read_text(encoding='utf-8')
            except Exception:
                old = None
        diff = compute_diff(old, content, str(p))
        before_hash = sha256_text(old.encode('utf-8')) if old is not None else None
        after_hash = sha256_text(content.encode('utf-8'))
        previews.append({'path': str(p), 'before_hash': before_hash, 'after_hash': after_hash, 'diff': diff})

    # All guards passed -> write change_log and then apply
    CHANGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_entries = []
    for pv, ch in zip(previews, changes):
        path = Path(pv['path'])
        # write file
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(ch.get('content',''), encoding='utf-8')
        except Exception as e:
            print(f"[SAFE_WRITE] Failed to write {path}: {e}")
            return 5
        log_entries.append({
            'path': pv['path'],
            'before_hash': pv['before_hash'],
            'after_hash': pv['after_hash'],
            'diff': pv['diff']
        })

    # Write artifacts/change_log.json
    meta = {
        'applied_at': datetime.utcnow().isoformat() + 'Z',
        'applier': os.environ.get('USERNAME') or os.environ.get('USER') or 'unknown',
        'entries': log_entries,
    }
    CHANGE_LOG.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print('[SAFE_WRITE] Changes applied and logged to', CHANGE_LOG)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', required=True, help='Path to JSON plan')
    args = parser.parse_args()
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print('[SAFE_WRITE] plan file not found:', plan_path)
        return 2
    return apply_plan(plan_path)


if __name__ == '__main__':
    raise SystemExit(main())
