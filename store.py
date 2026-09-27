#!/usr/bin/env python3
"""
Vera Message Engine - Stateful Store
====================================
Thread-safe in-memory store for:
- CategoryContexts (by slug)
- MerchantContexts (by merchant_id)
- CustomerContexts (by customer_id)
- TriggerContexts (by id)
- Active conversation states (by conversation_id)
- Suppression tracking (by suppression_key)
Supports version tracking, atomic updates, and idempotency checks.
"""
from __future__ import annotations
import threading
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

class ContextStore:
    def __init__(self):
        self._lock = threading.Lock()
        self.categories: Dict[str, Dict[str, Any]] = {}
        self.merchants: Dict[str, Dict[str, Any]] = {}
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.triggers: Dict[str, Dict[str, Any]] = {}
        
        # Track versions: (scope, context_id) -> version
        self.versions: Dict[Tuple[str, str], int] = {}
        
        # Conversation state tracking: conversation_id -> state dict
        self.conversations: Dict[str, Dict[str, Any]] = {}
        
        # Fired suppression keys: set of suppression_key
        self.suppressions: set[str] = set()
        
        self.start_time = datetime.utcnow()

    def get_uptime_seconds(self) -> int:
        return int((datetime.utcnow() - self.start_time).total_seconds())

    def get_counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "category": len(self.categories),
                "merchant": len(self.merchants),
                "customer": len(self.customers),
                "trigger": len(self.triggers),
            }

    def push_context(self, scope: str, context_id: str, version: int, payload: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Idempotent context push.
        Returns:
            (accepted, error_reason, current_version)
        """
        valid_scopes = {"category", "merchant", "customer", "trigger"}
        if scope not in valid_scopes:
            return False, "invalid_scope", None

        key = (scope, context_id)
        with self._lock:
            cur_ver = self.versions.get(key, 0)
            if version <= cur_ver:
                # Stale version / conflict
                return False, "stale_version", cur_ver

            # Atomic replace
            self.versions[key] = version
            if scope == "category":
                self.categories[context_id] = payload
            elif scope == "merchant":
                self.merchants[context_id] = payload
            elif scope == "customer":
                self.customers[context_id] = payload
            elif scope == "trigger":
                self.triggers[context_id] = payload
                
            return True, None, version

    def get_conversation_state(self, conv_id: str) -> Dict[str, Any]:
        with self._lock:
            if conv_id not in self.conversations:
                self.conversations[conv_id] = {
                    "turns": 0,
                    "auto_reply_count": 0,
                    "opted_out": False,
                    "committed": False,
                    "history": []
                }
            return self.conversations[conv_id]

    def record_suppression(self, supp_key: str):
        if supp_key:
            with self._lock:
                self.suppressions.add(supp_key)

    def is_suppressed(self, supp_key: str) -> bool:
        if not supp_key:
            return False
        with self._lock:
            return supp_key in self.suppressions
