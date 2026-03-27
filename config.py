"""Configuration management for Qwen-TTS OpenAI Proxy."""

import os
from dotenv import load_dotenv

load_dotenv()

# DashScope API configuration
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL",
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
)

# Server configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# Default TTS settings
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen3-tts-flash")
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "Cherry")
DEFAULT_FORMAT = os.getenv("DEFAULT_FORMAT", "mp3")
DEFAULT_SAMPLE_RATE = int(os.getenv("DEFAULT_SAMPLE_RATE", "24000"))

# Supported models
SUPPORTED_MODELS = [
    "qwen3-tts-flash",
    "qwen3-tts-instruct-flash",
    "qwen-tts",
]

# Voice mapping: OpenAI voice name -> Qwen-TTS voice name
VOICE_MAP = {
    "alloy": "Cherry",
    "echo": "Ethan",
    "fable": "Serena",
    "onyx": "Ethan",
    "nova": "Chelsie",
    "shimmer": "Momo",
}

# Format mapping: OpenAI format -> Qwen-TTS format
FORMAT_MAP = {
    "mp3": "mp3",
    "wav": "wav",
    "pcm": "pcm",
    "opus": "mp3",   # Qwen-TTS doesn't support opus, fallback to mp3
    "aac": "mp3",    # Qwen-TTS doesn't support aac, fallback to mp3
    "flac": "wav",   # Qwen-TTS doesn't support flac, fallback to wav
}

# Content-Type mapping for audio response
CONTENT_TYPE_MAP = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
    "opus": "audio/mpeg",
    "aac": "audio/mpeg",
    "flac": "audio/wav",
}
