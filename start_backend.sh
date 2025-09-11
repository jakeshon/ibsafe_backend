#!/bin/bash

# Django 백엔드 서버 시작 스크립트 (백그라운드 실행)

echo "=== IBSafe 백엔드 서버 시작 ==="

# 가상환경 활성화
echo "가상환경 활성화 중..."
source ../venv_backend/bin/activate

# Django 서버 시작 (백그라운드)
echo "Django 서버 시작 중..."
echo "서버 주소: http://0.0.0.0:9005"
echo ""

# Django 개발 서버를 백그라운드에서 실행
nohup python manage.py runserver 0.0.0.0:9005 > django_server.log 2>&1 &
SERVER_PID=$!

# PID를 파일에 저장
echo $SERVER_PID > django_server.pid

echo "=== 백엔드 서버 시작 완료 ==="
echo "서버가 백그라운드에서 실행 중입니다."
echo "PID: $SERVER_PID"
echo "로그 확인: tail -f django_server.log"
echo "서버 중지: ./stop_backend.sh"
echo "또는: kill $SERVER_PID"
