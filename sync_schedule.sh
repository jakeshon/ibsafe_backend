#!/bin/bash

# 스케줄 동기화 스크립트

echo "=== 배치 스케줄 동기화 시작 ==="

# 가상환경 활성화
source ../venv_backend/bin/activate

# 스케줄 동기화 실행
echo "DB 변경사항을 Celery Beat에 동기화 중..."
python manage.py shell -c "
from ibsafe.utils import sync_batch_schedules, get_schedule_status
sync_success = sync_batch_schedules()
status = get_schedule_status()
print('스케줄 동기화 완료' if sync_success else '스케줄 동기화 실패')
if status:
    print(f'총 스케줄: {status[\"total_schedules\"]}개')
    print(f'활성 스케줄: {status[\"active_schedules\"]}개')
    print(f'PeriodicTask: {status[\"periodic_tasks\"]}개')
    print(f'활성화된 태스크: {status[\"enabled_tasks\"]}개')
"

echo "=== 스케줄 동기화 완료 ==="
echo "💡 팁: DB에서 스케줄을 수정한 후 이 스크립트를 실행하면 됩니다."
