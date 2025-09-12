#!/bin/bash

# 배치 작업 시작 스크립트

echo "=== IBSafe 배치 작업 시작 ==="

# Conda 초기화 및 가상환경 활성화
eval "$(conda shell.bash hook)"
conda activate ibsafe 

# 환경 변수 확인 및 명령어 경로 설정
echo "환경 확인 중..."
which redis-server
which celery

# Redis 서버 시작 (백그라운드)
echo "Redis 서버 시작 중..."
/home/doyoung/anaconda3/envs/ibsafe/bin/redis-server --daemonize yes

# Celery Worker 시작 (백그라운드, 로그 파일로 출력)
echo "Celery Worker 시작 중..."
celery -A backend worker --loglevel=info --detach --logfile=celery_worker.log

# Celery Beat 시작 (백그라운드, 로그 파일로 출력)
echo "Celery Beat 시작 중..."
celery -A backend beat --loglevel=info --detach --logfile=celery_beat.log

# 기본 배치 스케줄 생성 (처음 한 번만 필요)
# echo "기본 배치 스케줄 생성 중..."
# python manage.py shell -c "
# from ibsafe.utils import create_default_schedule, sync_batch_schedules
# create_default_schedule()
# sync_batch_schedules()
# print('기본 배치 스케줄 생성 완료')
# "

echo "=== 배치 작업 시작 완료 ==="
echo "Celery Worker와 Beat가 백그라운드에서 실행 중입니다."
echo "Worker 로그 확인: tail -f celery_worker.log"
echo "Beat 로그 확인: tail -f celery_beat.log"
echo "작업 중지: ./stop_batch.sh"
echo ""
echo "💡 팁: DB에서 스케줄을 수정한 후에는 다음 명령으로 동기화할 수 있습니다:"
echo "   python manage.py shell -c \"from ibsafe.utils import sync_batch_schedules; sync_batch_schedules()\""
echo "   또는: ./sync_schedule.sh"
