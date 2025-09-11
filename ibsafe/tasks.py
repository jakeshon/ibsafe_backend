import os
import sys
import django
from datetime import datetime, timedelta
from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
import pytz
from .models import (
    UserProfile, UserSleepRecord, UserFoodRecord, UserWaterRecord, 
    UserExerciseRecord, IBSSSSRecord, IBSQOLRecord, PSSStressRecord,
    InterventionRecord, BatchSchedule
)

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()


@shared_task
def run_intervention_batch():
    """
    모든 사용자에 대해 배치로 중재 권고사항을 생성하는 태스크
    """
    print("=== 배치 중재 작업 시작 ===")
    
    # 활성화된 스케줄 확인
    active_schedules = BatchSchedule.objects.filter(is_active=True)
    if not active_schedules.exists():
        print("활성화된 배치 스케줄이 없습니다.")
        return
    
    # 어제 날짜 계산 (한국 시간 기준)
    korea_tz = pytz.timezone('Asia/Seoul')
    korea_now = timezone.now().astimezone(korea_tz)
    yesterday = korea_now.date() - timedelta(days=1)
    print(f"처리 대상 날짜: {yesterday}")
    
    # 모든 사용자 조회
    users = User.objects.all()
    processed_count = 0
    error_count = 0
    
    for user in users:
        try:
            print(f"사용자 {user.username} 처리 중...")
            
            # 해당 사용자의 어제 날짜 기록들 확인
            has_sleep = UserSleepRecord.objects.filter(
                user=user, 
                record_date=yesterday
            ).exists()
            
            has_food = UserFoodRecord.objects.filter(
                user=user, 
                record_date=yesterday
            ).exists()
            
            has_water = UserWaterRecord.objects.filter(
                user=user, 
                record_date=yesterday
            ).exists()
            
            has_exercise = UserExerciseRecord.objects.filter(
                user=user, 
                record_date=yesterday
            ).exists()
            
            has_ibssss = IBSSSSRecord.objects.filter(
                user=user, 
                record_date=yesterday
            ).exists()
            
            has_ibsqol = IBSQOLRecord.objects.filter(
                user=user, 
                record_date=yesterday
            ).exists()
            
            has_pss = PSSStressRecord.objects.filter(
                user=user, 
                record_date=yesterday
            ).exists()
            
            # 모든 필수 기록이 있는지 확인
            required_records = [
                has_sleep, has_food, has_water, has_exercise, 
                has_ibssss, has_ibsqol, has_pss
            ]
            
            if not all(required_records):
                missing_records = []
                if not has_sleep:
                    missing_records.append("수면")
                if not has_food:
                    missing_records.append("음식")
                if not has_water:
                    missing_records.append("물섭취")
                if not has_exercise:
                    missing_records.append("운동")
                if not has_ibssss:
                    missing_records.append("IBS-SSS")
                if not has_ibsqol:
                    missing_records.append("IBS-QOL")
                if not has_pss:
                    missing_records.append("PSS 스트레스")
                
                print(f"사용자 {user.username}: 필수 기록 누락 - {', '.join(missing_records)}")
                continue
            
            # 이미 중재 기록이 있는지 확인하고 삭제
            existing_intervention = InterventionRecord.objects.filter(
                user=user,
                record_date=yesterday
            ).first()
            
            if existing_intervention:
                print(f"사용자 {user.username}: 기존 중재 기록을 삭제합니다.")
                existing_intervention.delete()
            
            # 중재 권고사항 생성
            print(f"사용자 {user.username}: 중재 권고사항 생성 시작")
            
            # views.py의 get_intervention 로직을 여기서 실행
            from .views import _run_intervention_inference, _format_allergies_list, _get_recent_food_names, _get_week_step_counts
            
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
            sleep_record = UserSleepRecord.objects.get(user=user, record_date=yesterday)
            sleep_data = {
                'sleep_hours': sleep_record.sleep_hours,
            }
            
            # 음식 데이터 (최근 3일간)
            three_days_start = yesterday - timedelta(days=2)
            food_records = UserFoodRecord.objects.filter(
                user=user,
                record_date__range=[three_days_start, yesterday]
            ).select_related('food').order_by('record_date', 'meal_type')
            
            food_data = []
            for record in food_records:
                food_data.append({
                    'food_name': record.food.food_name,
                })
            
            # 오늘 음식 데이터 (today_diet용)
            today_food_records = UserFoodRecord.objects.filter(
                user=user,
                record_date=yesterday
            ).select_related('food').order_by('meal_type')
            
            today_diet = []
            for record in today_food_records:
                food_name = record.food.food_name
                if food_name not in today_diet:
                    today_diet.append(food_name)
            
            # 운동 데이터 (일주일간)
            week_start = yesterday - timedelta(days=6)
            exercise_records = UserExerciseRecord.objects.filter(
                user=user,
                record_date__range=[week_start, yesterday]
            ).order_by('record_date')
            
            exercise_data = []
            for record in exercise_records:
                exercise_data.append({
                    'current_steps': record.current_steps,
                })
            
            # 음식 DB 로드
            llm_oss_path = os.path.join(os.path.dirname(__file__), 'llm_oss')
            food_db_path = os.path.join(llm_oss_path, "Food_list.xlsx")
            
            if not os.path.exists(food_db_path):
                print(f"음식 DB 파일을 찾을 수 없습니다: {food_db_path}")
                continue
            
            import pandas as pd
            df = pd.read_excel(food_db_path)
            df.columns = [str(c).strip().lower() for c in df.columns]
            required = {"food", "fodmap", "fiber"}
            if not required.issubset(set(df.columns)):
                print(f"CSV에 필수 컬럼이 없습니다: {required} / 현재: {set(df.columns)}")
                continue
            
            table_food = df.to_csv(index=False)
            
            # 중재 추론 실행
            import time
            start_time = time.time()
            
            try:
                results, outputs, error_message = _run_intervention_inference(
                    ollama_base_url="http://127.0.0.1:11434",
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
                target_date = yesterday + timedelta(days=1)
                
                intervention_record = InterventionRecord.objects.create(
                    user=user,
                    record_date=yesterday,
                    target_date=target_date,
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
                    print(f"사용자 {user.username}: 오류 발생 - {error_message}")
                    error_count += 1
                else:
                    print(f"사용자 {user.username}: 중재 권고사항 생성 완료 (처리시간: {processing_time:.2f}초)")
                    processed_count += 1
                
            except Exception as e:
                error_message = f"중재 서비스 오류: {str(e)}"
                print(f"사용자 {user.username}: {error_message}")
                
                # 오류 정보를 데이터베이스에 저장
                target_date = yesterday + timedelta(days=1)
                InterventionRecord.objects.create(
                    user=user,
                    record_date=yesterday,
                    target_date=target_date,
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
            print(f"사용자 {user.username} 처리 중 오류: {str(e)}")
            error_count += 1
    
    print(f"=== 배치 중재 작업 완료 ===")
    print(f"처리된 사용자: {processed_count}명")
    print(f"오류 발생: {error_count}명")
    print(f"총 사용자: {users.count()}명")


@shared_task
def create_default_batch_schedule():
    """
    기본 배치 스케줄을 생성하는 태스크
    """
    try:
        # 기본 스케줄이 없으면 생성
        if not BatchSchedule.objects.exists():
            BatchSchedule.objects.create(
                name='일일 중재 권고사항 생성',
                frequency='daily',
                hour=9,
                minute=0,
                is_active=True
            )
            print("기본 배치 스케줄이 생성되었습니다.")
        else:
            print("이미 배치 스케줄이 존재합니다.")
    except Exception as e:
        print(f"기본 배치 스케줄 생성 중 오류: {str(e)}")
