#!/usr/bin/env python3
"""
Vera Message Engine - HTTP Server
=================================
Exposes the 5 required endpoints under /v1/:
- GET  /v1/healthz
- GET  /v1/metadata
- POST /v1/context
- POST /v1/tick
- POST /v1/reply
"""
from __future__ import annotations
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime
from typing import Dict, Any, List

from store import ContextStore
from composer import compose
from handlers import handle_reply

# Global store singleton
store = ContextStore()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class VeraRequestHandler(BaseHTTPRequestHandler):
    server_version = "VeraEngine/1.0"

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            return {}
        raw = self.rfile.read(content_len).decode("utf-8")
        return json.loads(raw)

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        
        # 1. GET /v1/healthz
        if path in ["/v1/healthz", "/healthz"]:
            resp = {
                "status": "ok",
                "uptime_seconds": store.get_uptime_seconds(),
                "contexts_loaded": store.get_counts()
            }
            self._send_json(200, resp)
            return

        # 2. GET /v1/metadata
        if path in ["/v1/metadata", "/metadata"]:
            resp = {
                "team_name": "Team Vera Elite",
                "team_members": ["Vinayak"],
                "model": "deterministic-context-grounded-engine-v1",
                "approach": "deterministic 4-context fusion with proactive trigger ranking & stateful multi-turn intent handlers",
                "contact_email": "vinayak@example.com",
                "version": "1.0.0",
                "submitted_at": "2026-04-29T10:00:00Z"
            }
            self._send_json(200, resp)
            return

        self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")

        # 3. POST /v1/context
        if path in ["/v1/context", "/context"]:
            try:
                body = self._read_json()
                scope = body.get("scope", "")
                context_id = body.get("context_id", "")
                version = int(body.get("version", 1))
                payload = body.get("payload", {})

                accepted, err, cur_ver = store.push_context(scope, context_id, version, payload)
                if not accepted:
                    if err == "stale_version":
                        self._send_json(409, {
                            "accepted": False,
                            "reason": "stale_version",
                            "current_version": cur_ver
                        })
                    else:
                        self._send_json(400, {
                            "accepted": False,
                            "reason": err or "invalid_request"
                        })
                    return

                self._send_json(200, {
                    "accepted": True,
                    "ack_id": f"ack_{context_id}_v{version}",
                    "stored_at": datetime.utcnow().isoformat() + "Z"
                })
            except Exception as e:
                self._send_json(400, {"accepted": False, "error": str(e)})
            return

        # 4. POST /v1/tick
        if path in ["/v1/tick", "/tick"]:
            try:
                body = self._read_json()
                available = body.get("available_triggers", [])
                
                # If available_triggers is provided, evaluate those; otherwise inspect store
                trigger_ids = available if available else list(store.triggers.keys())
                actions: List[Dict[str, Any]] = []

                for tid in trigger_ids:
                    if len(actions) >= 20:
                        break

                    trg = store.triggers.get(tid)
                    if not trg:
                        continue

                    supp_key = trg.get("suppression_key", "")
                    if store.is_suppressed(supp_key):
                        continue

                    # Resolve merchant
                    mid = trg.get("merchant_id") or trg.get("payload", {}).get("merchant_id")
                    if not mid:
                        continue
                    mer = store.merchants.get(mid)
                    if not mer:
                        continue

                    # Resolve category
                    cat_slug = mer.get("category_slug", "")
                    cat = store.categories.get(cat_slug, {})

                    # Resolve customer
                    cid = trg.get("customer_id")
                    cust = store.customers.get(cid) if cid else None

                    # Compose
                    res = compose(cat, mer, trg, cust)
                    
                    conv_id = f"conv_{mid}_{tid}"
                    actions.append({
                        "conversation_id": conv_id,
                        "merchant_id": mid,
                        "customer_id": cid,
                        "send_as": res["send_as"],
                        "trigger_id": tid,
                        "template_name": f"{res['send_as']}_{trg.get('kind', 'generic')}_v1",
                        "template_params": [mer.get("identity", {}).get("name", ""), res["body"][:50]],
                        "body": res["body"],
                        "cta": res["cta"],
                        "suppression_key": res["suppression_key"],
                        "rationale": res["rationale"]
                    })
                    
                    # Mark suppressed
                    store.record_suppression(res["suppression_key"])

                self._send_json(200, {"actions": actions})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # 5. POST /v1/reply
        if path in ["/v1/reply", "/reply"]:
            try:
                body = self._read_json()
                conv_id = body.get("conversation_id", "conv_default")
                mid = body.get("merchant_id", "")
                cid = body.get("customer_id")
                from_role = body.get("from_role", "merchant")
                message = body.get("message", "")
                turn = int(body.get("turn_number", 2))

                conv_state = store.get_conversation_state(conv_id)
                conv_state["turns"] = turn
                conv_state["history"].append({"from": from_role, "body": message})

                decision = handle_reply(conv_id, mid, cid, from_role, message, turn, conv_state)
                self._send_json(200, decision)
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        self._send_json(404, {"error": "not_found"})

    def log_message(self, format, *args):
        # Terse log output
        pass

def run_server(port: int = 8080):
    server_address = ("0.0.0.0", port)
    httpd = ThreadedHTTPServer(server_address, VeraRequestHandler)
    print(f"Vera Message Engine running at http://0.0.0.0:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8080))
    run_server(port)

