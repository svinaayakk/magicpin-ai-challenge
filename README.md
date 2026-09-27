# Vera Message Engine — magicpin AI Challenge Submission

**Candidate**: Vinayak  
**Role**: Vera Message Engine  
**Architecture**: Deterministic 4-Context Synthesis Engine with Stateful Multi-Turn Intent & Auto-Reply Handlers  
**API Version**: 1.0.0  

---

## 1. Executive Summary & Approach

Vera is magicpin's WhatsApp assistant designed to accelerate merchant growth across retail verticals (Dentists, Salons, Restaurants, Gyms, Pharmacies). In production, WhatsApp messaging carries severe friction risks: generic 10%-off discount nudges are ignored, canned WhatsApp Business auto-replies trap conversational bots into qualification loops, and ungrounded claims destroy merchant trust.

Our solution implements an ultra-fast, strictly deterministic, and fully grounded message engine built upon magicpin's **4-Context Framework**:
1. **Category Context**: Embeds vertical voice (clinical-peer for dentists, operator-to-operator for restaurants, motivational coaching for gyms, warm styling for salons, precision compliance for pharmacies), domain taboos (e.g., zero "guaranteed/cure" promises in healthcare), and peer benchmarks (local median CTR, typical reviews, views).
2. **Merchant Context**: Extracts exact business facts without fabrication — owner first names, local trade areas (e.g. Lajpat Nagar, Indiranagar, Kapra), actual 30-day views/calls/CTR metrics, and active offer catalogs.
3. **Trigger Context**: Translates external signals (research digest publications, regulatory changes, IPL match-day dynamics, upcoming festivals) and internal shifts (performance drops, review milestones, dormant streaks, lapse windows) into an urgent, verifiable "why now".
4. **Customer Context**: Personalizes customer-facing outreach with name, relationship duration, Hindi-English code-mixing preferences, and specific time slots.

---

## 2. Key Architecture & Compulsion Levers

```
                 ┌────────────────────────────────────────────────────────┐
                 │                   4 Context Layers                     │
                 │ [Category]      [Merchant]      [Trigger]   [Customer] │
                 └───────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
                 ┌────────────────────────────────────────────────────────┐
                 │       Deterministic Context Grounding & Synthesis      │
                 │   - Salutation & Category Voice Normalizer             │
                 │   - Concrete Fact & Performance Metric Injector        │
                 │   - Single Low-Friction Binary/Slot CTA Selector       │
                 │   - Zero-URL & Anti-Taboo Hard Guardrails              │
                 └───────────────────────────┬────────────────────────────┘
                                             │
                        ┌────────────────────┴───────────────────┐
                        ▼                                        ▼
             Outbound Proactive Tick                     Inbound Merchant Reply
             (/v1/tick)                                  (/v1/reply)
             - Up to 20 actions/tick                     - Auto-Reply Detector (Backoff & Exit)
             - Dedup via suppression_key                 - Commitment Detector (ACTION Mode)
             - Send-as: vera vs merchant_on_behalf       - Hostility / Opt-out Handler
```

### Compulsion Levers Implemented
- **Effort Externalization & Reciprocity**: "Want me to draft X? Ready in 5 min" lowers cognitive load from decision-making to a single low-friction commitment.
- **Counter-Intuitive Domain Intelligence**: During Saturday IPL matches, instead of pushing dine-in discounts (which suffer a -12% cover drop as fans watch at home), Vera advises delivery-only BOGO pizza promotions.
- **Verifiable Provenance**: Research and regulatory alerts cite official sources (`JIDA Oct 2026, p.14`, `DCI circular 2026-11-04`), clinical trial sample sizes (`2,100 patients`), and specific dose thresholds (`1.5 → 1.0 mSv`).
- **Binary & Slot CTAs**: Restricts requests to single binary choices (`Reply YES`, `Reply CONFIRM`) or discrete time slots (`Reply 1 for Wed 6pm, 2 for Thu 5pm`).

---

## 3. Replay Test & Multi-Turn State Machine (`/v1/reply`)

To pass hostile, auto-reply, and intent transition edge-cases without turn-burning:
1. **Auto-Reply Detection**: Matches canned WhatsApp Business templates ("Thank you for contacting..."). Turn 1 triggers a wait backoff (`wait_seconds: 14400`) so the human owner can review. If repeated >= 2 times, the conversation ends gracefully with zero spam.
2. **Intent Transition (The Qualification Trap Fix)**: When a merchant expresses commitment ("Ok lets do it. Whats next?", "proceed", "send me the abstract"), Vera **instantly transitions from qualification to ACTION execution mode** ("Done. Sending the draft now... Reply CONFIRM to proceed"). It strictly suppresses qualification phrasing ("would you", "do you", "how about").
3. **Hostility & Opt-Out**: Flags words like "stop", "useless", "spam", immediately ending the conversation and respecting opt-out.
4. **Out-of-Scope Redirection**: Politely defers curveballs (e.g. GST/tax filing) to their accountant while steering back to the marketing trigger.

---

## 4. Engineering & Trade-Offs

- **Deterministic Rule & Retrieval Core vs. Pure LLM**: While an LLM prompt can be creative, high-frequency merchant communication requires deterministic reliability, strict adherence to zero-fabrication rules, sub-millisecond execution, and immunity to token timeouts. Our engine executes in **< 1ms per action** with zero external API dependencies.
- **Zero URL Policy**: Strict adherence to WhatsApp business policies; all navigation actions are driven through chat replies rather than external web links.
- **Idempotent Context Stores**: Thread-safe storage with atomic version updates preventing race conditions during concurrent judge pushes.

---

## 5. What Additional Context Would Help Most

1. **Merchant Channel Response Affinities**: Data on whether a merchant prefers evening replies vs morning digests, and past acceptance rates on specific offer types.
2. **Catalog Margin Data**: Knowing gross margins on services (e.g., aligners vs scaling) to recommend the highest-margin campaign during recovery windows.
3. **Local Event Calenders**: Hyperlocal neighborhood footfall indicators (marathons, road closures, power cuts) for timely tactical promotions.

---

## 6. Verification & Endpoints Reference

The bot exposes all 5 required endpoints under `/v1`:
- `GET  /v1/healthz`: Liveness and contexts-loaded count probe.
- `GET  /v1/metadata`: Team identity and architecture summary.
- `POST /v1/context`: Idempotent context ingestion with atomic version replacement.
- `POST /v1/tick`: Proactive trigger evaluation producing up to 20 grounded actions.
- `POST /v1/reply`: Multi-turn conversational replays with state machine.
