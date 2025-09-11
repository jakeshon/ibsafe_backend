#!/bin/bash

# IBSafe 중재 테스트 스크립트
# 하드코딩된 파라미터로 중재 권고사항을 테스트합니다.

echo "=== IBSafe 중재 테스트 ==="
echo "하드코딩된 파라미터로 테스트합니다."
echo ""

# 가상환경 활성화
conda activate ibsafe

# Python 스크립트 실행
python test_intervention.py

echo "=== 중재 테스트 완료 ==="
