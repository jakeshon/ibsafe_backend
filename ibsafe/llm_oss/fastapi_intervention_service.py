from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import sys
import torch
import gc
import time
import pandas as pd
import numpy as np
from crewai import LLM

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(__file__))

from backend.ibsafe.llm_oss.make_prompt_korean_org import build_prompt_ko_from_csv, make_sleep_prompt_ko, make_exercise_prompt_ko
from rag_utility import get_embedder, get_faiss_and_chunks

app = FastAPI(title="IBS 중재 서비스", description="Ollama gpt-oss-20b를 이용한 IBS 환자 중재 서비스")

# Pydantic 모델들
class InterventionRequest(BaseModel):
    allergies: List[str] = []
    restrictions: List[str] = []
    recent_3days: List[str] = []
    today_sleep: float
    week_step: List[int]
    use_rag: bool = True

class InterventionResponse(BaseModel):
    diet_recommendation: str
    sleep_recommendation: str
    exercise_recommendation: str
    processing_time: float

# 전역 변수로 LLM 인스턴스 관리
llm_instance = None

def get_llm_instance():
    """LLM 인스턴스를 싱글톤으로 관리"""
    global llm_instance
    if llm_instance is None:
        llm_instance = LLM(
            model="ollama/gpt-oss:20b",
            base_url="http://127.0.0.1:11434",
            api_key="ollama"
        )
    return llm_instance

def run_inference(
    test_llm,
    allergies: List[str],
    restrictions: List[str],
    recent_3days: List[str],
    use_rag: bool,
    today_sleep: float,
    week_step: List[int],
    table_food: str
) -> Dict[str, str]:
    """
    중재 추론 실행 함수
    """
    # 맥북 MPS 지원 확인 및 설정
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    
    print(f"사용 중인 디바이스: {device}")

    # --- 임베딩 
    embed_model = get_embedder()
    
    # --- VectorDB
    vectorDB, chunks = get_faiss_and_chunks()
    
    retrieval_queries = {
        "diet": "Clinical guidelines for IBS dietary management, low FODMAP diet, and recommended meals",
        "sleep": "Guidelines on sleep quality, sleep hygiene, and sleep disorders in IBS patients",
        "exercise": "Recommendations on physical activity and walking for symptom relief in IBS",
    }

    # 카테고리별 결과 저장
    contexts = {}
    outputs = {}

    for category in ["diet", "sleep", "exercise"]:
        # --- 컨텍스트 검색 (영어 쿼리)
        context = ""
        if use_rag:
            composed_query = f"{retrieval_queries[category]}"
            query_embedding = embed_model.encode([composed_query])
            if category == 'diet':
                _, top_indices = vectorDB["diet"].search(np.array(query_embedding), k=2)
                context = "\n\n".join([str(chunks["diet"][i]) for i in top_indices[0]])
            elif category == 'sleep':
                _, top_indices = vectorDB["sleep"].search(np.array(query_embedding), k=2)
                context = "\n\n".join([str(chunks["sleep"][i]) for i in top_indices[0]])
            elif category == 'exercise':
                _, top_indices = vectorDB["exercise"].search(np.array(query_embedding), k=2)
                context = "\n\n".join([str(chunks["exercise"][i]) for i in top_indices[0]])
        contexts[category] = context

        # 중재 문장 생성
        if category == "diet":
            prompt_ko = build_prompt_ko_from_csv(table_food, allergies, restrictions, recent_3days)
            response = test_llm.call(prompt_ko)
        elif category == "sleep":
            prompt_ko = make_sleep_prompt_ko(context=context, today_sleep=today_sleep)
            response = test_llm.call(prompt_ko)
        else:  # exercise
            prompt_ko = make_exercise_prompt_ko(context=context, week_step=week_step)
            response = test_llm.call(prompt_ko)

        outputs[category] = response
        print(f'{category} 완료')
        
        # 메모리 정리
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            # MPS에서는 empty_cache가 없으므로 gc만 실행
            pass

    return outputs

@app.post("/intervention", response_model=InterventionResponse)
async def generate_intervention(request: InterventionRequest):
    """
    IBS 중재 권고사항 생성 API
    """
    try:
        start_time = time.time()
        
        # LLM 인스턴스 가져오기
        test_llm = get_llm_instance()
        
        # 음식 DB 로드 (고정 경로 사용)
        food_db_path = "Food_list.xlsx"
        if not os.path.exists(food_db_path):
            raise HTTPException(status_code=404, detail=f"음식 DB 파일을 찾을 수 없습니다: {food_db_path}")
        
        df = pd.read_excel(food_db_path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        required = {"food", "fodmap", "fiber"}
        if not required.issubset(set(df.columns)):
            raise HTTPException(
                status_code=400, 
                detail=f"CSV에 필수 컬럼이 없습니다: {required} / 현재: {set(df.columns)}"
            )
        
        table_food = df.to_csv(index=False)
        
        # 중재 추론 실행
        results = run_inference(
            test_llm=test_llm,
            allergies=request.allergies,
            restrictions=request.restrictions,
            recent_3days=request.recent_3days,
            use_rag=request.use_rag,
            today_sleep=request.today_sleep,
            week_step=request.week_step,
            table_food=table_food
        )
        
        processing_time = time.time() - start_time
        
        return InterventionResponse(
            diet_recommendation=results.get("diet", "식단 권고사항을 생성할 수 없습니다."),
            sleep_recommendation=results.get("sleep", "수면 권고사항을 생성할 수 없습니다."),
            exercise_recommendation=results.get("exercise", "운동 권고사항을 생성할 수 없습니다."),
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"중재 생성 중 오류가 발생했습니다: {str(e)}")

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "message": "IBS 중재 서비스가 정상적으로 실행 중입니다."}

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "IBS 중재 서비스 API",
        "version": "1.0.0",
        "endpoints": {
            "POST /intervention": "중재 권고사항 생성",
            "GET /health": "헬스 체크",
            "GET /docs": "API 문서"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=29005)
