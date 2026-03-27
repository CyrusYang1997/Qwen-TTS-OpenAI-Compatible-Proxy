"""
Qwen-TTS OpenAI-Compatible Proxy Server

Wraps Alibaba Cloud Qwen-TTS (DashScope) API into OpenAI-compatible
/v1/audio/speech endpoint using FastAPI.
"""

import base64
import json
import time
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from config import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    SERVER_HOST,
    SERVER_PORT,
    DEFAULT_MODEL,
    DEFAULT_VOICE,
    DEFAULT_FORMAT,
    DEFAULT_SAMPLE_RATE,
    SUPPORTED_MODELS,
    VOICE_MAP,
    FORMAT_MAP,
    CONTENT_TYPE_MAP,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Qwen-TTS OpenAI Proxy",
    description="OpenAI-compatible TTS API proxy for Alibaba Cloud Qwen-TTS",
    version="1.0.0",
)


# ─── Request / Response Models ───────────────────────────────────────────────

class TTSRequest(BaseModel):
    """OpenAI-compatible TTS request body."""
    model: str = Field(default=DEFAULT_MODEL, description="TTS model name")
    input: str = Field(..., description="Text to synthesize", max_length=10000)
    voice: str = Field(default="alloy", description="Voice name")
    response_format: Optional[str] = Field(default=None, description="Audio format: mp3, wav, pcm, opus, aac, flac")
    speed: Optional[float] = Field(default=1.0, ge=0.25, le=4.0, description="Speech speed")


class ModelObject(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "dashscope"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelObject]


# ─── Helper Functions ────────────────────────────────────────────────────────

def _resolve_api_key(request: Request) -> str:
    """Extract API key from Authorization header or fall back to env var."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer ") and len(auth_header) > 7:
        return auth_header[7:].strip()
    if DASHSCOPE_API_KEY:
        return DASHSCOPE_API_KEY
    raise HTTPException(
        status_code=401,
        detail={
            "error": {
                "message": "No API key provided. Set DASHSCOPE_API_KEY env var or pass Authorization: Bearer <key>",
                "type": "authentication_error",
                "code": "missing_api_key",
            }
        },
    )


def _resolve_voice(voice: str) -> str:
    """Map OpenAI voice name to Qwen-TTS voice, or pass through directly."""
    return VOICE_MAP.get(voice.lower(), voice)


def _resolve_format(fmt: Optional[str]) -> str:
    """Map OpenAI response_format to Qwen-TTS supported format."""
    if fmt is None:
        return DEFAULT_FORMAT
    return FORMAT_MAP.get(fmt.lower(), DEFAULT_FORMAT)


def _clamp_speed(speed: Optional[float]) -> float:
    """Convert OpenAI speed (0.25-4.0) to Qwen-TTS speech_rate (0.5-2.0)."""
    if speed is None:
        return 1.0
    # Linear mapping: OpenAI 0.25-4.0 → Qwen 0.5-2.0
    # Simplified: clamp to Qwen range
    return max(0.5, min(2.0, speed))


def _build_dashscope_payload(
    model: str,
    text: str,
    voice: str,
    audio_format: str,
    speech_rate: float,
) -> dict:
    """Build the DashScope API request payload."""
    return {
        "model": model,
        "input": {
            "text": text,
            "voice": voice,
        },
        "parameters": {
            "format": audio_format,
            "sample_rate": DEFAULT_SAMPLE_RATE,
            "speech_rate": speech_rate,
        },
    }


# ─── API Endpoints ───────────────────────────────────────────────────────────

@app.post("/v1/audio/speech")
async def create_speech(body: TTSRequest, request: Request):
    """
    OpenAI-compatible TTS endpoint.

    Converts text to speech using Qwen-TTS via DashScope API.
    Returns audio data in the requested format.
    """
    api_key = _resolve_api_key(request)
    voice = _resolve_voice(body.voice)
    audio_format = _resolve_format(body.response_format)
    speech_rate = _clamp_speed(body.speed)
    model = body.model or DEFAULT_MODEL
    if model not in SUPPORTED_MODELS:
        logger.info("Using custom/unknown model: %s", model)

    logger.info(
        "TTS request: model=%s, voice=%s, format=%s, speed=%.1f, text_len=%d",
        model, voice, audio_format, speech_rate, len(body.input),
    )

    payload = _build_dashscope_payload(model, body.input, voice, audio_format, speech_rate)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Check if client wants streaming
    accept_header = request.headers.get("Accept", "")
    want_stream = "text/event-stream" in accept_header

    if want_stream:
        return await _handle_streaming(headers, payload, audio_format)
    else:
        return await _handle_non_streaming(headers, payload, audio_format, body.response_format)


async def _handle_non_streaming(
    headers: dict,
    payload: dict,
    audio_format: str,
    original_format: Optional[str],
) -> Response:
    """Handle non-streaming TTS: call DashScope API and return complete audio."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(DASHSCOPE_BASE_URL, headers=headers, json=payload)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail={"error": {"message": "DashScope API timeout", "type": "timeout_error"}})
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail={"error": {"message": f"DashScope API request failed: {e}", "type": "upstream_error"}})

    if resp.status_code != 200:
        _handle_upstream_error(resp)

    data = resp.json()
    logger.debug("DashScope response: %s", json.dumps(data, ensure_ascii=False)[:1000])

    # Extract audio data from response
    audio_base64 = None
    audio_url = None

    output = data.get("output", {})

    # Helper to extract audio from a value that may be a dict, str, or URL
    def _extract_audio(audio_val):
        """Return (base64_str_or_None, url_or_None) from an audio value."""
        if isinstance(audio_val, dict):
            # DashScope returns: {"data": "<url>", "expires": ...}
            url = audio_val.get("data") or audio_val.get("url") or audio_val.get("audio_url")
            b64 = audio_val.get("audio_base64")
            if url and (url.startswith("http://") or url.startswith("https://")):
                return None, url
            elif b64:
                return b64, None
            elif url:
                # "data" might be base64
                return url, None
            return None, None
        elif isinstance(audio_val, str):
            if audio_val.startswith("http://") or audio_val.startswith("https://"):
                return None, audio_val
            return audio_val, None  # Assume base64
        return None, None

    # Try various response structures
    if "audio" in output:
        audio_base64, audio_url = _extract_audio(output["audio"])
    elif "audio_base64" in output:
        audio_base64 = output["audio_base64"]
    elif "audio_url" in output:
        audio_url = output["audio_url"]

    # Also check nested choices structure
    if audio_base64 is None and audio_url is None:
        choices = output.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            if "audio" in message:
                audio_base64, audio_url = _extract_audio(message["audio"])

    if audio_base64:
        audio_bytes = base64.b64decode(audio_base64)
    elif audio_url:
        # Download from URL
        logger.info("Downloading audio from URL: %s", audio_url[:100])
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                audio_resp = await client.get(audio_url)
                audio_bytes = audio_resp.content
        except Exception as e:
            raise HTTPException(status_code=502, detail={"error": {"message": f"Failed to download audio: {e}", "type": "upstream_error"}})
    else:
        logger.error("Unexpected DashScope response structure: %s", json.dumps(data, ensure_ascii=False)[:500])
        raise HTTPException(
            status_code=502,
            detail={"error": {"message": "No audio data in DashScope response", "type": "upstream_error"}},
        )

    content_type = CONTENT_TYPE_MAP.get(original_format or audio_format, "audio/mpeg")
    return Response(content=audio_bytes, media_type=content_type)


async def _handle_streaming(
    headers: dict,
    payload: dict,
    audio_format: str,
) -> StreamingResponse:
    """Handle streaming TTS: use SSE to stream audio chunks."""
    headers["X-DashScope-SSE"] = "enable"

    async def audio_stream():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", DASHSCOPE_BASE_URL, headers=headers, json=payload) as resp:
                    if resp.status_code != 200:
                        error_body = await resp.aread()
                        logger.error("DashScope streaming error: %s", error_body.decode(errors="replace")[:500])
                        return

                    buffer = ""
                    async for chunk in resp.aiter_text():
                        buffer += chunk
                        # Parse SSE events
                        while "\n\n" in buffer:
                            event_str, buffer = buffer.split("\n\n", 1)
                            for line in event_str.strip().split("\n"):
                                if line.startswith("data:"):
                                    data_str = line[5:].strip()
                                    if data_str == "[DONE]":
                                        return
                                    try:
                                        event_data = json.loads(data_str)
                                        output = event_data.get("output", {})
                                        audio_b64 = output.get("audio") or output.get("audio_base64")
                                        if not audio_b64:
                                            choices = output.get("choices", [])
                                            if choices:
                                                msg = choices[0].get("message", {})
                                                audio_info = msg.get("audio", {})
                                                if isinstance(audio_info, dict):
                                                    audio_b64 = audio_info.get("data") or audio_info.get("audio_base64")
                                                elif isinstance(audio_info, str):
                                                    audio_b64 = audio_info
                                        if audio_b64:
                                            yield base64.b64decode(audio_b64)
                                    except json.JSONDecodeError:
                                        continue
        except Exception as e:
            logger.error("Streaming error: %s", e)

    content_type = CONTENT_TYPE_MAP.get(audio_format, "audio/mpeg")
    return StreamingResponse(audio_stream(), media_type=content_type)


def _handle_upstream_error(resp: httpx.Response):
    """Parse and re-raise DashScope API errors in OpenAI error format."""
    try:
        error_data = resp.json()
        message = error_data.get("message", "") or json.dumps(error_data, ensure_ascii=False)
    except Exception:
        message = resp.text[:500]

    logger.error("DashScope API error (HTTP %d): %s", resp.status_code, message)

    status_map = {400: 400, 401: 401, 403: 403, 429: 429}
    http_status = status_map.get(resp.status_code, 502)

    raise HTTPException(
        status_code=http_status,
        detail={
            "error": {
                "message": f"DashScope API error: {message}",
                "type": "upstream_error",
                "code": str(resp.status_code),
            }
        },
    )


@app.get("/v1/models")
async def list_models():
    """List available TTS models (OpenAI-compatible format)."""
    created = int(time.time())
    models = [
        ModelObject(id=model_id, created=created)
        for model_id in SUPPORTED_MODELS
    ]
    return ModelListResponse(data=models)


@app.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    """Retrieve a specific model (OpenAI-compatible format)."""
    if model_id not in SUPPORTED_MODELS:
        raise HTTPException(status_code=404, detail={"error": {"message": f"Model '{model_id}' not found", "type": "not_found"}})
    return ModelObject(id=model_id, created=int(time.time()))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "qwen-tts-openai-proxy"}


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    if not DASHSCOPE_API_KEY:
        logger.warning(
            "DASHSCOPE_API_KEY not set. You must provide it via Authorization header or .env file."
        )

    logger.info("Starting Qwen-TTS OpenAI Proxy on %s:%d", SERVER_HOST, SERVER_PORT)
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
