"""
NavSakhi Assistant Intent & Relevance Layer (Phase 51.51)

Classifies user inquiries into five structured intent groups:
1. SAFETY: Harassment, emergency, fear, dark areas, personal protection.
2. JOURNEY_TRANSIT: Chennai transit modes, stops, lines, routes, landmarks, schedules.
3. NAVSAKHI_SUPPORT: Application usage, account, emergency contacts, safety score methodology.
4. SMALL_TALK: Greetings, gratitude, friendly travel-companion interaction.
5. OFF_TOPIC: Unrelated general knowledge (programming, foreign politics, recipes).

Policy:
- Safety and transit queries are prioritized and never rejected.
- Mixed-intent messages containing any safety or transit terms are classified as SAFETY or JOURNEY_TRANSIT.
- Small talk is handled with natural, responsive companion replies without consuming external API quota.
- Harmless off-topic questions receive a concise 1-2 sentence response with gentle redirection.
"""

import re
from enum import Enum
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel


class AssistantIntent(str, Enum):
    SAFETY = "SAFETY"
    JOURNEY_TRANSIT = "JOURNEY_TRANSIT"
    NAVSAKHI_SUPPORT = "NAVSAKHI_SUPPORT"
    SMALL_TALK = "SMALL_TALK"
    COMPANION_EMPATHY = "COMPANION_EMPATHY"
    OFF_TOPIC = "OFF_TOPIC"


IntentCategory = AssistantIntent


class IntentClassificationResult(BaseModel):
    intent: AssistantIntent
    confidence: float
    is_supported_domain: bool
    requires_external_llm: bool
    direct_response: Optional[str] = None
    redirection_note: Optional[str] = None


class AssistantIntentClassifier:
    """Lightweight, deterministic, offline intent and relevance classifier."""

    # Keywords strictly prioritized for acute physical danger, harassment, stalking, or distress
    ACUTE_DANGER_KEYWORDS = [
        "following me", "follow me", "stalk", "stalker", "danger", "attack",
        "threat", "trouble", "screaming", "hurt", "in danger", "protect me",
        "trapped", "harass", "harassment", "molest", "creepy", "unsafe", "dark",
        "suspicious", "scared"
    ]

    # Travel anxiety and nervousness when traveling alone (without acute danger/stalker)
    TRAVEL_ANXIETY_KEYWORDS = [
        "nervous", "anxious", "travel anxiety", "uneasy", "feeling alone",
        "scared of travelling", "scared of traveling", "nervous about"
    ]

    # Companionship, emotional presence, and journey partner requests
    COMPANION_KEYWORDS = [
        "companion", "partner", "be with me", "stay with me", "talk to me",
        "keep me company", "walk with me", "accompany me", "accompany",
        "travel partner", "journey partner", "with me through out", "with me throughout",
        "just want a companion", "need a companion", "be my companion", "travel friend",
        "by my side"
    ]

    # General emergency and helpline keywords
    EMERGENCY_KEYWORDS = [
        "emergency", "police", "sos", "helpline", "112", "1091"
    ]

    # General safety awareness, considerations, and precaution inquiries
    SAFETY_AWARENESS_KEYWORDS = [
        "aware", "be aware", "look out", "watch out", "safety tip", "safety tips",
        "precaution", "precautions", "stay safe", "staying safe", "keeping safe",
        "safe travel", "safety consideration", "safety considerations", "advice",
        "safety advice", "guidelines", "safety guidelines", "caution", "vigilant"
    ]

    # Specific indicators of account / settings configuration for emergency contacts
    CONTACT_CONFIG_INDICATORS = [
        "add", "update", "edit", "delete", "remove", "change", "set up",
        "setup", "configure", "manage", "save", "how to add", "how do i add",
        "how do i update", "how to update", "how do i set up", "how to set up",
        "where do i add", "where can i add", "account", "settings", "profile"
    ]

    # Keywords for JOURNEY & CHENNAI TRANSIT
    TRANSIT_KEYWORDS = [
        "route", "bus", "metro", "suburban", "train", "mrts", "mtc", "station",
        "stop", "fare", "ticket", "reach", "travel", "navigate", "distance", "eta",
        "transit", "schedule", "timing", "chennai", "central", "egmore", "tambaram",
        "guindy", "saidapet", "koyambedu", "beach", "vit", "iit", "t nagar",
        "velachery", "airport", "omr", "ecr", "anna nagar", "adyar", "sholinganallur"
    ]

    # Keywords for NAVSAKHI SUPPORT & APPLICATION
    SUPPORT_KEYWORDS = [
        "navsakhi", "safeshe", "score", "safety score", "lightgbm", "model",
        "what is navsakhi", "what is safeshe", "what can you do", "features",
        "account", "login", "register", "signup", "signin", "password",
        "profile", "settings", "guest", "how to use", "how do i use",
        "guide", "tutorial"
    ]

    # Keywords for SMALL TALK & GREETINGS
    SMALL_TALK_KEYWORDS = [
        "hi", "hello", "hey", "good morning", "good evening", "good afternoon",
        "namaste", "vanakkam", "thanks", "thank you", "bye", "goodbye", "how are you",
        "who are you", "what's up", "whats up", "great", "nice"
    ]

    # Pre-crafted deterministic off-topic knowledge capsules (1-2 sentences)
    OFF_TOPIC_KNOWLEDGE = {
        "capital of france": "The capital of France is Paris, located along the Seine River.",
        "capital of india": "The capital of India is New Delhi, the seat of the government of India.",
        "who wrote hamlet": "Hamlet was written by the English playwright William Shakespeare around 1600.",
        "speed of light": "The speed of light in a vacuum is approximately 299,792 kilometers per second (about 300,000 km/s).",
    }

    @classmethod
    def classify(cls, query: str, history: Optional[Any] = None) -> IntentClassificationResult:
        clean_q = query.strip().lower()
        if not clean_q:
            return IntentClassificationResult(
                intent=AssistantIntent.SMALL_TALK,
                confidence=1.0,
                is_supported_domain=True,
                requires_external_llm=False,
                direct_response="Hello! I am your NavSakhi travel companion. How can I help you navigate Chennai safely today?"
            )

        words = set(re.findall(r"\b\w+\b", clean_q))

        # Check conversation history for prior companionship context
        had_prior_companion_turn = False
        if history and isinstance(history, list):
            for h in history[-3:]:
                h_content = str(h.get("content", "")).lower() if isinstance(h, dict) else ""
                if any(ck in h_content for ck in cls.COMPANION_KEYWORDS):
                    had_prior_companion_turn = True
                    break

        # 1. ACUTE SAFETY: Highest Priority (Immediate physical danger, harassment, stalking, feeling unsafe)
        # Stalking or physical distress overrides travel anxiety or settings
        is_stalking_or_attack = any(w in clean_q for w in ["following me", "follow me", "stalk", "stalker", "attack", "threat", "screaming", "hurt", "in danger", "protect me", "trapped"])
        if is_stalking_or_attack or (any(kw in clean_q for kw in cls.ACUTE_DANGER_KEYWORDS) and not any(aq in clean_q for aq in cls.TRAVEL_ANXIETY_KEYWORDS)):
            acute_response = (
                "I hear you, and your immediate safety is the top priority. If someone is following you or you feel in danger:\n\n"
                "1. **Move to a Staffed Safe Haven Immediately:** Walk directly into an open shop, well-lit café, metro station customer counter, or busy bus shelter nearby.\n"
                "2. **Alert People Nearby:** Let staff or commuters know you need help or that someone is following you.\n"
                "3. **Call Emergency Services:**\n"
                "   - **112** (National Emergency Helpline)\n"
                "   - **1091** (Tamil Nadu Women Helpline)\n"
                "4. **Share Live Route:** Tap the SOS button in NavSakhi to alert your emergency contacts.\n\n"
                "Are you in a safe, staffed area with people around you right now?"
            )
            return IntentClassificationResult(
                intent=AssistantIntent.SAFETY,
                confidence=0.99,
                is_supported_domain=True,
                requires_external_llm=True,
                direct_response=acute_response
            )

        # 2. EMERGENCY CONTACTS: Distinguish account configuration from emergency distress
        if "emergency contact" in clean_q or "emergency contacts" in clean_q:
            if any(ind in clean_q for ind in cls.CONTACT_CONFIG_INDICATORS):
                return IntentClassificationResult(
                    intent=AssistantIntent.NAVSAKHI_SUPPORT,
                    confidence=0.95,
                    is_supported_domain=True,
                    requires_external_llm=True
                )
            return IntentClassificationResult(
                intent=AssistantIntent.SAFETY,
                confidence=0.96,
                is_supported_domain=True,
                requires_external_llm=True
            )

        # 3. GENERAL EMERGENCY & HELPLINES (112, 1091, police, SOS)
        if any(kw in clean_q for kw in cls.EMERGENCY_KEYWORDS):
            return IntentClassificationResult(
                intent=AssistantIntent.SAFETY,
                confidence=0.97,
                is_supported_domain=True,
                requires_external_llm=True
            )

        # 3b. SAFETY AWARENESS & PRECAUTIONS (Considerations, tips, what to look out for)
        if any(kw in clean_q for kw in cls.SAFETY_AWARENESS_KEYWORDS) or any(w in clean_q for w in ["take care", "look out", "watch out", "should i take care"]):
            awareness_fallback = (
                "When traveling across Chennai, here are a few practical considerations:\n\n"
                "1. **Check Transit Timing:** Verify bus or metro schedules in advance to avoid long waits at quiet stops.\n"
                "2. **Stay Connected:** Keep your phone charged and consider sharing your journey details with a trusted person.\n"
                "3. **Prefer Familiar Corridors:** Choose active, well-populated routes near open businesses and transit hubs, especially after dark.\n"
                "4. **Emergency Helplines:** Remember that **112** (National Emergency) and **1091** (Tamil Nadu Women Helpline) are available 24/7."
            )
            return IntentClassificationResult(
                intent=AssistantIntent.SAFETY,
                confidence=0.94,
                is_supported_domain=True,
                requires_external_llm=True,
                direct_response=awareness_fallback
            )

        # 4. TRAVEL ANXIETY & NERVOUSNESS (Calm reassurance without false emergency alarm)
        if any(kw in clean_q for kw in cls.TRAVEL_ANXIETY_KEYWORDS) and not is_stalking_or_attack:
            anxiety_resp = (
                "It is completely normal to feel nervous or uneasy when traveling alone, especially in unfamiliar or quiet areas. "
                "Take a slow breath — you are not alone, and I am right here with you in your phone.\n\n"
                "A reassuring practical step is to stay along major, well-lit transit corridors like the Chennai Metro or primary arterial MTC bus routes, "
                "and choose a seat near the driver, conductor, or in the designated women's section. You can also share your live journey route with someone you trust.\n\n"
                "Where are you traveling right now? I would be glad to check verified routes or just stay in this chat with you."
            )
            return IntentClassificationResult(
                intent=AssistantIntent.COMPANION_EMPATHY,
                confidence=0.95,
                is_supported_domain=True,
                requires_external_llm=True,
                direct_response=anxiety_resp
            )

        # 5. COMPANIONSHIP & JOURNEY PARTNER (Empathetic, digital companion presence)
        if any(kw in clean_q for kw in cls.COMPANION_KEYWORDS) or any(w in clean_q for w in ["will you be my sakhi", "be my sakhi", "will you travel with me", "travel with me"]):
            companion_resp = (
                "Of course—I can be your digital travel companion and journey partner while you plan and monitor your route. "
                "I can't physically accompany you or guarantee safety, but I can help you compare routes, "
                "track transit timing, and understand the available safety information. Where are you heading today?"
            )
            return IntentClassificationResult(
                intent=AssistantIntent.COMPANION_EMPATHY,
                confidence=0.96,
                is_supported_domain=True,
                requires_external_llm=True,
                direct_response=companion_resp
            )

        # 6. NAVSAKHI APPLICATION SUPPORT (Features, Account, LightGBM Model, Scoring)
        if any(kw in clean_q for kw in cls.SUPPORT_KEYWORDS):
            support_resp = None
            if any(sk in clean_q for sk in ["score", "lightgbm", "safety score", "model", "how is score", "based on"]):
                support_resp = (
                    "NavSakhi route safety scores are calculated using a frozen LightGBM regression model that evaluates objective "
                    "road environmental infrastructure features (including highway classification, road width, junction complexity, "
                    "and verified commercial service density). We also calculate an independent Night Activity Score based on confirmed "
                    "open places, transit nodes, and surveillance cameras along your route. It represents an environmental safety proxy, "
                    "not an empirical crime prediction or guarantee of personal safety."
                )
            return IntentClassificationResult(
                intent=AssistantIntent.NAVSAKHI_SUPPORT,
                confidence=0.95,
                is_supported_domain=True,
                requires_external_llm=True,
                direct_response=support_resp
            )

        # 7. JOURNEY & TRANSIT: Core Mobility Purpose (Routes, Bus, Metro, Chennai Travel)
        if any(kw in clean_q for kw in cls.TRANSIT_KEYWORDS):
            return IntentClassificationResult(
                intent=AssistantIntent.JOURNEY_TRANSIT,
                confidence=0.92,
                is_supported_domain=True,
                requires_external_llm=True
            )

        # 8. SMALL TALK
        if any(clean_q == kw or clean_q.startswith(kw + " ") or kw in words for kw in cls.SMALL_TALK_KEYWORDS) or any(w in clean_q for w in ["how are you", "how are u"]):
            if any(w in clean_q for w in ["how are you", "how are u"]):
                greeting_resp = "I'm doing well, thank you for asking! How is your travel planning going today?"
            elif any(t in words for t in ["thanks", "thank"]):
                greeting_resp = "You are very welcome! Safe travels across Chennai. Let me know if you need route advice or emergency contacts."
            else:
                greeting_resp = "Hello! I am your NavSakhi travel companion. How can I help you navigate Chennai safely today?"
            return IntentClassificationResult(
                intent=AssistantIntent.SMALL_TALK,
                confidence=0.90,
                is_supported_domain=True,
                requires_external_llm=False,
                direct_response=greeting_resp
            )

        # 9. OFF_TOPIC (Harmless general questions: strictly 1-2 concise sentences with gentle redirection)
        brief_answer = None
        for key, ans in cls.OFF_TOPIC_KNOWLEDGE.items():
            if key in clean_q:
                brief_answer = ans
                break

        redirection = "As your NavSakhi companion, I specialize in personal safety and Chennai transit."
        if brief_answer:
            full_off_topic_reply = f"{brief_answer} {redirection}"
        else:
            full_off_topic_reply = "I specialize as NavSakhi's travel companion for Chennai personal safety and transit. How can I help you navigate safely today?"

        return IntentClassificationResult(
            intent=AssistantIntent.OFF_TOPIC,
            confidence=0.85,
            is_supported_domain=False,
            requires_external_llm=False,
            direct_response=full_off_topic_reply,
            redirection_note=redirection
        )


global_intent_classifier = AssistantIntentClassifier()
