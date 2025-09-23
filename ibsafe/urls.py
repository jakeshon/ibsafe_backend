from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.login_with_credentials, name='login_with_credentials'),
    path('auth/google-login/', views.google_login, name='google_login'),
    path('auth/apple-login/', views.apple_login, name='apple_login'),
    path('auth/refresh/', views.refresh_token, name='refresh_token'),
    path('auth/change-password/', views.change_password, name='change_password'),
    path('user/profile/', views.my_profile, name='my_profile'),
    path('user/medications/', views.user_medications, name='user_medications'),
    path('auth/logout/', views.logout, name='logout'),
    path('foods/search/', views.search_foods, name='search_foods'),
    path('foods/records/', views.save_food_records, name='save_food_records'),
    path('foods/records/get/', views.get_food_records, name='get_food_records'),
    path('foods/records/range/', views.get_food_records_by_date_range, name='get_food_records_by_date_range'),
    path('sleep/records/', views.create_sleep_record, name='create_sleep_record'),
    path('sleep/records/get/', views.get_sleep_record, name='get_sleep_record'),
    path('sleep/records/list/', views.get_sleep_records, name='get_sleep_records'),
    
    # IBS-SSS 관련 URL 패턴들
    path('ibssss/records/', views.save_ibssss_record, name='save_ibssss_record'),
    path('ibssss/records/get/', views.get_ibssss_record, name='get_ibssss_record'),
    path('ibssss/records/list/', views.get_ibssss_records, name='get_ibssss_records'),
    path('ibssss/pain-records/', views.get_ibssss_pain_records, name='get_ibssss_pain_records'),
    
    # IBS-QOL 관련 URL 패턴들
    path('ibsqol/records/', views.save_ibsqol_record, name='save_ibsqol_record'),
    path('ibsqol/records/get/', views.get_ibsqol_record, name='get_ibsqol_record'),
    path('ibsqol/records/list/', views.get_ibsqol_records, name='get_ibsqol_records'),
    
    # PSS 스트레스 관련 URL 패턴들
    path('pss-stress/records/', views.save_pss_stress_record, name='save_pss_stress_record'),
    path('pss-stress/records/get/', views.get_pss_stress_record, name='get_pss_stress_record'),
    path('pss-stress/records/list/', views.get_pss_stress_records, name='get_pss_stress_records'),
    
    # 물 섭취량 관련 URL 패턴들
    path('water/records/', views.save_water_record, name='save_water_record'),
    path('water/records/get/', views.get_water_record, name='get_water_record'),
    path('water/records/list/', views.get_water_records, name='get_water_records'),
    
    # 운동 관련 URL 패턴들
    path('exercise/save/', views.save_exercise_record, name='save_exercise_record'),
    path('exercise/records/get/', views.get_exercise_record, name='get_exercise_record'),
    path('exercise/records/list/', views.get_exercise_records, name='get_exercise_records'),
    
    # 중재 관련 URL 패턴들
    path('intervention/record/', views.get_intervention_record, name='get_intervention_record'),
    path('intervention/latest/', views.get_latest_intervention_record, name='get_latest_intervention_record'),
    path('intervention/latest-records/', views.get_latest_intervention_records, name='get_latest_intervention_records'),
    
    # 배치 스케줄 관련 URL 패턴들
    path('batch/schedule/', views.batch_schedule_management, name='batch_schedule_management'),
    path('batch/sync/', views.sync_batch_schedules_api, name='sync_batch_schedules_api'),
    path('batch/run/', views.run_manual_batch, name='run_manual_batch'),
    path('batch/status/', views.get_batch_task_status, name='get_batch_task_status'),
    
    # 알림 스케줄 관련 URL 패턴들
    path('notification-schedules/active/', views.get_active_notification_schedules, name='get_active_notification_schedules'),
    path('notification-schedules/', views.notification_schedule_management, name='notification_schedule_management'),
    
    # 복용약 기록 관련 URL 패턴들
    path('medication/records/', views.create_medication_record, name='create_medication_record'),
    path('medication/records/get/', views.get_medication_record, name='get_medication_record'),
    path('medication/records/list/', views.get_medication_records, name='get_medication_records'),
    path('medication/records/range/', views.get_medication_records_by_date_range, name='get_medication_records_by_date_range'),
    path('medication/records/<int:id>/', views.update_medication_record, name='update_medication_record'),
    path('medication/records/<int:id>/delete/', views.delete_medication_record, name='delete_medication_record'),
] 