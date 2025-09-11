#!/bin/bash

# Django 백엔드 서버 중지 스크립트

echo "=== IBSafe 백엔드 서버 중지 ==="

# PID 파일 확인
if [ -f "django_server.pid" ]; then
    SERVER_PID=$(cat django_server.pid)
    
    # 프로세스가 실행 중인지 확인
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo "서버 중지 중... (PID: $SERVER_PID)"
        kill $SERVER_PID
        
        # 프로세스가 완전히 종료될 때까지 대기
        sleep 2
        
        # 강제 종료가 필요한 경우
        if ps -p $SERVER_PID > /dev/null 2>&1; then
            echo "강제 종료 중..."
            kill -9 $SERVER_PID
        fi
        
        echo "서버가 성공적으로 중지되었습니다."
    else
        echo "서버가 이미 중지되어 있습니다."
    fi
    
    # PID 파일 삭제
    rm -f django_server.pid
else
    echo "PID 파일을 찾을 수 없습니다. 서버가 실행 중이지 않을 수 있습니다."
    
    # 포트 19005를 사용하는 프로세스 찾아서 종료
    echo "포트 19005를 사용하는 프로세스를 찾는 중..."
    PORT_PID=$(lsof -ti:19005)
    
    if [ ! -z "$PORT_PID" ]; then
        echo "포트 19005를 사용하는 프로세스 발견 (PID: $PORT_PID)"
        kill $PORT_PID
        echo "프로세스가 종료되었습니다."
    else
        echo "포트 19005를 사용하는 프로세스를 찾을 수 없습니다."
    fi
fi

echo "=== 백엔드 서버 중지 완료 ==="
