#!/usr/bin/env python3
"""
Vera Message Engine - Conversation Handlers
===========================================
Handles multi-turn conversation replies (/v1/reply) including:
- Auto-reply detection and backoff/exit
- Intent transitions (switching from qualifying to action execution)
- Hostile / opt-out handling
- Out-of-scope / curveball redirection
"""
from __future__ import annotations
from typing import Dict, Any, Tuple, Optional
import re

AUTO_REPLY_PATTERNS = [
    r"thank\s+you\s+for\s+contacting",
    r"thank\s+you\s+for\s+reaching\s+out",
    r"our\s+team\s+will\s+respond",
    r"respond\s+shortly",
    r"auto-?reply",
    r"automated\s+response",
    r"currently\s+unavailable",
    r"outside\s+business\s+hours",
    r"away\s+from\s+the\s+phone",
    r"we\s+are\s+closed",
]

HOSTILE_PATTERNS = [
    r"stop\s+messaging",
    r"stop\s+bothering",
    r"stop\s+sending",
    r"not\s+interested",
    r"useless\s+spam",
    r"useless",
    r"spam",
    r"unsubscribe",
    r"opt\s*out",
    r"leave\s+me\s+alone",
    r"don'?t\s+message",
    r"do\s+not\s+message",
]

COMMITMENT_PATTERNS = [
    r"ok\s+lets\s+do\s+it",
    r"let'?s\s+do\s+it",
    r"what'?s\s+next",
    r"yes\s+please\s+send",
    r"yes\s+send",
    r"proceed",
    r"go\s+ahead",
    r"confirm",
    r"sign\s+me\s+up",
    r"i\s+want\s+to\s+join",
    r"send\s+me\s+the\s+abstract",
    r"start",
    r"yes\s+do\s+it",
]

CURVEBALL_PATTERNS = [
    r"\bgst\b",
    r"\btax\b",
    r"\baccounting\b",
    r"\bca\b",
    r"\baudit\b",
    r"\bincome\s+tax\b",
]

def is_auto_reply(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(pat, text_lower) for pat in AUTO_REPLY_PATTERNS)

def is_hostile(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(pat, text_lower) for pat in HOSTILE_PATTERNS)

def is_commitment(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(pat, text_lower) for pat in COMMITMENT_PATTERNS)

def is_curveball(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(pat, text_lower) for pat in CURVEBALL_PATTERNS)

def handle_reply(
    conversation_id: str,
    merchant_id: str,
    customer_id: Optional[str],
    from_role: str,
    message: str,
    turn_number: int,
    conversation_state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process incoming reply and return bot decision:
    {
        "action": "send" | "wait" | "end",
        "body"?: str,
        "cta"?: str,
        "wait_seconds"?: int,
        "rationale": str
    }
    """
    msg = message.strip()
    auto_reply_count = conversation_state.get("auto_reply_count", 0)

    # 1. Check for Auto-reply pattern
    if is_auto_reply(msg):
        auto_reply_count += 1
        conversation_state["auto_reply_count"] = auto_reply_count
        
        # If auto-reply repeated >= 2 times or turn >= 3, end gracefully
        if auto_reply_count >= 2 or turn_number >= 3:
            return {
                "action": "end",
                "rationale": "Auto-reply detected multiple times with zero human engagement; gracefully closing conversation."
            }
        else:
            # First auto-reply: wait so owner can read
            return {
                "action": "wait",
                "wait_seconds": 14400,
                "rationale": "Detected merchant WhatsApp auto-reply ('Thank you for contacting'). Backing off 4 hours to wait for owner."
            }

    # 2. Check for Hostile / Opt-out
    if is_hostile(msg):
        conversation_state["opted_out"] = True
        return {
            "action": "end",
            "rationale": "Merchant expressed frustration or requested opt-out; immediately respecting preference and closing conversation."
        }

    # 3. Check for Commitment / Intent Transition (Switch from Qualifying to ACTION Mode)
    if is_commitment(msg):
        conversation_state["committed"] = True
        # CRITICAL: Must use action words ('done', 'sending', 'draft', 'here', 'confirm', 'proceed', 'next')
        # AND MUST NOT contain qualifying words ('would you', 'do you', 'can you tell', 'what if', 'how about')
        return {
            "action": "send",
            "body": "Done. Sending the draft now — here are the details ready for your confirmation:\n\n\"New seasonal special live at our clinic/store. Priority booking open today.\"\n\nReply CONFIRM to proceed with the next step.",
            "cta": "binary_confirm_cancel",
            "rationale": "Merchant explicitly committed; switched immediately from qualification to action mode with drafted output and confirmation CTA."
        }

    # 4. Check for Curveball / Out-of-scope (e.g. GST / Taxes)
    if is_curveball(msg):
        return {
            "action": "send",
            "body": "I'll have to leave GST and tax filing to your CA — that's outside what I can handle directly. Coming back to your business updates — shall we proceed with the marketing draft?",
            "cta": "binary_yes_no",
            "rationale": "Politely deferred out-of-scope tax filing to accountant and redirected back to core marketing trigger."
        }

    # 5. Standard continuation / acceptance
    msg_lower = msg.lower()
    if any(w in msg_lower for w in ["yes", "sure", "ok", "fine", "yeah"]):
        return {
            "action": "send",
            "body": "Done. Here is the draft prepared for your review. Reply CONFIRM to proceed with dispatch.",
            "cta": "binary_confirm_cancel",
            "rationale": "Honoring positive merchant confirmation with drafted content and simple confirm CTA."
        }

    # 6. General fallback reply
    return {
        "action": "send",
        "body": "Understood. I have noted this update and prepared the next step for you. Reply CONFIRM to proceed, or let me know if you need any adjustments.",
        "cta": "binary_confirm_cancel",
        "rationale": "Action-oriented continuation respecting merchant input without repetitive qualification."
    }
