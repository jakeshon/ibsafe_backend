#!/usr/bin/env python3
"""
IBSafe 중재 테스트 스크립트

하드코딩된 파라미터를 직접 수정하여 중재 권고사항을 테스트합니다.
결과는 DB에 저장하지 않고 print로 출력합니다.

사용법:
    python test_intervention.py
"""

import os
import sys
import django
from datetime import datetime, timedelta, date

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ibsafe.views import _run_intervention_inference, _format_allergies_list, _get_recent_food_names, _get_week_step_counts


def test_intervention():
    """
    하드코딩된 파라미터로 중재 테스트
    """
    print("=== IBSafe 중재 테스트 시작 ===")
    print("하드코딩된 파라미터로 테스트합니다.")
    print("-" * 60)
    
    # ========================================
    # 하드코딩된 입력 파라미터 (여기서 직접 수정하세요)
    # ========================================
    
    # 사용자 프로필 데이터 (알레르기 정보)
    user_profile_data = {
        'has_gluten_allergy': False,      # 글루텐 알레르기
        'has_lactose_allergy': True,      # 유당 알레르기
        'has_nut_allergy': False,         # 견과류 알레르기
        'has_seafood_allergy': False,     # 해산물 알레르기
        'has_egg_allergy': False,         # 계란 알레르기
        'has_soy_allergy': False,         # 콩 알레르기
        'has_lactose_intolerance': True,  # 유당 불내증
    }
    
    # 수면 데이터
    sleep_hours = 7.5  # 수면 시간 (시간)
    
    # 음식 데이터 (최근 3일간)
    food_data = [
        {'food_name': '쌀밥'},
        {'food_name': '된장국'},
        {'food_name': '김치'},
        {'food_name': '불고기'},
        {'food_name': '시금치나물'},
        {'food_name': '계란찜'},
        {'food_name': '우유'},
        {'food_name': '바나나'},
        {'food_name': '요거트'},
    ]
    
    # 오늘 식단
    today_diet = ['쌀밥', '된장국', '김치', '불고기', '시금치나물']
    
    # 운동 데이터 (일주일간 걸음수)
    exercise_data = [
        {'current_steps': 5000},
        {'current_steps': 6000},
        {'current_steps': 4500},
        {'current_steps': 7000},
        {'current_steps': 5500},
        {'current_steps': 8000},
        {'current_steps': 6500},
    ]
    
    # 기타 설정
    use_rag = True
    ollama_model = "gpt-oss:20b"
    
    # ========================================
    # 파라미터 출력
    # ========================================
    
    print("📋 테스트 입력 파라미터:")
    print(f"   알레르기: {_format_allergies_list(user_profile_data)}")
    print(f"   제한사항: []")
    print(f"   최근 3일 음식: {_get_recent_food_names(food_data)}")
    print(f"   오늘 수면시간: {sleep_hours}시간")
    print(f"   주간 걸음수: {_get_week_step_counts(exercise_data)}")
    print(f"   오늘 식단: {today_diet}")
    print(f"   RAG 사용: {use_rag}")
    print(f"   모델: {ollama_model}")
    
    # 음식 DB 로드
    llm_oss_path = os.path.join(os.path.dirname(__file__), 'ibsafe', 'llm_oss')
    food_db_path = os.path.join(llm_oss_path, "Food_list.xlsx")
    
    if not os.path.exists(food_db_path):
        print(f"❌ 음식 DB 파일을 찾을 수 없습니다: {food_db_path}")
        return
    
    import pandas as pd
    df = pd.read_excel(food_db_path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    required = {"food", "fodmap", "fiber"}
    if not required.issubset(set(df.columns)):
        print(f"❌ CSV에 필수 컬럼이 없습니다: {required} / 현재: {set(df.columns)}")
        return
    
    table_food = df.to_csv(index=False)
    print("✅ 음식 DB 로드 완료")
    
    # ========================================
    # 중재 추론 실행
    # ========================================
    
    import time
    start_time = time.time()
    
    try:
        print("-" * 60)
        print("🔄 AI 모델 추론 실행 중...")
        
        results, outputs, error_message = _run_intervention_inference(
            ollama_base_url="http://127.0.0.1:29005",
            ollama_model=ollama_model,
            allergies=_format_allergies_list(user_profile_data),
            restrictions=[],
            recent_3days=_get_recent_food_names(food_data),
            use_rag=use_rag,
            today_sleep=sleep_hours,
            week_step=_get_week_step_counts(exercise_data),
            today_diet=today_diet,
            table_food=table_food
        )
        
        processing_time = time.time() - start_time
        print(f"✅ AI 모델 추론 완료 (처리시간: {processing_time:.2f}초)")
        
        # ========================================
        # 결과 출력
        # ========================================
        
        print("-" * 60)
        print("📊 중재 결과 (DB 저장 없음):")
        
        if error_message:
            print(f"⚠️  오류 메시지: {error_message}")
        else:
            # 식단 평가
            diet_eval = results.get('diet', {}).get('Evaluation', '')
            diet_target = results.get('diet', {}).get('Target', {})
            print(f"🍽️  식단 평가: {diet_eval}")
            if diet_target:
                print(f"   식단 목표: {diet_target}")
            
            # 수면 평가
            sleep_eval = results.get('sleep', {}).get('Evaluation', '')
            sleep_target = results.get('sleep', {}).get('Target', 0.0)
            print(f"😴 수면 평가: {sleep_eval}")
            print(f"   수면 목표: {sleep_target}시간")
            
            # 운동 평가
            exercise_eval = results.get('exercise', {}).get('Evaluation', '')
            exercise_target = results.get('exercise', {}).get('Target', 0)
            print(f"🏃 운동 평가: {exercise_eval}")
            print(f"   운동 목표: {exercise_target}걸음")
        
        # 상세 결과 출력
        print("-" * 60)
        print("📋 상세 결과:")
        print(f"처리 시간: {processing_time:.2f}초")
        print(f"오류 메시지: {error_message if error_message else 'None'}")
        print(f"LLM 출력: {outputs}")
        
        print("-" * 60)
        print("✅ 중재 테스트 완료 (결과는 DB에 저장되지 않음)")
        
    except Exception as e:
        error_message = f"중재 서비스 오류: {str(e)}"
        print(f"❌ {error_message}")
        print("-" * 60)
        print("❌ 중재 테스트 실패")
    
    print("-" * 60)
    print("=== 중재 테스트 완료 ===")


def main():
    """메인 함수"""
    print("Ollama 서버가 실행 중인지 확인하세요: http://127.0.0.1:29005")
    print("모델 'gpt-oss:20b'가 설치되어 있는지 확인하세요.")
    print()
    print("💡 스크립트 상단의 하드코딩된 파라미터를 수정하여 테스트하세요.")
    print()
    
    # 사용자 확인 (자동 진행)
    print("자동으로 진행합니다...")
    # response = input("계속 진행하시겠습니까? (y/N): ")
    # if response.lower() not in ['y', 'yes']:
    #     print("작업이 취소되었습니다.")
    #     return
    
    test_intervention()


if __name__ == "__main__":
    main()
