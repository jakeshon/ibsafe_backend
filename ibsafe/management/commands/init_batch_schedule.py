from django.core.management.base import BaseCommand
from ibsafe.utils import create_default_schedule, sync_batch_schedules, get_schedule_status


class Command(BaseCommand):
    help = '배치 스케줄을 초기화하고 동기화합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='기존 스케줄이 있어도 강제로 생성합니다.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== 배치 스케줄 초기화 시작 ==='))
        
        try:
            # 기본 스케줄 생성
            if options['force']:
                self.stdout.write('기존 스케줄을 삭제하고 새로 생성합니다...')
                from ibsafe.models import BatchSchedule
                BatchSchedule.objects.all().delete()
            
            schedule = create_default_schedule()
            if schedule:
                self.stdout.write(
                    self.style.SUCCESS(f'기본 스케줄 생성 완료: {schedule}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('기본 스케줄이 이미 존재합니다.')
                )
            
            # 스케줄 동기화
            self.stdout.write('Celery Beat 스케줄 동기화 중...')
            sync_success = sync_batch_schedules()
            
            if sync_success:
                self.stdout.write(
                    self.style.SUCCESS('스케줄 동기화 완료')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('스케줄 동기화 실패')
                )
            
            # 현재 상태 출력
            status = get_schedule_status()
            if status:
                self.stdout.write('=== 현재 스케줄 상태 ===')
                self.stdout.write(f'총 스케줄: {status["total_schedules"]}개')
                self.stdout.write(f'활성 스케줄: {status["active_schedules"]}개')
                self.stdout.write(f'PeriodicTask: {status["periodic_tasks"]}개')
                self.stdout.write(f'활성화된 태스크: {status["enabled_tasks"]}개')
            
            self.stdout.write(
                self.style.SUCCESS('=== 배치 스케줄 초기화 완료 ===')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'배치 스케줄 초기화 중 오류 발생: {str(e)}')
            )
