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

    # Keywords strictly prioritized for acute danger, harassment, stalking, or distress
    ACUTE_SAFETY_KEYWORDS = [
        "unsafe", "danger", "scared", "alone", "nervous", "anxious", "fear",
        "uncomfortable", "following me", "follow me", "harass", "stalk", "dark",
        "threat", "trouble", "attack", "safe haven", "safe zone",
        "alert", "urgent", "in danger", "protect me", "screaming", "hurt",
        "suspicious", "creepy", "trapped"
    ]

    # General emergency and helpline keywords
    EMERGENCY_KEYWORDS = [
        "emergency", "police", "sos", "helpline", "112", "1091"
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
    def classify(cls, query: str) -> IntentClassificationResult:
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

        # 1. ACUTE SAFETY: Highest Priority (Immediate danger, harassment, fear, feeling unsafe)
        # Always takes precedence even if the message mentions contacts or account settings
        if any(kw in clean_q for kw in cls.ACUTE_SAFETY_KEYWORDS):
            return IntentClassificationResult(
                intent=AssistantIntent.SAFETY,
                confidence=0.98,
                is_supported_domain=True,
                requires_external_llm=True
            )

        # 2. EMERGENCY CONTACTS: Distinguish account configuration from emergency distress
        if "emergency contact" in clean_q or "emergency contacts" in clean_q:
            # If the user specifically asks how to add/edit/manage contacts in settings without distress
            if any(ind in clean_q for ind in cls.CONTACT_CONFIG_INDICATORS):
                return IntentClassificationResult(
                    intent=AssistantIntent.NAVSAKHI_SUPPORT,
                    confidence=0.95,
                    is_supported_domain=True,
                    requires_external_llm=True
                )
            # Otherwise, treat ambiguous requests conservatively as SAFETY
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

        # 4. NAVSAKHI APPLICATION SUPPORT (Features, Account, LightGBM Model, Scoring)
        if any(kw in clean_q for kw in cls.SUPPORT_KEYWORDS):
            return IntentClassificationResult(
                intent=AssistantIntent.NAVSAKHI_SUPPORT,
                confidence=0.95,
                is_supported_domain=True,
                requires_external_llm=True
            )

        # 5. JOURNEY & TRANSIT: Core Mobility Purpose (Routes, Bus, Metro, Chennai Travel)
        if any(kw in clean_q for kw in cls.TRANSIT_KEYWORDS):
            return IntentClassificationResult(
                intent=AssistantIntent.JOURNEY_TRANSIT,
                confidence=0.92,
                is_supported_domain=True,
                requires_external_llm=True
            )

        # 6. SMALL TALK
        if any(clean_q == kw or clean_q.startswith(kw + " ") or kw in words for kw in cls.SMALL_TALK_KEYWORDS):
            greeting_resp = (
                "Hello! I am your NavSakhi travel companion. "
                "I can help you check safe corridors, transit options (Metro, Suburban rail, MTC buses), "
                "and emergency safe havens across Chennai. Where are you heading today?"
            )
            if any(t in words for t in ["thanks", "thank"]):
                greeting_resp = "You are very welcome! Safe travels across Chennai. Let me know if you need route advice or emergency contacts."
            return IntentClassificationResult(
                intent=AssistantIntent.SMALL_TALK,
                confidence=0.90,
                is_supported_domain=True,
                requires_external_llm=False,
                direct_response=greeting_resp
            )

        # 7. OFF_TOPIC (Harmless general questions: strictly 1-2 concise sentences with gentle redirection)
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
