# IBSafe 배치 시스템 사용법

## 개요

IBSafe 배치 시스템은 Django Celery Beat를 사용하여 모든 사용자에 대해 자동으로 AI 중재 권고사항을 생성하는 시스템입니다.

## 주요 기능

- **자동 스케줄링**: DB에서 설정한 주기에 따라 배치 작업 실행
- **사용자별 처리**: 모든 사용자의 데이터를 개별적으로 처리
- **필수 데이터 검증**: 모든 필수 기록이 있는 사용자만 처리
- **중복 방지**: 이미 중재 기록이 있는 경우 건너뛰기
- **오류 처리**: 오류 발생 시 로그 기록 및 DB 저장

## 시스템 요구사항

- Python 3.8+
- Django 5.2+
- Redis 서버
- Celery 5.5+
- Django Celery Beat 2.8+

## 설치 및 설정

### 1. 패키지 설치

```bash
pip install celery django-celery-beat redis
```

### 2. 환경 변수 설정

`.env` 파일에 다음 설정을 추가:

```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 3. 데이터베이스 마이그레이션

```bash
python manage.py makemigrations
python manage.py migrate
```

## 사용법

### 1. 배치 시스템 시작

```bash
# 자동 시작 스크립트 사용
./start_batch.sh

# 또는 수동으로 시작
redis-server --daemonize yes
celery -A backend worker --loglevel=info --detach
celery -A backend beat --loglevel=info --detach
```

### 2. 배치 시스템 중지

```bash
./stop_batch.sh
```

### 3. 배치 스케줄 초기화

```bash
python manage.py init_batch_schedule
```

### 4. 기본 스케줄 강제 재생성

```bash
python manage.py init_batch_schedule --force
```

## API 엔드포인트

### 배치 스케줄 관리

- `GET /api/batch/schedule/` - 모든 배치 스케줄 조회
- `POST /api/batch/schedule/` - 새 배치 스케줄 생성
- `PUT /api/batch/schedule/` - 배치 스케줄 업데이트
- `DELETE /api/batch/schedule/` - 배치 스케줄 삭제

### 배치 작업 실행

- `POST /api/batch/run/` - 수동으로 배치 작업 실행
- `GET /api/batch/status/` - 배치 작업 상태 조회
- `POST /api/batch/sync/` - 스케줄 동기화

## 배치 스케줄 설정

### 스케줄 생성 예시

```json
{
    "name": "일일 중재 권고사항 생성",
    "frequency": "daily",
    "hour": 9,
    "minute": 0,
    "is_active": true
}
```

### 주기 옵션

- `daily`: 매일 실행
- `weekly`: 매주 일요일 실행
- `monthly`: 매월 1일 실행

## 배치 작업 로직

### 실행 조건

배치 작업은 다음 조건을 모두 만족하는 사용자에 대해서만 실행됩니다:

1. **필수 기록 존재**: 다음 2가지 기록이 모두 있어야 함
   - 음식 기록 (UserFoodRecord)
   - 운동 기록 (UserExerciseRecord)

2. **중재 기록 없음**: 해당 날짜에 이미 중재 기록이 없어야 함

3. **활성 스케줄 존재**: 최소 하나의 활성화된 배치 스케줄이 있어야 함

### 처리 과정

1. **데이터 수집**: 어제 날짜의 모든 사용자 기록 수집
2. **조건 검증**: 필수 기록 존재 여부 확인
3. **중재 생성**: AI 중재 권고사항 생성
4. **결과 저장**: 중재 결과를 데이터베이스에 저장
5. **오류 처리**: 오류 발생 시 오류 정보 저장

## 모니터링

### 로그 확인

```bash
# Celery Worker 로그
tail -f celery.log

# Redis 로그
tail -f /var/log/redis/redis-server.log
```

### 상태 확인

```bash
# Celery 상태 확인
celery -A backend inspect active

# 스케줄 상태 확인
python manage.py shell -c "
from ibsafe.utils import get_schedule_status
print(get_schedule_status())
"
```

## 문제 해결

### 일반적인 문제

1. **Redis 연결 오류**
   - Redis 서버가 실행 중인지 확인
   - `redis-cli ping` 명령으로 연결 테스트

2. **Celery Worker 시작 실패**
   - 가상환경이 활성화되어 있는지 확인
   - Django 설정이 올바른지 확인

3. **스케줄 동기화 실패**
   - `python manage.py init_batch_schedule` 실행
   - Django Celery Beat 마이그레이션 확인

### 디버깅

```bash
# Celery Worker 디버그 모드로 시작
celery -A backend worker --loglevel=debug

# Celery Beat 디버그 모드로 시작
celery -A backend beat --loglevel=debug
```

## 성능 최적화

1. **Worker 수 조정**: 시스템 리소스에 따라 Worker 수 조정
2. **배치 크기 조정**: 한 번에 처리할 사용자 수 조정
3. **데이터베이스 최적화**: 인덱스 추가 및 쿼리 최적화

## 보안 고려사항

1. **Redis 보안**: Redis 서버에 인증 설정
2. **API 보안**: 배치 관리 API에 적절한 권한 설정
3. **로그 보안**: 민감한 정보가 로그에 노출되지 않도록 주의
