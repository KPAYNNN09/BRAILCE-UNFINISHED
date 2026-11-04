"""
Brailce Ollama Client
=========================

Interfaces with a locally hosted Ollama API for offline AI responses.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)


DEFAULT_SYSTEM_PROMPT = (
    "You are Brailce, a friendly voice assistant for Grade 1 Braille learners. "
    "Answer ONLY the user's actual question in 1 to 2 short, complete sentences. "
    "Never mention math unless the user asks a math question. "
    "Always finish your sentence completely."
)


class OllamaClient:
    """
    Client for interacting with local Ollama instances via HTTP.
    
    This is synchronous. The caller is responsible for wrapping
    long-running generate() calls in a background thread if needed.
    """

    def __init__(
        self,
        host: str = "http://127.0.0.1:11434",
        model: str = "llama3",
        system_prompt: Optional[str] = None,
        num_predict: int = 80,
        num_thread: int = 4,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.num_predict = max(80, num_predict)
        self.num_thread = num_thread

    def is_available(self) -> bool:
        """Check if the Ollama API is reachable."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as response:
                return response.status == 200
        except Exception as e:
            logger.debug("Ollama is_available check failed: %s", e)
            return False

    def get_installed_models(self) -> list[str]:
        """Query Ollama API to find all available installed models."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return [m.get("name") for m in data.get("models", []) if m.get("name")]
        except Exception as e:
            logger.debug("Failed to query Ollama models: %s", e)
        return []

    def resolve_model(self) -> Optional[str]:
        """
        Check installed models in Ollama and select the preferred model.
        Primary: LiquidAI/lfm2.5-1.2b-instruct (case-insensitive, matching tags)
        Alternative: llama3 (case-insensitive, matching tags)
        Returns the resolved model name, or None if neither is installed.
        """
        installed = self.get_installed_models()
        if not installed:
            # If server check fails or no models installed, check if self.model was explicitly set
            return self.model if self.model else None

        # 1. Primary: LiquidAI/lfm2.5-1.2b-instruct
        for name in installed:
            n_lower = name.lower()
            if "liquidai/lfm2.5-1.2b-instruct" in n_lower or "lfm2.5-1.2b-instruct" in n_lower:
                self.model = name
                return name

        # 2. Alternative: llama3
        for name in installed:
            n_lower = name.lower()
            if "llama3" in n_lower:
                self.model = name
                return name

        # Neither preferred model found — do not silently substitute another model
        return None

    def generate(self, prompt: str) -> Optional[str]:
        """
        Send a generation request to the Ollama model.
        
        Args:
            prompt: The user's query.
            
        Returns:
            The generated response string, or a clear spoken error message.
        """
        if not prompt or not prompt.strip():
            return None

        # Check model availability
        resolved = self.resolve_model()
        if not resolved:
            logger.error("Neither LiquidAI/lfm2.5-1.2b-instruct nor llama3 is installed in Ollama.")
            return "Required AI model is not installed. Please install LiquidAI or llama3."

        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max(80, self.num_predict),
                "num_thread": self.num_thread,
                "stop": ["\n\n", "User:", "Question:", "Human:"],
            }
        }
        if self.system_prompt:
            payload["system"] = self.system_prompt
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        logger.info("Sending request to Ollama model %r: %r", self.model, prompt)
        try:
            with urllib.request.urlopen(req, timeout=25.0) as response:
                if response.status != 200:
                    logger.error("Ollama API returned status %d", response.status)
                    return None
                
                body = response.read().decode("utf-8")
                response_json = json.loads(body)
                reply = response_json.get("response", "").strip()

                # Clean thinking tokens or markdown formatting
                import re
                reply = re.sub(r"<think>[\s\S]*?</think>", "", reply).strip()
                reply = re.sub(r"\*\*([^*]+)\*\*", r"\1", reply)
                reply = re.sub(r"^[•\*\-\+]\s+", "", reply, flags=re.MULTILINE)
                reply = re.sub(r"\s+", " ", reply).strip()

                # Strip trailing incomplete sentence fragment if model was cut off mid-sentence
                last_punct = max(reply.rfind("."), reply.rfind("!"), reply.rfind("?"))
                if last_punct != -1 and (len(reply) - 1 - last_punct) > 0:
                    reply = reply[:last_punct + 1].strip()

                logger.info("Received response from Ollama (len %d)", len(reply))
                return reply if reply else None
        except urllib.error.URLError as e:
            logger.error("Failed to connect to Ollama: %s", e)
            return None
        except Exception as e:
            logger.error("Error during Ollama generation: %s", e)
            return None
