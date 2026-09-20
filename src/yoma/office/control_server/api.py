from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from .agent import ControlServerAgent
from .voice_engine import voice_engine
from .voice_assistant import VoiceAssistant


class VoiceSynthesisRequest(BaseModel):
    text: str


def create_control_server_app(
    agent: ControlServerAgent | None = None,
) -> FastAPI:

    agent = agent or ControlServerAgent()

    app = FastAPI(
        title="YOMA Control Server API",
        version=agent.VERSION,
        description="Local management API for the YOMA Control Server Agent.",
    )

    @app.get("/")
    def root() -> dict:
        return {
            "service": "yoma-control-server",
            "version": agent.VERSION,
            "status": "ok",
        }

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "service": "yoma-control-server",
            "running": agent.running,
        }

    @app.get("/status")
    def status() -> dict:
        return agent.status()

    @app.get("/discovery")
    def discovery() -> dict:
        return agent.discover()

    @app.get("/discovery/classified")
    def classified_discovery() -> dict:
        return agent.classified_discovery()

    @app.get("/attendance/environment")
    def attendance_environment() -> dict:
        return agent.attendance_environment()
    @app.get("/hardware")
    def hardware() -> dict:
        return {"hardware": agent.hardware.status()}

    @app.get("/intelligence/status")
    def intelligence_status() -> dict:
        return agent.intelligence_status()

    @app.get("/intelligence/latest")
    def intelligence_latest():
        result = agent.intelligence_latest()
        return {
            "available": agent.intelligence_runtime is not None,
            "has_latest_result": result is not None,
            "result": result,
        }

    @app.get("/voice/status")
    def voice_status() -> dict:
        return voice_engine.status()

    @app.get("/voice/security")
    def voice_security() -> dict:
        return {
            "voice_agent_role": "input_output_only",
            "execution_authority": False,
            "self_authorized_execution": False,
            "human_approval_required": True,
        }

    @app.get("/voice/permission")
    def voice_permission() -> dict:
        from yoma.voice_runtime import WindowsMicrophoneDevice
        return WindowsMicrophoneDevice().permission_status()

    @app.post("/voice/transcribe")
    async def voice_transcribe(file: UploadFile = File(...)) -> dict:
        audio = await file.read()

        if not audio:
            raise HTTPException(status_code=400, detail="Empty audio")
        if len(audio) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Audio exceeds the 5 MiB limit")

        try:
            text = voice_engine.transcribe(audio)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Local STT failed: {exc}",
            ) from exc

        return {
            "success": True,
            "text": text,
            "engine": "faster-whisper-local",
            "external_ai_required": False,
        }

    @app.post("/voice/synthesize")
    def voice_synthesize(request: VoiceSynthesisRequest):
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Empty text")

        try:
            audio = voice_engine.synthesize(request.text.strip())
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Local TTS failed: {exc}",
            ) from exc

        return Response(
            content=audio,
            media_type="audio/wav",
            headers={"X-YOMA-Voice-Engine": "piper-local"},
        )


    @app.post("/voice/assistant")
    async def voice_assistant(file: UploadFile = File(...)):
        from .voice_assistant import VoiceAssistant

        try:
            audio = await file.read()
            if not audio:
                raise HTTPException(status_code=400, detail="Empty audio")
            if len(audio) > 5 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Audio exceeds the 5 MiB limit")
            result, output_audio = VoiceAssistant(voice_engine).process(audio)

            return Response(
                content=output_audio,
                media_type="audio/wav",
                headers={
                    "X-YOMA-Voice-Engine": result.tts_engine,
                    "X-YOMA-STT": result.stt_engine,
                    "X-YOMA-TTS": result.tts_engine,
                    "X-YOMA-Provider": result.provider,
                    "X-YOMA-Transcript": result.transcript,
                    "X-YOMA-Answer": result.answer,
                    "X-YOMA-Latency-MS": f"{result.latency_ms:.2f}",
                },
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    return app



app = create_control_server_app()
