"""Voice ASR endpoints — optional server-side transcription fallback."""


import base64
import io
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TranscribeRequest(BaseModel):
    audio: str  # base64-encoded WAV (16 kHz mono)


@router.post("/transcribe")
async def transcribe(req: TranscribeRequest):
    """Transcribe audio to text. Requires OPENAI_API_KEY or returns 501."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=501,
            detail="服务端语音识别未配置，请使用 Chrome/Edge 浏览器内置麦克风",
        )

    try:
        raw = base64.b64decode(req.audio)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无效的音频数据: {e}") from e

    try:
        import httpx

        files = {"file": ("audio.wav", io.BytesIO(raw), "audio/wav")}
        data = {"model": "whisper-1", "language": "zh"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files=files,
                data=data,
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"转写服务错误: {resp.text[:200]}")
        body = resp.json()
        text = (body.get("text") or "").strip()
        return {"text": text}
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="需要安装 httpx 以启用服务端语音识别",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"转写失败: {e}") from e
