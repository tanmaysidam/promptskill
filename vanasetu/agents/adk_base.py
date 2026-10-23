"""
VanaSetu ADK Base Agent Framework
=================================
Provides the core abstraction for Google ADK (Agent Development Kit) style agents,
featuring structured tool binding, system prompt conditioning, Pydantic schema
enforcement, and dual-mode execution (Live Google GenAI / Gemini or deterministic
CoT fallback for zero-dependency execution).
"""

from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, Optional, List, Callable, Type
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ADKAgent:
    """
    Base Agent definition following Google ADK agent patterns.
    Supports LLM inference via Google GenAI / Gemini when GEMINI_API_KEY is available,
    with a deterministic Chain-of-Thought (CoT) reasoning engine for test & offline environments.
    """

    def __init__(
        self,
        name: str,
        role_description: str,
        system_instruction: str,
        tools: Optional[List[Any]] = None,
        model_name: str = "gemini-2.5-flash",
    ):
        self.name = name
        self.role_description = role_description
        self.system_instruction = system_instruction
        self.tools = tools or []
        self.model_name = model_name
        self.api_key = os.getenv("GEMINI_API_KEY")
        self._llm_client = None

        if self.api_key:
            try:
                # Optional live Google GenAI integration
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._llm_client = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self.system_instruction,
                )
                logger.info(f"[{self.name}] Initialized live Google GenAI model {self.model_name}")
            except Exception as e:
                logger.warning(f"[{self.name}] Could not initialize GenAI client: {e}. Using deterministic engine.")

    def run_llm_call(self, prompt: str) -> Optional[str]:
        """Calls live GenAI model if configured."""
        if self._llm_client:
            try:
                response = self._llm_client.generate_content(prompt)
                return response.text
            except Exception as e:
                logger.warning(f"[{self.name}] GenAI generation failed: {e}. Falling back.")
        return None
