from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fish_audio_sdk import Session, TTSRequest
from dotenv import load_dotenv
import os
import uvicorn

# FastAPI 앱 초기화
app = FastAPI()

# 환경 변수 로드
load_dotenv(dotenv_path='.env')  # .env 파일을 로드하여 환경 변수를 설정
API_KEY = os.getenv('Fish_API_KEY')  # 환경 변수에서 API 키 가져오기
KR_MODEL_ID = os.getenv('KR_MODEL_ID')  # 한국어 모델 ID
EN_MODEL_ID = os.getenv('EN_MODEL_ID')  # 영어 모델 ID
AUDIO_FORMAT = "mp3"  # 출력 파일 형식

# 세션 초기화
session = Session(API_KEY)

# 요청 데이터 모델 정의
class TTSRequestData(BaseModel):
    file_name: str  # 저장할 파일 이름
    language: str   # 언어 (예: "KR", "EN")
    text: str       # 변환할 텍스트

def get_model_id(language: str) -> str:
    """언어에 따라 적합한 모델 ID를 반환합니다."""
    if language.upper() == "KR":
        return KR_MODEL_ID
    elif language.upper() == "EN":
        return EN_MODEL_ID
    else:
        raise ValueError(f"지원되지 않는 언어: {language}")

def generate_tts(file_name: str, model_id: str, text: str):
    """주어진 텍스트를 음성으로 변환하여 지정된 파일에 저장합니다."""
    try:
        with open(file_name, "wb") as f:
            for chunk in session.tts(TTSRequest(
                reference_id=model_id,
                text=text,
                format=AUDIO_FORMAT
            )):
                f.write(chunk)
        return file_name
    except Exception as e:
        raise Exception(f"TTS 변환 중 에러 발생: {e}")

@app.post("/generate-tts")
async def generate_tts_api(request_data: TTSRequestData):
    """TTS 생성 API 엔드포인트."""
    try:
        file_name = request_data.file_name.strip()
        language = request_data.language.strip()
        text = request_data.text.strip()

        if not file_name or not text or not language:
            raise HTTPException(status_code=400, detail="file_name, language 또는 text가 제공되지 않았습니다.")

        # 언어에 따라 모델 ID 가져오기
        try:
            model_id = get_model_id(language)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

        # TTS 생성
        generate_tts(file_name, model_id, text)

        # 생성된 파일 반환
        return FileResponse(file_name, media_type="audio/mpeg", filename=file_name)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)