#!/usr/bin/env python3
"""
IBSafe 즉시 배치 실행 스크립트

입력된 날짜를 target_date(중재 적용 날짜)로, 하루 전을 record_date(중재 받는 날짜)로 설정하여 중재 권고사항을 즉시 생성합니다.
Celery Beat 스케줄링 없이 직접 실행됩니다.

사용법:
    python -m ibsafe.intervention_batch [YYYY-MM-DD] [username]
    python -m ibsafe.intervention_batch [username] [YYYY-MM-DD]
    python -m ibsafe.intervention_batch [YYYY-MM-DD]
    python -m ibsafe.intervention_batch [username]
    python -m ibsafe.intervention_batch  # 오늘 날짜를 target_date로, 어제 날짜를 record_date로 설정하여 모든 사용자 실행
    python -m ibsafe.intervention_batch --sleep [YYYY-MM-DD] [username]  # 수면 중재만 실행
    
예시:
    python -m ibsafe.intervention_batch 2024-01-15 user1  # 2024-01-15를 target_date로, 2024-01-14를 record_date로 설정
    python -m ibsafe.intervention_batch user1 2024-01-15  # 2024-01-15를 target_date로, 2024-01-14를 record_date로 설정
    python -m ibsafe.intervention_batch 2024-01-15        # 2024-01-15를 target_date로, 2024-01-14를 record_date로 설정하여 모든 사용자
    python -m ibsafe.intervention_batch user1             # 오늘을 target_date로, 어제를 record_date로 설정하여 특정 사용자
    python -m ibsafe.intervention_batch                   # 오늘을 target_date로, 어제를 record_date로 설정하여 모든 사용자
    python -m ibsafe.intervention_batch --sleep 2024-01-15 user1  # 수면 중재만 실행
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
from ibsafe.intervention import process_user_intervention, process_user_sleep_intervention


def run_immediate_intervention_batch(target_date_str=None, username=None):
    """
    입력된 날짜를 target_date(중재 적용 날짜)로, 하루 전을 record_date(중재 받는 날짜)로 설정하여 중재 권고사항을 생성
    
    Args:
        target_date_str (str): 중재가 적용될 날짜 (YYYY-MM-DD 형식). None이면 오늘 날짜 사용
        username (str): 처리할 사용자명. None이면 모든 사용자 처리
    """
    print("=== IBSafe 즉시 배치 중재 작업 시작 ===")
    
    # 날짜 처리
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            record_date = target_date - timedelta(days=1)
            print(f"지정된 target_date: {target_date}")
            print(f"계산된 record_date: {record_date}")
        except ValueError:
            print(f"잘못된 날짜 형식입니다: {target_date_str}")
            print("올바른 형식: YYYY-MM-DD (예: 2024-01-15)")
            return
    else:
        # 오늘 날짜를 target_date로, 어제 날짜를 record_date로 계산 (한국 시간 기준)
        korea_tz = pytz.timezone('Asia/Seoul')
        korea_now = timezone.now().astimezone(korea_tz)
        target_date = korea_now.date()
        record_date = target_date - timedelta(days=1)
        print(f"오늘 날짜를 target_date로 설정: {target_date}")
        print(f"어제 날짜를 record_date로 설정: {record_date}")
    
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
    print(f"중재 적용 날짜 (target_date): {target_date}")
    print(f"중재 받는 날짜 (record_date): {record_date}")
    print("-" * 50)
    
    for user in users:
        try:
            print(f"사용자 {user.username} 처리 중...")
            
            # 해당 사용자의 record_date 기록들 확인
            has_sleep = UserSleepRecord.objects.filter(
                user=user, 
                record_date=record_date
            ).exists()
            
            has_food = UserFoodRecord.objects.filter(
                user=user, 
                record_date=record_date
            ).exists()
            
            has_exercise = UserExerciseRecord.objects.filter(
                user=user, 
                record_date=record_date
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
            
            print(f"  ✅ 필수 기록 모두 존재 - 실행 가능")
            
            # 이미 중재 기록이 있는지 확인하고 삭제
            existing_intervention = InterventionRecord.objects.filter(
                user=user,
                record_date=record_date
            ).first()
            
            if existing_intervention:
                print(f"  🔄 기존 중재 기록을 삭제합니다.")
                existing_intervention.delete()
            
            # 중재 권고사항 생성
            print(f"  🤖 중재 권고사항 생성 시작")
            
            success, processing_time, error_message = process_user_intervention(
                user=user,
                record_date=record_date,
                mode='RULE'  # 또는 'LLM'
            )
            
            if success:
                print(f"  ✅ 중재 권고사항 생성 완료 (처리시간: {processing_time:.2f}초)")
                processed_count += 1
            else:
                print(f"  ❌ 오류 발생 - {error_message}")
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
    print(f"📅 중재 적용 날짜 (target_date): {target_date}")
    print(f"📅 중재 받는 날짜 (record_date): {record_date}")


def run_immediate_intervention_sleep_batch(target_date_str=None, username=None):
    """
    입력된 날짜를 target_date(중재 적용 날짜)로, 하루 전을 record_date(중재 받는 날짜)로 설정하여 수면 중재 권고사항만 생성
    
    Args:
        target_date_str (str): 중재가 적용될 날짜 (YYYY-MM-DD 형식). None이면 오늘 날짜 사용
        username (str): 처리할 사용자명. None이면 모든 사용자 처리
    """
    print("=== IBSafe 즉시 배치 수면 중재 작업 시작 ===")
    
    # 날짜 처리
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            record_date = target_date - timedelta(days=1)
            print(f"지정된 target_date: {target_date}")
            print(f"계산된 record_date: {record_date}")
        except ValueError:
            print(f"잘못된 날짜 형식입니다: {target_date_str}")
            print("올바른 형식: YYYY-MM-DD (예: 2024-01-15)")
            return
    else:
        # 오늘 날짜를 target_date로, 어제 날짜를 record_date로 계산 (한국 시간 기준)
        korea_tz = pytz.timezone('Asia/Seoul')
        korea_now = timezone.now().astimezone(korea_tz)
        target_date = korea_now.date()
        record_date = target_date - timedelta(days=1)
        print(f"오늘 날짜를 target_date로 설정: {target_date}")
        print(f"어제 날짜를 record_date로 설정: {record_date}")
    
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
    print(f"중재 적용 날짜 (target_date): {target_date}")
    print(f"중재 받는 날짜 (record_date): {record_date}")
    print("-" * 50)
    
    for user in users:
        try:
            print(f"사용자 {user.username} 처리 중...")
            
            # 해당 사용자의 record_date 수면 기록 확인
            has_sleep = UserSleepRecord.objects.filter(
                user=user, 
                record_date=record_date
            ).exists()
            
            # 수면 기록이 없으면 건너뛰기
            if not has_sleep:
                print(f"  ❌ 수면 기록이 없어서 실행 불가")
                skipped_count += 1
                continue
            
            print(f"  ✅ 수면 기록 존재 - 실행 가능")
            
            # 이미 중재 기록이 있는지 확인하고 삭제
            existing_intervention = InterventionRecord.objects.filter(
                user=user,
                record_date=record_date
            ).first()
            
            if existing_intervention:
                print(f"  🔄 기존 중재 기록을 삭제합니다.")
                existing_intervention.delete()
            
            # 수면 중재 권고사항 생성
            print(f"  🤖 수면 중재 권고사항 생성 시작")
            
            success, processing_time, error_message = process_user_sleep_intervention(
                user=user,
                record_date=record_date,
                mode='RULE'  # 또는 'LLM'
            )
            
            if success:
                print(f"  ✅ 수면 중재 권고사항 생성 완료 (처리시간: {processing_time:.2f}초)")
                processed_count += 1
            else:
                print(f"  ❌ 오류 발생 - {error_message}")
                error_count += 1
                
        except Exception as e:
            print(f"  ❌ 사용자 {user.username} 처리 중 오류: {str(e)}")
            error_count += 1
    
    print("-" * 50)
    print("=== 즉시 배치 수면 중재 작업 완료 ===")
    print(f"✅ 처리된 사용자: {processed_count}명")
    print(f"⚠️  오류 발생: {error_count}명")
    print(f"⏭️  건너뛴 사용자: {skipped_count}명")
    print(f"📊 총 사용자: {users.count()}명")
    print(f"📅 중재 적용 날짜 (target_date): {target_date}")
    print(f"📅 중재 받는 날짜 (record_date): {record_date}")


def main():
    """메인 함수"""
    target_date = None
    username = None
    sleep_only = False
    
    # 명령행 인수 처리
    if len(sys.argv) > 1:
        # 첫 번째 인수가 --sleep 옵션인지 확인
        if sys.argv[1] == '--sleep':
            sleep_only = True
            print("수면 중재만 실행합니다.")
            # --sleep 다음 인수들 처리
            if len(sys.argv) > 2:
                first_arg = sys.argv[2]
                # 날짜 형식인지 확인 (YYYY-MM-DD)
                if len(first_arg) == 10 and first_arg.count('-') == 2:
                    target_date = first_arg
                    print(f"지정된 날짜를 target_date로 설정: {target_date}")
                else:
                    # 사용자명으로 처리
                    username = first_arg
                    print(f"특정 사용자로 실행: {username}")
                
                if len(sys.argv) > 3:
                    # 세 번째 인수 처리
                    second_arg = sys.argv[3]
                    if username and len(second_arg) == 10 and second_arg.count('-') == 2:
                        target_date = second_arg
                        print(f"지정된 날짜를 target_date로 설정: {target_date}")
                    elif not username:
                        username = second_arg
                        print(f"특정 사용자로 실행: {username}")
        else:
            # 첫 번째 인수가 날짜인지 사용자명인지 판단
            first_arg = sys.argv[1]
            
            # 날짜 형식인지 확인 (YYYY-MM-DD)
            if len(first_arg) == 10 and first_arg.count('-') == 2:
                target_date = first_arg
                print(f"지정된 날짜를 target_date로 설정: {target_date}")
            else:
                # 사용자명으로 처리
                username = first_arg
                print(f"특정 사용자로 실행: {username}")
        
        if not sleep_only and len(sys.argv) > 2:
            # 두 번째 인수 처리
            second_arg = sys.argv[2]
            if username and len(second_arg) == 10 and second_arg.count('-') == 2:
                target_date = second_arg
                print(f"지정된 날짜를 target_date로 설정: {target_date}")
            elif not username:
                username = second_arg
                print(f"특정 사용자로 실행: {username}")
    
    if not target_date:
        print("오늘 날짜를 target_date로, 어제 날짜를 record_date로 설정하여 실행")
    if not username:
        print("모든 사용자 처리")
    
    print("Ollama 서버가 실행 중인지 확인하세요: http://127.0.0.1:29005")
    print("모델 'gpt-oss:20b'가 설치되어 있는지 확인하세요.")
    print()
    
    # 사용자 확인 (자동 진행)
    print("자동으로 진행합니다...")
    
    if sleep_only:
        run_immediate_intervention_sleep_batch(target_date, username)
    else:
        run_immediate_intervention_batch(target_date, username)


if __name__ == "__main__":
    main()
