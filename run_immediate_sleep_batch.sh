#!/bin/bash

# IBSafe 즉시 배치 수면 중재 실행 스크립트
# 입력된 날짜를 target_date(중재 적용 날짜)로, 하루 전을 record_date(중재 받는 날짜)로 설정하여 수면 중재 권고사항만 생성합니다.

echo "=== IBSafe 즉시 배치 수면 중재 실행 ==="

# 가상환경 활성화
source ../venv_backend/bin/activate

# 파라미터 처리
if [ $# -eq 0 ]; then
    echo "오늘 날짜를 target_date로, 어제 날짜를 record_date로 설정하여 모든 사용자에 대해 수면 중재를 실행합니다."
    python -m ibsafe.intervention_batch --sleep
elif [ $# -eq 1 ]; then
    echo "파라미터로 실행합니다: $1"
    python -m ibsafe.intervention_batch --sleep "$1"
elif [ $# -eq 2 ]; then
    echo "파라미터로 실행합니다: $1 $2"
    python -m ibsafe.intervention_batch --sleep "$1" "$2"
else
    echo "사용법: $0 [YYYY-MM-DD] [username]"
    echo "       $0 [username] [YYYY-MM-DD]"
    echo "       $0 [YYYY-MM-DD]"
    echo "       $0 [username]"
    echo "       $0  (오늘 날짜를 target_date로, 어제 날짜를 record_date로 설정하여 모든 사용자 수면 중재 실행)"
    echo ""
    echo "예시:"
    echo "  $0 2024-01-15 user1     # 2024-01-15를 target_date로, 2024-01-14를 record_date로 설정하여 특정 사용자 수면 중재 처리"
    echo "  $0 user1 2024-01-15     # 2024-01-15를 target_date로, 2024-01-14를 record_date로 설정하여 특정 사용자 수면 중재 처리"
    echo "  $0 2024-01-15           # 2024-01-15를 target_date로, 2024-01-14를 record_date로 설정하여 모든 사용자 수면 중재 처리"
    echo "  $0 user1                # 오늘을 target_date로, 어제를 record_date로 설정하여 특정 사용자 수면 중재 처리"
    echo "  $0                      # 오늘을 target_date로, 어제를 record_date로 설정하여 모든 사용자 수면 중재 처리"
    exit 1
fi

echo "=== 즉시 배치 수면 중재 실행 완료 ==="
