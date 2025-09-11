from django.core.management.base import BaseCommand
from ibsafe.models import IBSSSSQuestion


class Command(BaseCommand):
    help = 'IBS-SSS 설문 질문들을 초기화합니다.'

    def handle(self, *args, **options):
        questions_data = [
            {
                'question_number': 1,
                'question_text': '귀하는 현재 (최근) 복부 통증이 있습니까?',
                'question_type': 'yes_no',
                'description': '복부 통증의 유무를 확인하는 질문입니다.'
            },
            {
                'question_number': 2,
                'question_text': '복통이 있거나 있었다면 어느 정도였습니까?',
                'question_type': 'intensity',
                'description': '복부 통증의 강도를 0-100 사이에서 평가합니다.'
            },
            {
                'question_number': 3,
                'question_text': '10일 중 복통이 있는 날은 며칠입니까?',
                'question_type': 'days',
                'description': '최근 10일간 복통이 있었던 일수를 확인합니다.'
            },
            {
                'question_number': 4,
                'question_text': '귀하는 현재 (최근) 복부 팽만감이 있습니까?',
                'question_type': 'yes_no',
                'description': '배가 심하게 부르거나, 가스가 많이 찬 느낌 (여성인 경우, 생리기간 중의 불편감은 제외합니다.)'
            },
            {
                'question_number': 5,
                'question_text': '복부팽만감이 있거나 있었다면 어느 정도였습니까?',
                'question_type': 'intensity',
                'description': '복부 팽만감의 강도를 0-100 사이에서 평가합니다.'
            },
            {
                'question_number': 6,
                'question_text': '귀하의 배변 습관에 대해 만족하십니까?',
                'question_type': 'satisfaction',
                'description': '배변 습관에 대한 만족도를 0-100 사이에서 평가합니다.'
            },
            {
                'question_number': 7,
                'question_text': '과민성 장증후군 증상이 당신의 삶을 어느정도 방해 합니까?',
                'question_type': 'interference',
                'description': 'IBS 증상이 일상생활에 미치는 영향을 0-100 사이에서 평가합니다.'
            },
        ]

        created_count = 0
        updated_count = 0

        for question_data in questions_data:
            question, created = IBSSSSQuestion.objects.update_or_create(
                question_number=question_data['question_number'],
                defaults={
                    'question_text': question_data['question_text'],
                    'question_type': question_data['question_type'],
                    'description': question_data['description'],
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'질문 {question.question_number}이(가) 생성되었습니다.')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'질문 {question.question_number}이(가) 업데이트되었습니다.')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'완료! 생성: {created_count}개, 업데이트: {updated_count}개'
            )
        ) 