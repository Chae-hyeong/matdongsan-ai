from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from melo.api import TTS
import os

app = FastAPI()

# 전역 TTS 모델 초기화
models = {}

class GenerateRequest(BaseModel):
    """
    JSON 요청 데이터 모델 정의
    """
    filename: str
    language: str
    text: str

@app.on_event("startup")
async def load_models():
    """
    FastAPI 서버 시작 시 TTS 모델을 로드합니다.
    """
    global models
    try:
        # 언어별 모델 초기화
        models['KR'] = TTS(language="KR", device="cpu")  # 한국어 모델
        models['EN'] = TTS(language="EN", device="auto")  # 영어 모델
        print("TTS Models loaded successfully.")
    except Exception as e:
        print(f"Error loading TTS models: {e}")
        raise RuntimeError("Failed to load TTS models.")

@app.post("/generate")
async def generate_wav(request: GenerateRequest):
    """
    JSON 요청 데이터를 기반으로 언어를 판단하여 음성 파일(WAV)을 생성하고 반환합니다.
    """
    global models

    try:
        # 요청 데이터 가져오기
        filename = request.filename
        language = request.language
        text = request.text

        # 언어 검증
        if language not in models:
            raise HTTPException(status_code=400, detail="Unsupported language. Use 'KR' or 'EN'.")

        # 선택된 모델 가져오기
        model = models[language]
        speaker_ids = model.hps.data.spk2id

        # 파일 확장자 확인 및 경로 설정
        if not filename.endswith(".wav"):
            filename += ".wav"
        output_path = os.path.join(os.getcwd(), filename)

        # Speed 설정
        speed = 1.0

        # 언어별 처리 분기
        if language == "KR":
            # 한국어 모델 실행
            model.tts_to_file(
                text=text,
                speaker_id=speaker_ids['KR'],  # 한국어 화자 ID
                output_path=output_path,
                speed=speed
            )
        elif language == "EN":
            # 영어 모델 실행
            model.tts_to_file(
                text=text,
                speaker_id=speaker_ids['EN-Default'],  # 영어 기본 화자 ID
                output_path=output_path,
                speed=speed
            )

        # 생성된 파일 반환
        if os.path.exists(output_path):
            return FileResponse(output_path, media_type="audio/wav", filename=filename)
        else:
            raise HTTPException(status_code=500, detail="Failed to generate WAV file.")
    except Exception as e:
        print(f"Error during WAV generation: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(e)})