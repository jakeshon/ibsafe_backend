#!/bin/bash

# IBSafe 즉시 배치 실행 스크립트
# 선택된 날짜와 사용자를 기준으로 중재 권고사항을 즉시 생성합니다.

echo "=== IBSafe 즉시 배치 실행 ==="

# 가상환경 활성화
conda activate ibsafe

# 파라미터 처리
if [ $# -eq 0 ]; then
    echo "어제 날짜, 모든 사용자로 실행합니다."
    python run_immediate_batch.py
elif [ $# -eq 1 ]; then
    echo "파라미터로 실행합니다: $1"
    python run_immediate_batch.py "$1"
elif [ $# -eq 2 ]; then
    echo "파라미터로 실행합니다: $1 $2"
    python run_immediate_batch.py "$1" "$2"
else
    echo "사용법: $0 [YYYY-MM-DD] [username]"
    echo "       $0 [username] [YYYY-MM-DD]"
    echo "       $0 [YYYY-MM-DD]"
    echo "       $0 [username]"
    echo "       $0  (어제 날짜, 모든 사용자로 실행)"
    echo ""
    echo "예시:"
    echo "  $0 2024-01-15 user1     # 특정 날짜, 특정 사용자"
    echo "  $0 user1 2024-01-15     # 특정 사용자, 특정 날짜"
    echo "  $0 2024-01-15           # 특정 날짜, 모든 사용자"
    echo "  $0 user1                # 어제 날짜, 특정 사용자"
    echo "  $0                      # 어제 날짜, 모든 사용자"
    exit 1
fi

echo "=== 즉시 배치 실행 완료 ==="
