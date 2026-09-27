#!/usr/bin/env python3
"""
magicpin AI Challenge — Candidate Submission Module (bot.py)
===========================================================
Defines the canonical compose() and respond() interface required by challenge-brief.md §7.
"""
from __future__ import annotations
from typing import Optional, Dict, Any

from composer import compose as internal_compose
from handlers import handle_reply

def compose(
    category: Dict[str, Any],
    merchant: Dict[str, Any],
    trigger: Dict[str, Any],
    customer: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Deterministic message composition from the 4-context layers.
    Inputs:
        category: dict loaded from dataset/categories/*.json
        merchant: dict loaded from dataset/merchants/*.json
        trigger: dict loaded from dataset/triggers/*.json
        customer: optional dict loaded from dataset/customers/*.json
    Returns:
        dict with keys:
            - body (str): high-compulsion WhatsApp message body
            - cta (str): call-to-action type
            - send_as (str): 'vera' or 'merchant_on_behalf'
            - suppression_key (str): for deduplication
            - rationale (str): justification connecting trigger + merchant state + compulsion lever
    """
    return internal_compose(category, merchant, trigger, customer)

def respond(
    state: Dict[str, Any],
    merchant_message: str
) -> Dict[str, Any]:
    """
    Multi-turn conversation handler for incoming merchant/customer messages.
    Inputs:
        state: dict containing conversation state (turns, history, flags)
        merchant_message: incoming message text
    Returns:
        dict with keys:
            - action: 'send', 'wait', or 'end'
            - body (optional): response message
            - cta (optional): cta type
            - wait_seconds (optional): backoff duration
            - rationale: decision explanation
    """
    conv_id = state.get("conversation_id", "conv_default")
    mid = state.get("merchant_id", "")
    cid = state.get("customer_id")
    turn = state.get("turns", 2)
    return handle_reply(conv_id, mid, cid, "merchant", merchant_message, turn, state)
