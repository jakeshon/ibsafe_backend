#!/bin/bash

# 배치 작업 중지 스크립트

echo "=== IBSafe 배치 작업 중지 ==="

# Celery 프로세스 중지
echo "Celery 프로세스 중지 중..."
pkill -f "celery.*worker"
pkill -f "celery.*beat"

# Redis 서버 중지
echo "Redis 서버 중지 중..."
redis-cli shutdown

echo "=== 배치 작업 중지 완료 ==="
