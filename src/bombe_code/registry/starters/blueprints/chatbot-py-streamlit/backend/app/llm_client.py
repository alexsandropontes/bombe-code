"""
LLM Client - OpenAI Compatible + Gemini
Priority: OpenAI > Gemini (if both keys provided, uses OpenAI)
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMClient:
    """Client for LLM APIs (OpenAI Compatible + Gemini)"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        
        # Determine which provider to use
        if self.openai_api_key:
            self.provider = "openai"
            self._init_openai()
        elif self.gemini_api_key:
            self.provider = "gemini"
            self._init_gemini()
        else:
            raise ValueError(
                "No API key provided. Set OPENAI_API_KEY or GEMINI_API_KEY in .env"
            )
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        from openai import OpenAI
        
        if self.openai_base_url:
            self.client = OpenAI(
                api_key=self.openai_api_key,
                base_url=self.openai_base_url
            )
        else:
            self.client = OpenAI(api_key=self.openai_api_key)
    
    def _init_gemini(self):
        """Initialize Gemini client"""
        import google.generativeai as genai
        genai.configure(api_key=self.gemini_api_key)
        self.client = genai.GenerativeModel('gemini-pro')
    
    def chat(self, message: str, system_prompt: str = "") -> str:
        """Send a chat message and get response"""
        if self.provider == "openai":
            return self._chat_openai(message, system_prompt)
        else:
            return self._chat_gemini(message, system_prompt)
    
    def _chat_openai(self, message: str, system_prompt: str) -> str:
        """OpenAI compatible chat"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": message})
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    def _chat_gemini(self, message: str, system_prompt: str) -> str:
        """Gemini chat"""
        # Gemini doesn't have system prompt, so we prepend it
        full_message = message
        if system_prompt:
            full_message = f"{system_prompt}\n\n{message}"
        
        response = self.client.generate_content(full_message)
        return response.text
