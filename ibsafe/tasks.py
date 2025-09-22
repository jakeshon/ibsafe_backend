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
    yesterday = korea_now.date() - timedelta(days=1) - timedelta(days=2)
    print(f"처리 대상 날짜: {yesterday}")
    
    # 모든 사용자 조회
    users = User.objects.all()
    processed_count = 0
    error_count = 0
    
    for user in users:
        try:
            print(f"사용자 {user.username} 처리 중...")
            
            # 해당 사용자의 어제 날짜 필수 기록들 확인 (수면, 음식, 운동만)
            has_sleep = UserSleepRecord.objects.filter(
                user=user, 
                record_date=yesterday
            ).exists()
            
            has_food = UserFoodRecord.objects.filter(
                user=user, 
                record_date=yesterday
            ).exists()
            
            has_exercise = UserExerciseRecord.objects.filter(
                user=user, 
                record_date=yesterday
            ).exists()
            
            # 필수 기록이 있는지 확인 (수면, 음식, 운동)
            required_records = [has_sleep, has_food, has_exercise]
            
            if not all(required_records):
                missing_records = []
                if not has_sleep:
                    missing_records.append("수면")
                if not has_food:
                    missing_records.append("음식")
                if not has_exercise:
                    missing_records.append("운동")
                
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
            
            # intervention.py의 통합 함수 사용
            from .intervention import process_user_intervention
            
            success, processing_time, error_message = process_user_intervention(
                user=user,
                record_date=yesterday,
                mode='RULE'  # 또는 'LLM'
            )
            
            if success:
                print(f"사용자 {user.username}: 중재 권고사항 생성 완료 (처리시간: {processing_time:.2f}초)")
                processed_count += 1
            else:
                print(f"사용자 {user.username}: 오류 발생 - {error_message}")
                error_count += 1
                
        except Exception as e:
            print(f"사용자 {user.username} 처리 중 오류: {str(e)}")
            error_count += 1
    
    print(f"=== 배치 중재 작업 완료 ===")
    print(f"처리된 사용자: {processed_count}명")
    print(f"오류 발생: {error_count}명")
    print(f"총 사용자: {users.count()}명")


@shared_task
def run_intervention_sleep_batch():
    """
    모든 사용자에 대해 배치로 수면 중재 권고사항만 생성하는 태스크
    """
    print("=== 배치 수면 중재 작업 시작 ===")
    
    # 활성화된 스케줄 확인
    active_schedules = BatchSchedule.objects.filter(is_active=True)
    if not active_schedules.exists():
        print("활성화된 배치 스케줄이 없습니다.")
        return
    
    #  오늘 날짜 계산 (한국 시간 기준)
    korea_tz = pytz.timezone('Asia/Seoul')
    korea_now = timezone.now().astimezone(korea_tz)
    today = korea_now.date() - timedelta(days=2)
    print(f"처리 대상 날짜: {today}")
    
    # 모든 사용자 조회
    users = User.objects.all()
    processed_count = 0
    error_count = 0
    skipped_count = 0
    
    for user in users:
        try:
            print(f"사용자 {user.username} 처리 중...")
            
            # 해당 사용자의 어제 날짜 수면 기록 확인
            has_sleep = UserSleepRecord.objects.filter(
                user=user, 
                record_date=today
            ).exists()
            
            # 수면 기록이 없으면 건너뛰기
            if not has_sleep:
                print(f"사용자 {user.username}: 수면 기록이 없어서 실행 불가")
                skipped_count += 1
                continue
            
            print(f"사용자 {user.username}: 수면 기록 존재 - 실행 가능")
            
            # 이미 중재 기록이 있는지 확인하고 삭제
            existing_intervention = InterventionRecord.objects.filter(
                user=user,
                record_date=today
            ).first()
            
            if existing_intervention:
                print(f"사용자 {user.username}: 기존 중재 기록을 삭제합니다.")
                existing_intervention.delete()
            
            # 수면 중재 권고사항 생성
            print(f"사용자 {user.username}: 수면 중재 권고사항 생성 시작")
            
            # intervention.py의 통합 함수 사용
            from .intervention import process_user_sleep_intervention
            
            success, processing_time, error_message = process_user_sleep_intervention(
                user=user,
                record_date=today,
                mode='RULE'  # 또는 'LLM'
            )
            
            if success:
                print(f"사용자 {user.username}: 수면 중재 권고사항 생성 완료 (처리시간: {processing_time:.2f}초)")
                processed_count += 1
            else:
                print(f"사용자 {user.username}: 오류 발생 - {error_message}")
                error_count += 1
                
        except Exception as e:
            print(f"사용자 {user.username} 처리 중 오류: {str(e)}")
            error_count += 1
    
    print(f"=== 배치 수면 중재 작업 완료 ===")
    print(f"처리된 사용자: {processed_count}명")
    print(f"오류 발생: {error_count}명")
    print(f"건너뛴 사용자: {skipped_count}명")
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
