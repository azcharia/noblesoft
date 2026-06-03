"""
Groq LLM Client
Ultra-low latency LLM inference using Groq API
"""
from typing import List, Dict, Optional, Any
import logging
from groq import Groq

from app.config import settings

logger = logging.getLogger(__name__)


class GroqLLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """Initialize Groq client"""
        final_key = api_key or settings.GROQ_API_KEY
        final_url = base_url or None
        
        # Fallback to prevent crash on empty key
        if not final_key:
            final_key = "placeholder_key"

        self.client = Groq(api_key=final_key, base_url=final_url, timeout=15.0)
        self.model = model or settings.GROQ_MODEL
        self.max_tokens = 2048
        self.temperature = temperature if temperature is not None else 0.2
    
    def transcribe_audio(
        self,
        audio_file: Any,
        model: str = "whisper-large-v3-turbo",
        language: str = "id",
        prompt: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio using Groq Whisper API
        
        Args:
            audio_file: Binary audio file object
            model: Whisper model to use
            language: ISO 639-1 language code (default 'id' for Indonesian)
            prompt: Optional context prompt to improve accuracy
            
        Returns:
            Transcribed text
        """
        try:
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model=model,
                language=language,
                prompt=prompt,
                response_format="json",
            )
            return transcription.text
        except Exception as e:
            logger.error(f"Groq Transcription error: {str(e)}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")
    
    async def transcribe_audio_async(
        self,
        audio_file: Any,
        model: str = "whisper-large-v3-turbo",
        language: str = "id",
        prompt: Optional[str] = None,
    ) -> str:
        """Async version of audio transcription."""
        import asyncio
        return await asyncio.to_thread(
            self.transcribe_audio, audio_file, model, language, prompt
        )

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate chat completion using Groq
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated response text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                top_p=1,
                stream=False
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    async def chat_completion_async(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Async version of chat completion
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens
        
        Returns:
            Generated response text
        """
        # Note: Groq Python SDK doesn't have native async support yet
        # We'll use sync version in async context (it's fast enough)
        return self.chat_completion(messages, temperature, max_tokens)
    
    def stream_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None
    ):
        """
        Stream chat completion (for future real-time UI)
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
        
        Yields:
            Response chunks
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            logger.error(f"Groq streaming error: {str(e)}")
            raise Exception(f"Failed to stream response: {str(e)}")
