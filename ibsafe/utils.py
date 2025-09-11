from django_celery_beat.models import PeriodicTask, CrontabSchedule
from .models import BatchSchedule


def sync_batch_schedules():
    """
    BatchSchedule 모델의 변경사항을 Celery Beat 스케줄과 동기화
    """
    try:
        # 모든 활성화된 배치 스케줄 조회
        active_schedules = BatchSchedule.objects.filter(is_active=True)
        
        # 기존 PeriodicTask 중 배치 관련 태스크들 삭제
        PeriodicTask.objects.filter(name__startswith='batch_intervention_').delete()
        
        # 새로운 스케줄 생성
        for schedule in active_schedules:
            print(f"스케줄 동기화 중: {schedule.name} - {schedule.hour}:{schedule.minute}")
            
            # Crontab 스케줄 생성 또는 가져오기
            day_of_week = '*' if schedule.frequency == 'daily' else '0' if schedule.frequency == 'weekly' else '*'
            day_of_month = '*' if schedule.frequency != 'monthly' else '1'
            
            # 기존 CrontabSchedule이 있는지 확인
            crontab = CrontabSchedule.objects.filter(
                minute=schedule.minute,
                hour=schedule.hour,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                month_of_year='*',
            ).first()
            
            if crontab is None:
                crontab = CrontabSchedule.objects.create(
                    minute=schedule.minute,
                    hour=schedule.hour,
                    day_of_week=day_of_week,
                    day_of_month=day_of_month,
                    month_of_year='*',
                )
                print(f"새로운 CrontabSchedule 생성: {crontab.hour}:{crontab.minute}")
            else:
                print(f"기존 CrontabSchedule 사용: {crontab.hour}:{crontab.minute}")
            
            # PeriodicTask 생성
            task_name = f'batch_intervention_{schedule.id}'
            periodic_task, created = PeriodicTask.objects.get_or_create(
                name=task_name,
                defaults={
                    'task': 'ibsafe.tasks.run_intervention_batch',
                    'crontab': crontab,
                    'enabled': schedule.is_active,
                }
            )
            
            # 기존 태스크 업데이트
            if not created:
                periodic_task.crontab = crontab
                periodic_task.enabled = schedule.is_active
                periodic_task.save()
                print(f"PeriodicTask 업데이트: {task_name}")
            else:
                print(f"새로운 PeriodicTask 생성: {task_name}")
        
        print(f"배치 스케줄 동기화 완료: {active_schedules.count()}개 스케줄")
        return True
        
    except Exception as e:
        print(f"배치 스케줄 동기화 오류: {str(e)}")
        return False


def create_default_schedule():
    """
    기본 배치 스케줄 생성
    """
    try:
        if not BatchSchedule.objects.exists():
            schedule = BatchSchedule.objects.create(
                name='일일 중재 권고사항 생성',
                frequency='daily',
                hour=9,
                minute=0,
                is_active=True
            )
            print(f"기본 배치 스케줄 생성 완료: {schedule}")
            return schedule
        else:
            print("이미 배치 스케줄이 존재합니다.")
            return None
    except Exception as e:
        print(f"기본 배치 스케줄 생성 오류: {str(e)}")
        return None


def get_schedule_status():
    """
    현재 스케줄 상태 조회
    """
    try:
        schedules = BatchSchedule.objects.all()
        periodic_tasks = PeriodicTask.objects.filter(name__startswith='batch_intervention_')
        
        status = {
            'total_schedules': schedules.count(),
            'active_schedules': schedules.filter(is_active=True).count(),
            'periodic_tasks': periodic_tasks.count(),
            'enabled_tasks': periodic_tasks.filter(enabled=True).count(),
        }
        
        return status
    except Exception as e:
        print(f"스케줄 상태 조회 오류: {str(e)}")
        return None
