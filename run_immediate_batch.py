#!/usr/bin/env python3
"""
IBSafe 즉시 배치 실행 스크립트

선택된 날짜와 사용자를 기준으로 중재 권고사항을 즉시 생성합니다.
Celery Beat 스케줄링 없이 직접 실행됩니다.

사용법:
    python run_immediate_batch.py [YYYY-MM-DD] [username]
    python run_immediate_batch.py [username] [YYYY-MM-DD]
    python run_immediate_batch.py [YYYY-MM-DD]
    python run_immediate_batch.py [username]
    python run_immediate_batch.py  # 어제 날짜, 모든 사용자로 실행
    
예시:
    python run_immediate_batch.py 2024-01-15 user1
    python run_immediate_batch.py user1 2024-01-15
    python run_immediate_batch.py 2024-01-15  # 특정 날짜, 모든 사용자
    python run_immediate_batch.py user1       # 어제 날짜, 특정 사용자
    python run_immediate_batch.py             # 어제 날짜, 모든 사용자
"""

import os
import sys
import django
from datetime import datetime, timedelta, date
import pytz

# Django 설정 로드 (모델 import 전에 먼저 실행)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Django 설정 로드 후에 모델 import
from django.contrib.auth.models import User
from django.utils import timezone
from ibsafe.models import (
    UserProfile, UserSleepRecord, UserFoodRecord, UserWaterRecord, 
    UserExerciseRecord, IBSSSSRecord, IBSQOLRecord, PSSStressRecord,
    InterventionRecord
)
from ibsafe.views import _run_intervention_inference, _format_allergies_list, _get_recent_food_names, _get_week_step_counts


def run_immediate_intervention_batch(target_date_str=None, username=None):
    """
    선택된 날짜를 기준으로 사용자에 대해 중재 권고사항을 생성
    
    Args:
        target_date_str (str): 처리할 날짜 (YYYY-MM-DD 형식). None이면 어제 날짜 사용
        username (str): 처리할 사용자명. None이면 모든 사용자 처리
    """
    print("=== IBSafe 즉시 배치 중재 작업 시작 ===")
    
    # 날짜 처리
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            print(f"지정된 날짜로 처리: {target_date}")
        except ValueError:
            print(f"잘못된 날짜 형식입니다: {target_date_str}")
            print("올바른 형식: YYYY-MM-DD (예: 2024-01-15)")
            return
    else:
        # 어제 날짜 계산 (한국 시간 기준)
        korea_tz = pytz.timezone('Asia/Seoul')
        korea_now = timezone.now().astimezone(korea_tz)
        target_date = korea_now.date() - timedelta(days=1)
        print(f"어제 날짜로 처리: {target_date}")
    
    # 사용자 조회
    if username:
        try:
            users = User.objects.filter(username=username)
            if not users.exists():
                print(f"❌ 사용자 '{username}'를 찾을 수 없습니다.")
                return
            print(f"특정 사용자 처리: {username}")
        except Exception as e:
            print(f"❌ 사용자 조회 오류: {str(e)}")
            return
    else:
        users = User.objects.all()
        print(f"모든 사용자 처리")
    
    processed_count = 0
    error_count = 0
    skipped_count = 0
    
    print(f"총 사용자 수: {users.count()}명")
    print(f"처리 대상 날짜: {target_date}")
    print("-" * 50)
    
    for user in users:
        try:
            print(f"사용자 {user.username} 처리 중...")
            
            # 해당 사용자의 지정 날짜 기록들 확인
            has_sleep = UserSleepRecord.objects.filter(
                user=user, 
                record_date=target_date
            ).exists()
            
            has_food = UserFoodRecord.objects.filter(
                user=user, 
                record_date=target_date
            ).exists()
            
            has_water = UserWaterRecord.objects.filter(
                user=user, 
                record_date=target_date
            ).exists()
            
            has_exercise = UserExerciseRecord.objects.filter(
                user=user, 
                record_date=target_date
            ).exists()
            
            has_ibssss = IBSSSSRecord.objects.filter(
                user=user, 
                record_date=target_date
            ).exists()
            
            has_ibsqol = IBSQOLRecord.objects.filter(
                user=user, 
                record_date=target_date
            ).exists()
            
            has_pss = PSSStressRecord.objects.filter(
                user=user, 
                record_date=target_date
            ).exists()
            
            # 필수 기록 확인 (수면, 음식, 운동만 필수)
            essential_records = [has_sleep, has_food, has_exercise]
            
            if not all(essential_records):
                missing_records = []
                if not has_sleep:
                    missing_records.append("수면")
                if not has_food:
                    missing_records.append("음식")
                if not has_exercise:
                    missing_records.append("운동")
                
                print(f"  ❌ 필수 기록 누락으로 실행 불가 - {', '.join(missing_records)} 기록이 필요합니다")
                skipped_count += 1
                continue
            
            # 기록 상태 표시
            recorded_items = []
            missing_items = []
            
            # 필수 기록 상태
            if has_sleep:
                recorded_items.append("수면")
            else:
                missing_items.append("수면")
                
            if has_food:
                recorded_items.append("음식")
            else:
                missing_items.append("음식")
                
            if has_exercise:
                recorded_items.append("운동")
            else:
                missing_items.append("운동")
            
            # 선택적 기록 상태
            if has_water:
                recorded_items.append("물섭취")
            else:
                missing_items.append("물섭취")
                
            if has_ibssss:
                recorded_items.append("IBS-SSS")
            else:
                missing_items.append("IBS-SSS")
                
            if has_ibsqol:
                recorded_items.append("IBS-QOL")
            else:
                missing_items.append("IBS-QOL")
                
            if has_pss:
                recorded_items.append("PSS 스트레스")
            else:
                missing_items.append("PSS 스트레스")
            
            # 기록 상태 출력
            print(f"  📋 기록된 항목: {', '.join(recorded_items)}")
            if missing_items:
                print(f"  ❌ 기록 누락: {', '.join(missing_items)}")
            
            # 필수 기록 확인
            essential_missing = [item for item in missing_items if item in ["수면", "음식", "운동"]]
            if essential_missing:
                print(f"  🚫 필수 기록 누락으로 실행 불가 - {', '.join(essential_missing)} 기록이 필요합니다")
                skipped_count += 1
                continue
            else:
                print(f"  ✅ 필수 기록 모두 존재 - 실행 가능")
            
            # 이미 중재 기록이 있는지 확인하고 삭제
            existing_intervention = InterventionRecord.objects.filter(
                user=user,
                record_date=target_date
            ).first()
            
            if existing_intervention:
                print(f"  🔄 기존 중재 기록을 삭제합니다.")
                existing_intervention.delete()
            
            # 중재 권고사항 생성
            print(f"  🤖 중재 권고사항 생성 시작")
            
            # 사용자 프로필 정보
            profile = user.profile
            user_profile_data = {
                'has_gluten_allergy': profile.has_gluten_allergy,
                'has_lactose_allergy': profile.has_lactose_allergy,
                'has_nut_allergy': profile.has_nut_allergy,
                'has_seafood_allergy': profile.has_seafood_allergy,
                'has_egg_allergy': profile.has_egg_allergy,
                'has_soy_allergy': profile.has_soy_allergy,
                'has_lactose_intolerance': profile.has_lactose_intolerance,
            }
            
            # 수면 데이터
            sleep_record = UserSleepRecord.objects.get(user=user, record_date=target_date)
            sleep_data = {
                'sleep_hours': sleep_record.sleep_hours,
            }
            
            # 음식 데이터 (최근 3일간)
            three_days_start = target_date - timedelta(days=2)
            food_records = UserFoodRecord.objects.filter(
                user=user,
                record_date__range=[three_days_start, target_date]
            ).select_related('food').order_by('record_date', 'meal_type')
            
            food_data = []
            for record in food_records:
                food_data.append({
                    'food_name': record.food.food_name,
                })
            
            # 대상 날짜 음식 데이터 (today_diet용)
            target_food_records = UserFoodRecord.objects.filter(
                user=user,
                record_date=target_date
            ).select_related('food').order_by('meal_type')
            
            today_diet = []
            for record in target_food_records:
                food_name = record.food.food_name
                if food_name not in today_diet:
                    today_diet.append(food_name)
            
            # 운동 데이터 (일주일간)
            week_start = target_date - timedelta(days=6)
            exercise_records = UserExerciseRecord.objects.filter(
                user=user,
                record_date__range=[week_start, target_date]
            ).order_by('record_date')
            
            exercise_data = []
            for record in exercise_records:
                exercise_data.append({
                    'current_steps': record.current_steps,
                })
            
            # 음식 DB 로드
            llm_oss_path = os.path.join(os.path.dirname(__file__), 'ibsafe', 'llm_oss')
            food_db_path = os.path.join(llm_oss_path, "Food_list.xlsx")
            
            if not os.path.exists(food_db_path):
                print(f"  ❌ 음식 DB 파일을 찾을 수 없습니다: {food_db_path}")
                error_count += 1
                continue
            
            import pandas as pd
            df = pd.read_excel(food_db_path)
            df.columns = [str(c).strip().lower() for c in df.columns]
            required = {"food", "fodmap", "fiber"}
            if not required.issubset(set(df.columns)):
                print(f"  ❌ CSV에 필수 컬럼이 없습니다: {required} / 현재: {set(df.columns)}")
                error_count += 1
                continue
            
            table_food = df.to_csv(index=False)
            
            # 중재 추론 실행
            import time
            start_time = time.time()
            
            try:
                results, outputs, error_message = _run_intervention_inference(
                    ollama_base_url="http://127.0.0.1:29005",
                    ollama_model="gpt-oss:20b",
                    allergies=_format_allergies_list(user_profile_data),
                    restrictions=[],
                    recent_3days=_get_recent_food_names(food_data),
                    use_rag=True,
                    today_sleep=sleep_data['sleep_hours'],
                    week_step=_get_week_step_counts(exercise_data),
                    today_diet=today_diet,
                    table_food=table_food
                )
                
                processing_time = time.time() - start_time
                
                # 중재 결과를 데이터베이스에 저장
                next_day = target_date + timedelta(days=1)
                
                intervention_record = InterventionRecord.objects.create(
                    user=user,
                    record_date=target_date,
                    target_date=next_day,
                    diet_evaluation=results.get('diet', {}).get('Evaluation', ''),
                    diet_target=results.get('diet', {}).get('Target', {}),
                    sleep_evaluation=results.get('sleep', {}).get('Evaluation', ''),
                    sleep_target=results.get('sleep', {}).get('Target', 0.0),
                    exercise_evaluation=results.get('exercise', {}).get('Evaluation', ''),
                    exercise_target=results.get('exercise', {}).get('Target', 0),
                    processing_time=processing_time,
                    error_message=error_message,
                    # 입력 파라미터 저장
                    input_allergies=_format_allergies_list(user_profile_data),
                    input_restrictions=[],
                    input_recent_3days=_get_recent_food_names(food_data),
                    input_today_sleep=sleep_data['sleep_hours'],
                    input_week_step=_get_week_step_counts(exercise_data),
                    input_today_diet=today_diet,
                    input_use_rag=True,
                    input_ollama_model="gpt-oss:20b",
                    # LLM 출력 결과 저장
                    outputs=outputs,
                )
                
                if error_message:
                    print(f"  ⚠️  오류 발생 - {error_message}")
                    error_count += 1
                else:
                    print(f"  ✅ 중재 권고사항 생성 완료 (처리시간: {processing_time:.2f}초)")
                    processed_count += 1
                
            except Exception as e:
                error_message = f"중재 서비스 오류: {str(e)}"
                print(f"  ❌ {error_message}")
                
                # 오류 정보를 데이터베이스에 저장
                next_day = target_date + timedelta(days=1)
                InterventionRecord.objects.create(
                    user=user,
                    record_date=target_date,
                    target_date=next_day,
                    diet_evaluation='',
                    diet_target={},
                    sleep_evaluation='',
                    sleep_target=sleep_data['sleep_hours'],
                    exercise_evaluation='',
                    exercise_target=0,
                    processing_time=0.0,
                    error_message=error_message,
                    # 입력 파라미터 저장
                    input_allergies=_format_allergies_list(user_profile_data),
                    input_restrictions=[],
                    input_recent_3days=_get_recent_food_names(food_data),
                    input_today_sleep=sleep_data['sleep_hours'],
                    input_week_step=_get_week_step_counts(exercise_data),
                    input_today_diet=today_diet,
                    input_use_rag=True,
                    input_ollama_model="gpt-oss:20b",
                    # LLM 출력 결과 저장 (오류 시 빈 딕셔너리)
                    outputs={},
                )
                error_count += 1
                
        except Exception as e:
            print(f"  ❌ 사용자 {user.username} 처리 중 오류: {str(e)}")
            error_count += 1
    
    print("-" * 50)
    print("=== 즉시 배치 중재 작업 완료 ===")
    print(f"✅ 처리된 사용자: {processed_count}명")
    print(f"⚠️  오류 발생: {error_count}명")
    print(f"⏭️  건너뛴 사용자: {skipped_count}명")
    print(f"📊 총 사용자: {users.count()}명")
    print(f"📅 처리 날짜: {target_date}")


def main():
    """메인 함수"""
    target_date = None
    username = None
    
    # 명령행 인수 처리
    if len(sys.argv) > 1:
        # 첫 번째 인수가 날짜인지 사용자명인지 판단
        first_arg = sys.argv[1]
        
        # 날짜 형식인지 확인 (YYYY-MM-DD)
        if len(first_arg) == 10 and first_arg.count('-') == 2:
            target_date = first_arg
            print(f"지정된 날짜로 실행: {target_date}")
        else:
            # 사용자명으로 처리
            username = first_arg
            print(f"특정 사용자로 실행: {username}")
    
    if len(sys.argv) > 2:
        # 두 번째 인수 처리
        second_arg = sys.argv[2]
        if username and len(second_arg) == 10 and second_arg.count('-') == 2:
            target_date = second_arg
            print(f"지정된 날짜로 실행: {target_date}")
        elif not username:
            username = second_arg
            print(f"특정 사용자로 실행: {username}")
    
    if not target_date:
        print("어제 날짜로 실행")
    if not username:
        print("모든 사용자 처리")
    
    print("Ollama 서버가 실행 중인지 확인하세요: http://127.0.0.1:29005")
    print("모델 'gpt-oss:20b'가 설치되어 있는지 확인하세요.")
    print()
    
    # 사용자 확인 (자동 진행)
    print("자동으로 진행합니다...")
    # response = input("계속 진행하시겠습니까? (y/N): ")
    # if response.lower() not in ['y', 'yes']:
    #     print("작업이 취소되었습니다.")
    #     return
    
    run_immediate_intervention_batch(target_date, username)


if __name__ == "__main__":
    main()
