#!/usr/bin/env python3
"""
SystemProfile 데이터 생성 스크립트
"""
import os
import sys
import django

# Django 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ibsafe.models import SystemProfile

def create_system_profiles():
    """시스템 프로필 데이터 생성"""
    
    # Android 프로필
    android_profile, created = SystemProfile.objects.get_or_create(
        platform='android',
        defaults={
            'version': '0.1.10+10',
            'download_url': 'https://play.google.com/store/apps/details?id=com.ibsafe.app',
            'is_active': True,
        }
    )
    
    if created:
        print(f"Android 프로필 생성됨: {android_profile}")
    else:
        print(f"Android 프로필이 이미 존재함: {android_profile}")
    
    # iOS 프로필
    ios_profile, created = SystemProfile.objects.get_or_create(
        platform='ios',
        defaults={
            'version': '0.1.10+10',
            'download_url': 'https://apps.apple.com/app/ibsafe/id123456789',
            'is_active': True,
        }
    )
    
    if created:
        print(f"iOS 프로필 생성됨: {ios_profile}")
    else:
        print(f"iOS 프로필이 이미 존재함: {ios_profile}")
    
    print("\n=== 현재 시스템 프로필 목록 ===")
    for profile in SystemProfile.objects.all():
        print(f"플랫폼: {profile.platform}")
        print(f"버전: {profile.version}")
        print(f"다운로드 URL: {profile.download_url}")
        print(f"활성화: {profile.is_active}")
        print("-" * 50)

if __name__ == '__main__':
    create_system_profiles()
