import re
from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import UserProfile, SocialAccount, Food, UserFoodRecord, UserSleepRecord, UserMedication, MedicationRecord, IBSSSSRecord, IBSSSSPainRecord, IBSQOLRecord, PSSStressRecord, UserWaterRecord, UserExerciseRecord, InterventionRecord, BatchSchedule, NotificationSchedule
import requests
import json
import os
import sys
import torch
import gc
import time
import pandas as pd
import numpy as np

# Create your views here.

@api_view(['POST'])
@permission_classes([AllowAny])
def login_with_credentials(request):
    """
    ID/PW 로그인 API
    """
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': '사용자명과 비밀번호가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 사용자 인증
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response(
                {'error': '사용자명 또는 비밀번호가 올바르지 않습니다.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # JWT 토큰 생성
        refresh = RefreshToken.for_user(user)
        
        # 프로필이 없으면 생성
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)
        
        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile_image': user.profile.profile_image if hasattr(user, 'profile') else None,
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'로그인 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    """
    구글 로그인 API
    """
    try:
        # 요청 데이터에서 access_token 추출
        access_token = request.data.get('access_token')
        
        if not access_token:
            return Response(
                {'error': 'Access token이 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Google API를 통해 사용자 정보 가져오기
        google_user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(google_user_info_url, headers=headers)
        
        if response.status_code != 200:
            return Response(
                {'error': 'Google API에서 사용자 정보를 가져올 수 없습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        user_info = response.json()
        provider_id = user_info.get('id')
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')

        # 기존 사용자 확인 (소셜 계정으로)
        try:
            social_account = SocialAccount.objects.get(
                provider='google',
                provider_id=provider_id
            )
            user = social_account.user
        except SocialAccount.DoesNotExist:
            # 새 사용자 생성
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                # 기존 사용자에게 소셜 계정 추가
                SocialAccount.objects.create(
                    user=user,
                    provider='google',
                    provider_id=provider_id
                )
                # 프로필이 없으면 생성
                if not hasattr(user, 'profile'):
                    UserProfile.objects.create(
                        user=user,
                        profile_image=picture
                    )
                else:
                    # 기존 프로필에 이미지 업데이트
                    user.profile.profile_image = picture
                    user.profile.save()
            else:
                # 완전히 새로운 사용자 생성
                username = f"google_{provider_id}"
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=name.split()[0] if name else '',
                    last_name=' '.join(name.split()[1:]) if name and len(name.split()) > 1 else ''
                )
                # 소셜 계정 생성
                SocialAccount.objects.create(
                    user=user,
                    provider='google',
                    provider_id=provider_id
                )
                # 프로필 생성
                UserProfile.objects.create(
                    user=user,
                    profile_image=picture
                )

        # JWT 토큰 생성
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile_image': user.profile.profile_image,
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'로그인 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    비밀번호 변경 API
    """
    try:
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        is_first_login = request.data.get('is_first_login', False)
        
        if not new_password:
            return Response(
                {'error': '새 비밀번호가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 첫 로그인이 아닌 경우에만 현재 비밀번호 확인
        if not is_first_login:
            if not current_password:
                return Response(
                    {'error': '현재 비밀번호가 필요합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 현재 비밀번호 확인
            if not user.check_password(current_password):
                return Response(
                    {'error': '현재 비밀번호가 올바르지 않습니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 새 비밀번호 설정
        user.set_password(new_password)
        user.save()
        
        # 프로필의 is_password_changed를 true로 설정
        if hasattr(user, 'profile'):
            user.profile.is_password_changed = True
            user.profile.save()
        
        return Response({
            'message': '비밀번호가 성공적으로 변경되었습니다.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'비밀번호 변경 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def my_profile(request):
    """
    현재 로그인한 사용자의 프로필 정보 조회 및 업데이트 API
    """
    try:
        user = request.user
        
        # 프로필이 없으면 생성
        if not hasattr(user, 'profile'):
            profile = UserProfile.objects.create(user=user)
        else:
            profile = user.profile
        
        if request.method == 'GET':
            # 프로필 조회
            try:
                response_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'profile_image': profile.profile_image,
                    'gender': profile.gender,
                    'birth_date': profile.birth_date.isoformat() if profile.birth_date else None,
                    'height': profile.height,
                    'weight': float(profile.weight) if profile.weight else None,
                    'step_count': profile.step_count,
                    'sleep_time': profile.sleep_time,
                    'water_intake': profile.water_intake,
                    'has_breakfast': profile.has_breakfast,
                    'has_lunch': profile.has_lunch,
                    'has_dinner': profile.has_dinner,
                    'has_gluten_allergy': profile.has_gluten_allergy,
                    'has_lactose_allergy': profile.has_lactose_allergy,
                    'has_nut_allergy': profile.has_nut_allergy,
                    'has_seafood_allergy': profile.has_seafood_allergy,
                    'has_egg_allergy': profile.has_egg_allergy,
                    'has_soy_allergy': profile.has_soy_allergy,
                    'has_lactose_intolerance': profile.has_lactose_intolerance,
                    'food_preference': profile.food_preference,
                    'is_password_changed': getattr(profile, 'is_password_changed', False),
                    'created_at': profile.created_at.isoformat() if hasattr(profile, 'created_at') and profile.created_at else None,
                }
                return Response(response_data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {'error': f'프로필 데이터 생성 중 오류: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        elif request.method == 'PUT':
            # 프로필 업데이트
            data = request.data
            
            # 기본 신체 정보
            if 'gender' in data:
                profile.gender = data['gender']
            if 'birth_date' in data:
                from datetime import datetime
                try:
                    profile.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass
            if 'height' in data:
                profile.height = data['height']
            if 'weight' in data:
                profile.weight = data['weight']
            
            # 목표 설정
            if 'step_count' in data:
                profile.step_count = data['step_count']
            if 'sleep_time' in data:
                profile.sleep_time = data['sleep_time']
            if 'water_intake' in data:
                profile.water_intake = data['water_intake']
            
            # 식사 패턴
            if 'has_breakfast' in data:
                profile.has_breakfast = data['has_breakfast']
            if 'has_lunch' in data:
                profile.has_lunch = data['has_lunch']
            if 'has_dinner' in data:
                profile.has_dinner = data['has_dinner']
            
            # 음식 알러지
            if 'has_gluten_allergy' in data:
                profile.has_gluten_allergy = data['has_gluten_allergy']
            if 'has_lactose_allergy' in data:
                profile.has_lactose_allergy = data['has_lactose_allergy']
            if 'has_nut_allergy' in data:
                profile.has_nut_allergy = data['has_nut_allergy']
            if 'has_seafood_allergy' in data:
                profile.has_seafood_allergy = data['has_seafood_allergy']
            if 'has_egg_allergy' in data:
                profile.has_egg_allergy = data['has_egg_allergy']
            if 'has_soy_allergy' in data:
                profile.has_soy_allergy = data['has_soy_allergy']
            
            # 유당불내증
            if 'has_lactose_intolerance' in data:
                profile.has_lactose_intolerance = data['has_lactose_intolerance']
            
            # 음식 선호도
            if 'food_preference' in data:
                profile.food_preference = data['food_preference']
            
            profile.save()
            
            return Response({
                'message': '프로필이 성공적으로 업데이트되었습니다.',
                'gender': profile.gender,
                'birth_date': profile.birth_date.isoformat() if profile.birth_date else None,
                'height': profile.height,
                'weight': float(profile.weight) if profile.weight else None,
                'step_count': profile.step_count,
                'sleep_time': profile.sleep_time,
                'water_intake': profile.water_intake,
                'has_breakfast': profile.has_breakfast,
                'has_lunch': profile.has_lunch,
                'has_dinner': profile.has_dinner,
                'has_gluten_allergy': profile.has_gluten_allergy,
                'has_lactose_allergy': profile.has_lactose_allergy,
                'has_nut_allergy': profile.has_nut_allergy,
                'has_seafood_allergy': profile.has_seafood_allergy,
                'has_egg_allergy': profile.has_egg_allergy,
                'has_soy_allergy': profile.has_soy_allergy,
                'has_lactose_intolerance': profile.has_lactose_intolerance,
                'food_preference': profile.food_preference,
            }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'프로필 처리 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_medications(request):
    """
    사용자 복용약 관리 API
    """
    try:
        user = request.user
        
        if request.method == 'GET':
            # 복용약 목록 조회
            medications = user.medications.all()
            return Response({
                'medications': [
                    {
                        'id': med.id,
                        'medication_name': med.medication_name,
                        'has_breakfast': med.has_breakfast,
                        'has_lunch': med.has_lunch,
                        'has_dinner': med.has_dinner,
                        'has_as_needed': med.has_as_needed,
                        'created_at': med.created_at,
                    }
                    for med in medications
                ]
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'POST':
            # 복용약 추가
            print(f"=== 복용약 추가 API 호출됨 ===")
            print(f"요청 데이터: {request.data}")
            print(f"요청 사용자: {user.username}")
            
            data = request.data
            medication_name = data.get('medication_name')
            has_breakfast = data.get('has_breakfast', False)
            has_lunch = data.get('has_lunch', False)
            has_dinner = data.get('has_dinner', False)
            has_as_needed = data.get('has_as_needed', False)
            
            print(f"약 이름: {medication_name}")
            print(f"복용 시기: 아침={has_breakfast}, 점심={has_lunch}, 저녁={has_dinner}, 필요시={has_as_needed}")
            
            if not medication_name:
                return Response(
                    {'error': '약 이름이 필요합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 최소 하나의 복용 시기는 선택되어야 함
            if not any([has_breakfast, has_lunch, has_dinner, has_as_needed]):
                return Response(
                    {'error': '최소 하나의 복용 시기를 선택해주세요.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                medication = UserMedication.objects.create(
                    user=user,
                    medication_name=medication_name,
                    has_breakfast=has_breakfast,
                    has_lunch=has_lunch,
                    has_dinner=has_dinner,
                    has_as_needed=has_as_needed
                )
                print(f"복용약 생성 성공: {medication.id} - {medication_name}")
            except Exception as create_error:
                print(f"복용약 생성 실패: {create_error}")
                raise create_error
            
            return Response({
                'message': '복용약이 성공적으로 추가되었습니다.',
                'medication': {
                    'id': medication.id,
                    'medication_name': medication.medication_name,
                    'has_breakfast': medication.has_breakfast,
                    'has_lunch': medication.has_lunch,
                    'has_dinner': medication.has_dinner,
                    'has_as_needed': medication.has_as_needed,
                    'created_at': medication.created_at,
                }
            }, status=status.HTTP_201_CREATED)
        
        elif request.method == 'DELETE':
            # 복용약 삭제
            medication_id = request.data.get('medication_id')
            if not medication_id:
                return Response(
                    {'error': '삭제할 복용약 ID가 필요합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                medication = user.medications.get(id=medication_id)
                medication.delete()
                return Response({
                    'message': '복용약이 성공적으로 삭제되었습니다.'
                }, status=status.HTTP_200_OK)
            except UserMedication.DoesNotExist:
                return Response(
                    {'error': '해당 복용약을 찾을 수 없습니다.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
    except Exception as e:
        return Response(
            {'error': f'복용약 처리 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def apple_login(request):
    """
    애플 로그인 API
    """
    try:
        # 요청 데이터에서 identity_token 추출
        identity_token = request.data.get('identity_token')
        user_identifier = request.data.get('user_identifier')
        email = request.data.get('email')
        name = request.data.get('name')
        
        if not identity_token or not user_identifier:
            return Response(
                {'error': 'Identity token과 user identifier가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 기존 사용자 확인 (소셜 계정으로)
        try:
            social_account = SocialAccount.objects.get(
                provider='apple',
                provider_id=user_identifier
            )
            user = social_account.user
        except SocialAccount.DoesNotExist:
            # 새 사용자 생성
            if email and User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                # 기존 사용자에게 소셜 계정 추가
                SocialAccount.objects.create(
                    user=user,
                    provider='apple',
                    provider_id=user_identifier
                )
                # 프로필이 없으면 생성
                if not hasattr(user, 'profile'):
                    UserProfile.objects.create(user=user)
            else:
                # 완전히 새로운 사용자 생성
                username = f"apple_{user_identifier}"
                user = User.objects.create_user(
                    username=username,
                    email=email or '',
                    first_name=name.split()[0] if name else '',
                    last_name=' '.join(name.split()[1:]) if name and len(name.split()) > 1 else ''
                )
                # 소셜 계정 생성
                SocialAccount.objects.create(
                    user=user,
                    provider='apple',
                    provider_id=user_identifier
                )
                # 프로필 생성
                UserProfile.objects.create(user=user)

        # JWT 토큰 생성
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile_image': user.profile.profile_image,
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'로그인 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Refresh Token을 사용하여 새로운 Access Token 발급 API
    """
    try:
        refresh_token = request.data.get('refresh_token')
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh token이 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Refresh Token 검증 및 새로운 Access Token 발급
        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)
            
            # refresh token에서 user 정보 추출
            user_id = refresh.payload.get('user_id')
            if user_id:
                user = User.objects.get(id=user_id)
                return Response({
                    'access_token': new_access_token,
                    'refresh_token': str(refresh),  # 새로운 refresh token (ROTATE_REFRESH_TOKENS=True인 경우)
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'profile_image': user.profile.profile_image if hasattr(user, 'profile') else None,
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'access_token': new_access_token,
                    'refresh_token': str(refresh),
                    'user': {
                        'id': 0,
                        'username': '',
                        'email': '',
                        'first_name': '',
                        'last_name': '',
                        'profile_image': None,
                    }
                }, status=status.HTTP_200_OK)
            
        except TokenError as e:
            return Response(
                {'error': '유효하지 않은 refresh token입니다.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
    except Exception as e:
        return Response(
            {'error': f'토큰 갱신 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    로그아웃 API
    """
    try:
        # 클라이언트에서 토큰을 삭제하도록 안내
        return Response({
            'message': '로그아웃되었습니다.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'로그아웃 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def search_foods(request):
    """
    음식 검색 API
    """
    try:
        query = request.GET.get('q', '').strip()
        
        if not query:
            return Response(
                {'error': '검색어가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 띄어쓰기 기준으로 검색어 분리
        search_terms = query.split()
        
        # 각 검색어에 대해 AND 조건으로 필터링
        foods = Food.objects.all()
        for term in search_terms:
            if term.strip():  # 빈 문자열이 아닌 경우만
                foods = foods.filter(food_name__icontains=term.strip())
        
        # 최대 20개 결과로 제한
        foods = foods[:20]
        
        results = []
        for food in foods:
            results.append({
                'id': food.food_code,
                'name': food.food_name,
                'calories': food.energy_kcal or 0,
                'protein': float(food.protein_g) if food.protein_g else 0.0,
                'fat': float(food.fat_g) if food.fat_g else 0.0,
                'carbs': float(food.carbohydrates_g) if food.carbohydrates_g else 0.0,
                'amount': 100,  # 기본 100g 기준
                'category': food.category.main_category_name if food.category else '',
                'fodmap': food.fodmap,
                'dietary_fiber_type': food.dietary_fiber_type,
            })
        
        return Response({
            'results': results,
            'count': len(results),
            'query': query
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'음식 검색 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_food_records(request):
    """
    음식 기록 저장 API
    """
    try:
        print("=== 음식 기록 저장 API 호출됨 ===")
        print(f"요청 데이터: {request.data}")
        print(f"요청 사용자: {request.user}")
        
        data = request.data
        record_date = data.get('record_date')  # YYYY-MM-DD 형식
        meal_records = data.get('meal_records', {})  # {'breakfast': [...], 'lunch': [...], 'dinner': [...]}
        
        print(f"기록 날짜: {record_date}")
        print(f"식사 기록: {meal_records}")
        
        if not record_date:
            return Response(
                {'error': '기록 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 기존 기록 삭제 (같은 날짜의 같은 사용자 기록)
        UserFoodRecord.objects.filter(
            user=request.user,
            record_date=record_date
        ).delete()
        
        saved_records = []
        
        # 각 식사 타입별로 기록 저장
        for meal_type, foods in meal_records.items():
            if not foods:  # 빈 리스트는 건너뛰기
                continue
                
            for food_data in foods:
                try:
                    # 음식 객체 찾기
                    food = Food.objects.get(food_code=food_data['food_id'])
                    
                    # 음식 기록 생성
                    food_record = UserFoodRecord.objects.create(
                        user=request.user,
                        food=food,
                        meal_type=meal_type,
                        amount=food_data['amount'],
                        record_date=record_date
                    )
                    
                    saved_records.append({
                        'id': food_record.id,
                        'food_name': food.food_name,
                        'meal_type': food_record.get_meal_type_display(),
                        'amount': float(food_record.amount),
                        'calories': food_record.total_calories,
                        'protein': food_record.total_protein,
                        'fat': food_record.total_fat,
                        'carbohydrates': food_record.total_carbohydrates,
                    })
                    
                except Food.DoesNotExist:
                    return Response(
                        {'error': f'음식 코드 {food_data["food_id"]}를 찾을 수 없습니다.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                except Exception as e:
                    return Response(
                        {'error': f'음식 기록 저장 중 오류가 발생했습니다: {str(e)}'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
        
        return Response({
            'message': '음식 기록이 성공적으로 저장되었습니다.',
            'saved_records': saved_records,
            'total_records': len(saved_records)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'음식 기록 저장 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_food_records(request):
    """
    특정 날짜의 음식 기록 조회 API
    """
    try:
        record_date = request.GET.get('date')  # YYYY-MM-DD 형식
        
        if not record_date:
            return Response(
                {'error': '조회할 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 날짜의 음식 기록 조회
        food_records = UserFoodRecord.objects.filter(
            user=request.user,
            record_date=record_date
        ).select_related('food').order_by('meal_type', 'created_at')
        
        # 식사 타입별로 그룹화
        meal_records = {
            'breakfast': [],
            'lunch': [],
            'dinner': [],
        }
        
        for record in food_records:
            meal_records[record.meal_type].append({
                'id': record.id,
                'food_id': record.food.food_code,
                'food_name': record.food.food_name,
                'amount': float(record.amount or 0),
                'calories': float(record.total_calories or 0),
                'protein': float(record.total_protein or 0),
                'fat': float(record.total_fat or 0),
                'carbohydrates': float(record.total_carbohydrates or 0),
                'category': record.food.category.main_category_name if record.food.category else '',
                'fodmap': record.food.fodmap or '',
                'dietary_fiber_type': record.food.dietary_fiber_type or '',
            })
        
        return Response({
            'record_date': record_date,
            'meal_records': meal_records,
            'total_records': food_records.count()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'음식 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_food_records_by_date_range(request):
    """
    기간별 음식 기록 조회 API
    """
    try:
        start_date = request.GET.get('start_date')  # YYYY-MM-DD 형식
        end_date = request.GET.get('end_date')      # YYYY-MM-DD 형식
        
        if not start_date or not end_date:
            return Response(
                {'error': '시작 날짜와 종료 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 기간별 음식 기록 조회
        food_records = UserFoodRecord.objects.filter(
            user=request.user,
            record_date__range=[start_date, end_date]
        ).select_related('food').order_by('record_date', 'meal_type', 'created_at')
        
        # 날짜별로 그룹화
        date_records = {}
        
        for record in food_records:
            record_date = record.record_date.strftime('%Y-%m-%d')
            
            if record_date not in date_records:
                date_records[record_date] = {
                    'record_date': record_date,
                    'meal_records': {
                        'breakfast': [],
                        'lunch': [],
                        'dinner': [],
                    }
                }
            
            date_records[record_date]['meal_records'][record.meal_type].append({
                'id': record.id,
                'food_id': record.food.food_code,
                'food_name': record.food.food_name,
                'amount': float(record.amount or 0),
                'calories': float(record.total_calories or 0),
                'protein': float(record.total_protein or 0),
                'fat': float(record.total_fat or 0),
                'carbohydrates': float(record.total_carbohydrates or 0),
                'category': record.food.category.main_category_name if record.food.category else '',
                'fodmap': record.food.fodmap or '',
                'dietary_fiber_type': record.food.dietary_fiber_type or '',
            })
        
        # 리스트로 변환
        food_records_list = list(date_records.values())
        
        return Response({
            'message': '기간별 음식 기록 조회 성공',
            'foodRecords': food_records_list
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'기간별 음식 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_sleep_record(request):
    """
    수면 기록 생성 API
    """
    try:
        print(f"=== 수면 기록 생성 요청 ===")
        print(f"요청 데이터: {request.data}")
        print(f"요청 데이터 타입: {type(request.data)}")
        print(f"Content-Type: {request.content_type}")
        print(f"요청 헤더: {dict(request.headers)}")
        
        sleep_minutes = request.data.get('sleep_minutes')
        record_date = request.data.get('record_date')
        
        print(f"sleep_minutes: {sleep_minutes} (타입: {type(sleep_minutes)})")
        print(f"record_date: {record_date} (타입: {type(record_date)})")
        
        # 요청 데이터의 모든 키 확인
        if isinstance(request.data, dict):
            print(f"요청 데이터 키들: {list(request.data.keys())}")
            for key, value in request.data.items():
                print(f"  {key}: {value} (타입: {type(value)})")
        else:
            print(f"요청 데이터가 딕셔너리가 아님: {request.data}")
            print(f"요청 데이터 타입: {type(request.data)}")
            if hasattr(request.data, '__dict__'):
                print(f"요청 데이터 속성들: {request.data.__dict__}")
        
        if not sleep_minutes or not record_date:
            print(f"=== 400 에러: 필수 데이터 누락 ===")
            print(f"sleep_minutes: {sleep_minutes}")
            print(f"record_date: {record_date}")
            return Response(
                {'error': '수면 시간과 기록 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 기존 기록이 있는지 확인
        existing_record = UserSleepRecord.objects.filter(
            user=request.user,
            record_date=record_date
        ).first()
        
        if existing_record:
            # 기존 기록 업데이트
            existing_record.sleep_minutes = sleep_minutes
            existing_record.save()
            
            return Response({
                'message': '수면 기록이 업데이트되었습니다.',
                'sleep_record': {
                    'id': existing_record.id,
                    'sleep_minutes': existing_record.sleep_minutes,
                    'sleep_hours': existing_record.sleep_hours,
                    'formatted_sleep_time': existing_record.formatted_sleep_time,
                    'record_date': str(existing_record.record_date),
                    'created_at': existing_record.created_at.isoformat(),
                    'updated_at': existing_record.updated_at.isoformat(),
                }
            }, status=status.HTTP_200_OK)
        else:
            # 새 기록 생성
            sleep_record = UserSleepRecord.objects.create(
                user=request.user,
                sleep_minutes=sleep_minutes,
                record_date=record_date
            )
            
            return Response({
                'message': '수면 기록이 성공적으로 저장되었습니다.',
                'sleep_record': {
                    'id': sleep_record.id,
                    'sleep_minutes': sleep_record.sleep_minutes,
                    'sleep_hours': sleep_record.sleep_hours,
                    'formatted_sleep_time': sleep_record.formatted_sleep_time,
                    'record_date': str(sleep_record.record_date),
                    'created_at': sleep_record.created_at.isoformat(),
                    'updated_at': sleep_record.updated_at.isoformat(),
                }
            }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"=== 500 에러: 수면 기록 저장 중 예외 발생 ===")
        print(f"예외 내용: {str(e)}")
        print(f"예외 타입: {type(e)}")
        import traceback
        print(f"스택 트레이스: {traceback.format_exc()}")
        return Response(
            {'error': f'수면 기록 저장 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sleep_records(request):
    """
    기간별 수면 기록 조회 API
    """
    try:
        start_date = request.GET.get('start_date')  # YYYY-MM-DD 형식
        end_date = request.GET.get('end_date')  # YYYY-MM-DD 형식
        
        if not start_date or not end_date:
            return Response(
                {'error': '시작 날짜와 종료 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 기간의 수면 기록 조회
        sleep_records = UserSleepRecord.objects.filter(
            user=request.user,
            record_date__range=[start_date, end_date]
        ).order_by('record_date')
        
        records = []
        for record in sleep_records:
            records.append({
                'id': record.id,
                'sleep_minutes': record.sleep_minutes,
                'sleep_hours': record.sleep_hours,
                'formatted_sleep_time': record.formatted_sleep_time,
                'record_date': str(record.record_date),
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat(),
            })
        
        return Response({
            'message': '수면 기록을 성공적으로 조회했습니다.',
            'sleep_records': records
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'수면 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sleep_record(request):
    """
    특정 날짜의 수면 기록 조회 API
    """
    try:
        record_date = request.GET.get('date')  # YYYY-MM-DD 형식
        
        if not record_date:
            return Response(
                {'error': '조회할 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 날짜의 수면 기록 조회
        sleep_record = UserSleepRecord.objects.filter(
            user=request.user,
            record_date=record_date
        ).first()
        
        if not sleep_record:
            return Response(
                {
                    'message': '해당 날짜의 수면 기록이 없습니다.',
                    'sleep_record': None
                }, 
                status=status.HTTP_200_OK
            )
        
        return Response({
            'message': '수면 기록을 성공적으로 조회했습니다.',
            'sleep_record': {
                'id': sleep_record.id,
                'sleep_minutes': sleep_record.sleep_minutes,
                'sleep_hours': sleep_record.sleep_hours,
                'formatted_sleep_time': sleep_record.formatted_sleep_time,
                'record_date': str(sleep_record.record_date),
                'created_at': sleep_record.created_at.isoformat(),
                'updated_at': sleep_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'수면 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_ibssss_record(request):
    """
    IBS-SSS 설문 기록을 저장하는 API
    """
    try:
        user = request.user
        
        # 요청 데이터 추출
        data = request.data
        
        # 필수 필드 검증
        required_fields = [
            'question_1', 'question_2', 'question_3',
            'question_4', 'question_5', 'question_6', 'question_7'
        ]
        
        for field in required_fields:
            if field not in data:
                return Response(
                    {'error': f'필수 필드가 누락되었습니다: {field}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 통증 기록 데이터 추출
        pain_records = data.get('pain_records', [])
        
        # 기록 저장 또는 업데이트
        record_date = data.get('record_date')
        if not record_date:
            from datetime import date
            record_date = date.today()
        
        ibssss_record, created = IBSSSSRecord.objects.update_or_create(
            user=user,
            record_date=record_date,
            defaults={
                'question_1': data['question_1'],
                'question_2': data['question_2'],
                'question_3': data['question_3'],
                'question_4': data['question_4'],
                'question_5': data['question_5'],
                'question_6': data['question_6'],
                'question_7': data['question_7'],
            }
        )
        
        # update_or_create는 모델의 save() 메서드를 호출하지 않으므로 수동으로 총점과 심각도 업데이트
        ibssss_record.total_score = ibssss_record.calculate_total_score()
        ibssss_record.severity = ibssss_record.calculate_severity()
        ibssss_record.save(update_fields=['total_score', 'severity'])
        
        # 통증 기록 저장
        for pain_record in pain_records:
            record_date = pain_record.get('date')
            has_pain = pain_record.get('has_pain', False)
            
            if record_date:
                IBSSSSPainRecord.objects.update_or_create(
                    user=user,
                    record_date=record_date,
                    defaults={'has_pain': has_pain}
                )
        
        # 총점과 심각도 계산
        total_score = ibssss_record.total_score
        severity = ibssss_record.severity
        
        return Response({
            'message': 'IBS-SSS 기록이 성공적으로 저장되었습니다.',
            'record_id': ibssss_record.id,
            'total_score': total_score,
            'severity': severity,
            'created': created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'기록 저장 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_ibsqol_record(request):
    """
    IBS-QOL 설문 기록을 저장하는 API
    """
    try:
        user = request.user
        
        # 요청 데이터 추출
        data = request.data
        
        # 필수 필드 검증 (34개 질문)
        required_fields = [f'question_{i}' for i in range(1, 35)]
        
        for field in required_fields:
            if field not in data:
                return Response(
                    {'error': f'필수 필드가 누락되었습니다: {field}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 기록 저장 또는 업데이트
        record_date = data.get('record_date')
        if not record_date:
            from datetime import date
            record_date = date.today()
        
        ibsqol_record, created = IBSQOLRecord.objects.update_or_create(
            user=user,
            record_date=record_date,
            defaults={
                'question_1': data['question_1'],
                'question_2': data['question_2'],
                'question_3': data['question_3'],
                'question_4': data['question_4'],
                'question_5': data['question_5'],
                'question_6': data['question_6'],
                'question_7': data['question_7'],
                'question_8': data['question_8'],
                'question_9': data['question_9'],
                'question_10': data['question_10'],
                'question_11': data['question_11'],
                'question_12': data['question_12'],
                'question_13': data['question_13'],
                'question_14': data['question_14'],
                'question_15': data['question_15'],
                'question_16': data['question_16'],
                'question_17': data['question_17'],
                'question_18': data['question_18'],
                'question_19': data['question_19'],
                'question_20': data['question_20'],
                'question_21': data['question_21'],
                'question_22': data['question_22'],
                'question_23': data['question_23'],
                'question_24': data['question_24'],
                'question_25': data['question_25'],
                'question_26': data['question_26'],
                'question_27': data['question_27'],
                'question_28': data['question_28'],
                'question_29': data['question_29'],
                'question_30': data['question_30'],
                'question_31': data['question_31'],
                'question_32': data['question_32'],
                'question_33': data['question_33'],
                'question_34': data['question_34'],
            }
        )
        
        # update_or_create는 모델의 save() 메서드를 호출하지 않으므로 수동으로 총점과 삶의 질 수준 업데이트
        ibsqol_record.total_score = ibsqol_record.calculate_total_score()
        ibsqol_record.quality_level = ibsqol_record.calculate_quality_level()
        ibsqol_record.save(update_fields=['total_score', 'quality_level'])
        
        # 총점과 삶의 질 수준 계산
        total_score = ibsqol_record.total_score
        quality_level = ibsqol_record.quality_level
        
        return Response({
            'message': 'IBS-QOL 기록이 성공적으로 저장되었습니다.',
            'record_id': ibsqol_record.id,
            'total_score': total_score,
            'quality_level': quality_level,
            'created': created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'기록 저장 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_pss_stress_record(request):
    """
    PSS 스트레스 설문 기록을 저장하는 API
    """
    try:
        user = request.user
        
        # 요청 데이터 추출
        data = request.data
        
        # 필수 필드 검증 (10개 질문)
        required_fields = [f'question_{i}' for i in range(1, 11)]
        
        for field in required_fields:
            if field not in data:
                return Response(
                    {'error': f'필수 필드가 누락되었습니다: {field}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 기록 저장 또는 업데이트
        record_date = data.get('record_date')
        if not record_date:
            from datetime import date
            record_date = date.today()
        
        pss_stress_record, created = PSSStressRecord.objects.update_or_create(
            user=user,
            record_date=record_date,
            defaults={
                'question_1': data['question_1'],
                'question_2': data['question_2'],
                'question_3': data['question_3'],
                'question_4': data['question_4'],
                'question_5': data['question_5'],
                'question_6': data['question_6'],
                'question_7': data['question_7'],
                'question_8': data['question_8'],
                'question_9': data['question_9'],
                'question_10': data['question_10'],
            }
        )
        
        # update_or_create는 모델의 save() 메서드를 호출하지 않으므로 수동으로 총점과 스트레스 수준 업데이트
        pss_stress_record.total_score = pss_stress_record.calculate_total_score()
        pss_stress_record.stress_level = pss_stress_record.calculate_stress_level()
        pss_stress_record.save(update_fields=['total_score', 'stress_level'])
        
        # 총점과 스트레스 수준 계산
        total_score = pss_stress_record.total_score
        stress_level = pss_stress_record.stress_level
        
        return Response({
            'message': 'PSS 스트레스 기록이 성공적으로 저장되었습니다.',
            'record_id': pss_stress_record.id,
            'total_score': total_score,
            'stress_level': stress_level,
            'created': created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'기록 저장 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ibssss_record(request):
    """
    특정 날짜의 IBS-SSS 기록 조회 API
    """
    try:
        record_date = request.GET.get('date')  # YYYY-MM-DD 형식
        
        if not record_date:
            return Response(
                {'error': '조회할 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 날짜의 IBS-SSS 기록 조회
        ibssss_record = IBSSSSRecord.objects.filter(
            user=request.user,
            record_date=record_date
        ).first()
        
        if not ibssss_record:
            return Response(
                {
                    'message': '해당 날짜의 IBS-SSS 기록이 없습니다.',
                    'ibssss_record': None
                }, 
                status=status.HTTP_200_OK
            )
        
        return Response({
            'message': 'IBS-SSS 기록을 성공적으로 조회했습니다.',
            'ibssss_record': {
                'id': ibssss_record.id,
                'question_1': ibssss_record.question_1,
                'question_2': ibssss_record.question_2,
                'question_3': ibssss_record.question_3,
                'question_4': ibssss_record.question_4,
                'question_5': ibssss_record.question_5,
                'question_6': ibssss_record.question_6,
                'question_7': ibssss_record.question_7,
                'total_score': ibssss_record.total_score,
                'severity': ibssss_record.severity,
                'record_date': str(ibssss_record.record_date),
                'created_at': ibssss_record.created_at.isoformat(),
                'updated_at': ibssss_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'IBS-SSS 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ibsqol_record(request):
    """
    특정 날짜의 IBS-QOL 기록 조회 API
    """
    try:
        record_date = request.GET.get('date')  # YYYY-MM-DD 형식
        
        if not record_date:
            return Response(
                {'error': '조회할 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 날짜의 IBS-QOL 기록 조회
        ibsqol_record = IBSQOLRecord.objects.filter(
            user=request.user,
            record_date=record_date
        ).first()
        
        if not ibsqol_record:
            return Response(
                {
                    'message': '해당 날짜의 IBS-QOL 기록이 없습니다.',
                    'ibsqol_record': None
                }, 
                status=status.HTTP_200_OK
            )
        
        return Response({
            'message': 'IBS-QOL 기록을 성공적으로 조회했습니다.',
            'ibsqol_record': {
                'id': ibsqol_record.id,
                'question_1': ibsqol_record.question_1,
                'question_2': ibsqol_record.question_2,
                'question_3': ibsqol_record.question_3,
                'question_4': ibsqol_record.question_4,
                'question_5': ibsqol_record.question_5,
                'question_6': ibsqol_record.question_6,
                'question_7': ibsqol_record.question_7,
                'question_8': ibsqol_record.question_8,
                'question_9': ibsqol_record.question_9,
                'question_10': ibsqol_record.question_10,
                'question_11': ibsqol_record.question_11,
                'question_12': ibsqol_record.question_12,
                'question_13': ibsqol_record.question_13,
                'question_14': ibsqol_record.question_14,
                'question_15': ibsqol_record.question_15,
                'question_16': ibsqol_record.question_16,
                'question_17': ibsqol_record.question_17,
                'question_18': ibsqol_record.question_18,
                'question_19': ibsqol_record.question_19,
                'question_20': ibsqol_record.question_20,
                'question_21': ibsqol_record.question_21,
                'question_22': ibsqol_record.question_22,
                'question_23': ibsqol_record.question_23,
                'question_24': ibsqol_record.question_24,
                'question_25': ibsqol_record.question_25,
                'question_26': ibsqol_record.question_26,
                'question_27': ibsqol_record.question_27,
                'question_28': ibsqol_record.question_28,
                'question_29': ibsqol_record.question_29,
                'question_30': ibsqol_record.question_30,
                'question_31': ibsqol_record.question_31,
                'question_32': ibsqol_record.question_32,
                'question_33': ibsqol_record.question_33,
                'question_34': ibsqol_record.question_34,
                'total_score': ibsqol_record.total_score,
                'quality_level': ibsqol_record.quality_level,
                'record_date': str(ibsqol_record.record_date),
                'created_at': ibsqol_record.created_at.isoformat(),
                'updated_at': ibsqol_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'IBS-QOL 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ibsqol_records(request):
    """
    기간별 IBS-QOL 기록 조회 API
    """
    try:
        start_date = request.GET.get('start_date')  # YYYY-MM-DD 형식
        end_date = request.GET.get('end_date')  # YYYY-MM-DD 형식
        
        if not start_date or not end_date:
            return Response(
                {'error': '시작 날짜와 종료 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 기간의 IBS-QOL 기록 조회
        ibsqol_records = IBSQOLRecord.objects.filter(
            user=request.user,
            record_date__range=[start_date, end_date]
        ).order_by('record_date')
        
        records = []
        for record in ibsqol_records:
            records.append({
                'id': record.id,
                'question_1': record.question_1,
                'question_2': record.question_2,
                'question_3': record.question_3,
                'question_4': record.question_4,
                'question_5': record.question_5,
                'question_6': record.question_6,
                'question_7': record.question_7,
                'question_8': record.question_8,
                'question_9': record.question_9,
                'question_10': record.question_10,
                'question_11': record.question_11,
                'question_12': record.question_12,
                'question_13': record.question_13,
                'question_14': record.question_14,
                'question_15': record.question_15,
                'question_16': record.question_16,
                'question_17': record.question_17,
                'question_18': record.question_18,
                'question_19': record.question_19,
                'question_20': record.question_20,
                'question_21': record.question_21,
                'question_22': record.question_22,
                'question_23': record.question_23,
                'question_24': record.question_24,
                'question_25': record.question_25,
                'question_26': record.question_26,
                'question_27': record.question_27,
                'question_28': record.question_28,
                'question_29': record.question_29,
                'question_30': record.question_30,
                'question_31': record.question_31,
                'question_32': record.question_32,
                'question_33': record.question_33,
                'question_34': record.question_34,
                'total_score': record.total_score,
                'quality_level': record.quality_level,
                'record_date': str(record.record_date),
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat(),
            })
        
        return Response({
            'message': 'IBS-QOL 기록을 성공적으로 조회했습니다.',
            'ibsqol_records': records
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'IBS-QOL 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pss_stress_record(request):
    """
    특정 날짜의 PSS 스트레스 기록 조회 API
    """
    try:
        record_date = request.GET.get('date')  # YYYY-MM-DD 형식
        
        if not record_date:
            return Response(
                {'error': '조회할 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 날짜의 PSS 스트레스 기록 조회
        pss_stress_record = PSSStressRecord.objects.filter(
            user=request.user,
            record_date=record_date
        ).first()
        
        if not pss_stress_record:
            return Response(
                {
                    'message': '해당 날짜의 PSS 스트레스 기록이 없습니다.',
                    'pss_stress_record': None
                }, 
                status=status.HTTP_200_OK
            )
        
        return Response({
            'message': 'PSS 스트레스 기록을 성공적으로 조회했습니다.',
            'pss_stress_record': {
                'id': pss_stress_record.id,
                'question_1': pss_stress_record.question_1,
                'question_2': pss_stress_record.question_2,
                'question_3': pss_stress_record.question_3,
                'question_4': pss_stress_record.question_4,
                'question_5': pss_stress_record.question_5,
                'question_6': pss_stress_record.question_6,
                'question_7': pss_stress_record.question_7,
                'question_8': pss_stress_record.question_8,
                'question_9': pss_stress_record.question_9,
                'question_10': pss_stress_record.question_10,
                'total_score': pss_stress_record.total_score,
                'stress_level': pss_stress_record.stress_level,
                'record_date': str(pss_stress_record.record_date),
                'created_at': pss_stress_record.created_at.isoformat(),
                'updated_at': pss_stress_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'PSS 스트레스 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ibssss_pain_records(request):
    """
    IBS-SSS 통증 기록 조회 API
    """
    try:
        start_date = request.GET.get('start_date')  # YYYY-MM-DD 형식
        end_date = request.GET.get('end_date')  # YYYY-MM-DD 형식
        
        if not start_date or not end_date:
            return Response(
                {'error': '시작 날짜와 종료 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 기간의 통증 기록 조회
        pain_records = IBSSSSPainRecord.objects.filter(
            user=request.user,
            record_date__range=[start_date, end_date]
        ).order_by('record_date')
        
        records = []
        for record in pain_records:
            records.append({
                'date': str(record.record_date),
                'has_pain': record.has_pain,
            })
        
        return Response({
            'message': '통증 기록을 성공적으로 조회했습니다.',
            'pain_records': records
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'통증 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_water_record(request):
    """
    물 섭취량 기록 저장 API
    """
    try:
        water_intake = request.data.get('water_intake')
        cup_count = request.data.get('cup_count')
        record_date = request.data.get('record_date')
        
        if not water_intake or not cup_count or not record_date:
            return Response(
                {'error': '물 섭취량, 컵 수, 기록 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 기존 기록이 있으면 업데이트, 없으면 새로 생성
        water_record, created = UserWaterRecord.objects.update_or_create(
            user=request.user,
            record_date=record_date,
            defaults={
                'water_intake': water_intake,
                'cup_count': cup_count,
            }
        )
        
        action = '생성' if created else '업데이트'
        
        return Response({
            'message': f'물 섭취량 기록이 성공적으로 {action}되었습니다.',
            'water_record': {
                'id': water_record.id,
                'water_intake': float(water_record.water_intake),
                'cup_count': water_record.cup_count,
                'record_date': str(water_record.record_date),
                'water_intake_liters': water_record.water_intake_liters,
                'formatted_water_intake': water_record.formatted_water_intake,
                'created_at': water_record.created_at.isoformat(),
                'updated_at': water_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'물 섭취량 기록 저장 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_water_record(request):
    """
    특정 날짜의 물 섭취량 기록 조회 API
    """
    try:
        record_date = request.GET.get('date')  # YYYY-MM-DD 형식
        
        if not record_date:
            return Response(
                {'error': '조회할 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 날짜의 물 섭취량 기록 조회
        water_record = UserWaterRecord.objects.filter(
            user=request.user,
            record_date=record_date
        ).first()
        
        if not water_record:
            return Response(
                {
                    'message': '해당 날짜의 물 섭취량 기록이 없습니다.',
                    'water_record': None
                }, 
                status=status.HTTP_200_OK
            )
        
        return Response({
            'message': '물 섭취량 기록을 성공적으로 조회했습니다.',
            'water_record': {
                'id': water_record.id,
                'water_intake': float(water_record.water_intake),
                'cup_count': water_record.cup_count,
                'record_date': str(water_record.record_date),
                'water_intake_liters': water_record.water_intake_liters,
                'formatted_water_intake': water_record.formatted_water_intake,
                'created_at': water_record.created_at.isoformat(),
                'updated_at': water_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'물 섭취량 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_water_records(request):
    """
    기간별 물 섭취량 기록 조회 API
    """
    try:
        start_date = request.GET.get('start_date')  # YYYY-MM-DD 형식
        end_date = request.GET.get('end_date')  # YYYY-MM-DD 형식
        
        if not start_date or not end_date:
            return Response(
                {'error': '시작 날짜와 종료 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 기간의 물 섭취량 기록 조회
        water_records = UserWaterRecord.objects.filter(
            user=request.user,
            record_date__range=[start_date, end_date]
        ).order_by('record_date')
        
        records = []
        for record in water_records:
            records.append({
                'id': record.id,
                'water_intake': float(record.water_intake),
                'cup_count': record.cup_count,
                'record_date': str(record.record_date),
                'water_intake_liters': record.water_intake_liters,
                'formatted_water_intake': record.formatted_water_intake,
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat(),
            })
        
        return Response({
            'message': '물 섭취량 기록을 성공적으로 조회했습니다.',
            'water_records': records
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'물 섭취량 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_exercise_record(request):
    """
    운동 기록 저장 API
    """
    try:
        target_steps = request.data.get('target_steps')
        current_steps = request.data.get('current_steps')
        record_date = request.data.get('record_date')
        
        if not current_steps or not record_date:
            return Response(
                {'error': '현재 걸음 수와 기록 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 목표 걸음 수가 없으면 사용자 프로필에서 가져오기
        if not target_steps:
            target_steps = request.user.profile.step_count or 0
        
        # 기존 기록이 있으면 업데이트, 없으면 새로 생성
        exercise_record, created = UserExerciseRecord.objects.update_or_create(
            user=request.user,
            record_date=record_date,
            defaults={
                'target_steps': target_steps,
                'current_steps': current_steps,
            }
        )
        
        action = '생성' if created else '업데이트'
        
        return Response({
            'message': f'운동 기록이 성공적으로 {action}되었습니다.',
            'exercise_record': {
                'id': exercise_record.id,
                'target_steps': exercise_record.target_steps,
                'current_steps': exercise_record.current_steps,
                'progress_percentage': exercise_record.progress_percentage,
                'is_goal_achieved': exercise_record.is_goal_achieved,
                'formatted_progress': exercise_record.formatted_progress,
                'record_date': str(exercise_record.record_date),
                'created_at': exercise_record.created_at.isoformat(),
                'updated_at': exercise_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'운동 기록 저장 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_exercise_record(request):
    """
    특정 날짜의 운동 기록 조회 API
    """
    try:
        record_date = request.GET.get('date')  # YYYY-MM-DD 형식
        
        if not record_date:
            return Response(
                {'error': '조회할 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 날짜의 운동 기록 조회
        exercise_record = UserExerciseRecord.objects.filter(
            user=request.user,
            record_date=record_date
        ).first()
        
        if not exercise_record:
            return Response(
                {
                    'message': '해당 날짜의 운동 기록이 없습니다.',
                    'exercise_record': None
                }, 
                status=status.HTTP_200_OK
            )
        
        return Response({
            'message': '운동 기록을 성공적으로 조회했습니다.',
            'exercise_record': {
                'id': exercise_record.id,
                'target_steps': exercise_record.target_steps,
                'current_steps': exercise_record.current_steps,
                'progress_percentage': exercise_record.progress_percentage,
                'is_goal_achieved': exercise_record.is_goal_achieved,
                'formatted_progress': exercise_record.formatted_progress,
                'record_date': str(exercise_record.record_date),
                'created_at': exercise_record.created_at.isoformat(),
                'updated_at': exercise_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'운동 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_exercise_records(request):
    """
    기간별 운동 기록 조회 API
    """
    try:
        start_date = request.GET.get('start_date')  # YYYY-MM-DD 형식
        end_date = request.GET.get('end_date')  # YYYY-MM-DD 형식
        
        if not start_date or not end_date:
            return Response(
                {'error': '시작 날짜와 종료 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 기간의 운동 기록 조회
        exercise_records = UserExerciseRecord.objects.filter(
            user=request.user,
            record_date__range=[start_date, end_date]
        ).order_by('record_date')
        
        records = []
        for record in exercise_records:
            records.append({
                'id': record.id,
                'target_steps': record.target_steps,
                'current_steps': record.current_steps,
                'progress_percentage': record.progress_percentage,
                'is_goal_achieved': record.is_goal_achieved,
                'formatted_progress': record.formatted_progress,
                'record_date': str(record.record_date),
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat(),
            })
        
        return Response({
            'message': '운동 기록을 성공적으로 조회했습니다.',
            'exercise_records': records
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'운동 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ibssss_records(request):
    """
    기간별 IBS-SSS 기록 조회 API
    """
    try:
        start_date = request.GET.get('start_date')  # YYYY-MM-DD 형식
        end_date = request.GET.get('end_date')  # YYYY-MM-DD 형식
        
        if not start_date or not end_date:
            return Response(
                {'error': '시작 날짜와 종료 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 기간의 IBS-SSS 기록 조회
        ibssss_records = IBSSSSRecord.objects.filter(
            user=request.user,
            record_date__range=[start_date, end_date]
        ).order_by('record_date')
        
        records = []
        for record in ibssss_records:
            records.append({
                'id': record.id,
                'question_1': record.question_1,
                'question_2': record.question_2,
                'question_3': record.question_3,
                'question_4': record.question_4,
                'question_5': record.question_5,
                'question_6': record.question_6,
                'question_7': record.question_7,
                'total_score': record.total_score,
                'severity': record.severity,
                'record_date': str(record.record_date),
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat(),
            })
        
        return Response({
            'message': 'IBS-SSS 기록을 성공적으로 조회했습니다.',
            'ibssss_records': records
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'IBS-SSS 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pss_stress_records(request):
    """
    기간별 PSS 스트레스 기록 조회 API
    """
    try:
        start_date = request.GET.get('start_date')  # YYYY-MM-DD 형식
        end_date = request.GET.get('end_date')  # YYYY-MM-DD 형식
        
        if not start_date or not end_date:
            return Response(
                {'error': '시작 날짜와 종료 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 기간의 PSS 스트레스 기록 조회
        pss_stress_records = PSSStressRecord.objects.filter(
            user=request.user,
            record_date__range=[start_date, end_date]
        ).order_by('record_date')
        
        records = []
        for record in pss_stress_records:
            records.append({
                'id': record.id,
                'question_1': record.question_1,
                'question_2': record.question_2,
                'question_3': record.question_3,
                'question_4': record.question_4,
                'question_5': record.question_5,
                'question_6': record.question_6,
                'question_7': record.question_7,
                'question_8': record.question_8,
                'question_9': record.question_9,
                'question_10': record.question_10,
                'total_score': record.total_score,
                'stress_level': record.stress_level,
                'record_date': str(record.record_date),
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat(),
            })
        
        return Response({
            'message': 'PSS 스트레스 기록을 성공적으로 조회했습니다.',
            'pss_stress_records': records
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'PSS 스트레스 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_intervention(request):
    """
    AI 중재 권고사항 생성 API
    """
    try:
        selected_date = request.GET.get('selected_date')  # YYYY-MM-DD 형식
        
        if not selected_date:
            return Response(
                {'error': '선택된 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        profile = user.profile
        
        # 선택된 날짜의 수면 기록 가져오기
        sleep_record = UserSleepRecord.objects.filter(
            user=user,
            record_date=selected_date
        ).first()
        
        # 선택된 날짜의 음식 기록 가져오기 (today_diet용)
        today_food_records = UserFoodRecord.objects.filter(
            user=user,
            record_date=selected_date
        ).select_related('food').order_by('meal_type')
        
        # 선택된 날짜 기준으로 최근 3일간의 음식 기록 가져오기
        from datetime import datetime, timedelta
        selected_datetime = datetime.strptime(selected_date, '%Y-%m-%d')
        three_days_start = selected_datetime - timedelta(days=2)  # 최근 3일
        three_days_end = selected_datetime
        
        food_records = UserFoodRecord.objects.filter(
            user=user,
            record_date__range=[three_days_start.date(), three_days_end.date()]
        ).select_related('food').order_by('record_date', 'meal_type')
        
        # 선택된 날짜 기준으로 일주일간의 운동 기록 가져오기
        week_start = selected_datetime - timedelta(days=6)  # 최근 7일
        week_end = selected_datetime
        
        exercise_records = UserExerciseRecord.objects.filter(
            user=user,
            record_date__range=[week_start.date(), week_end.date()]
        ).order_by('record_date')
        
        # 사용자 프로필 정보 (중재 요청에 필요한 부분만)
        user_profile_data = {
            'has_gluten_allergy': profile.has_gluten_allergy,
            'has_lactose_allergy': profile.has_lactose_allergy,
            'has_nut_allergy': profile.has_nut_allergy,
            'has_seafood_allergy': profile.has_seafood_allergy,
            'has_egg_allergy': profile.has_egg_allergy,
            'has_soy_allergy': profile.has_soy_allergy,
            'has_lactose_intolerance': profile.has_lactose_intolerance,
        }
        
        # 수면 데이터 (중재 요청에 필요한 부분만)
        sleep_data = None
        if sleep_record:
            sleep_data = {
                'sleep_hours': sleep_record.sleep_hours,
            }
        
        # 오늘 음식 데이터 (today_diet용) - 음식 이름 리스트
        today_diet = []
        for record in today_food_records:
            food_name = record.food.food_name
            if food_name not in today_diet:  # 중복 제거
                today_diet.append(food_name)
        
        # 음식 데이터 (최근 3일간, 중재 요청에 필요한 부분만)
        food_data = []
        for record in food_records:
            food_data.append({
                'food_name': record.food.food_name,
            })
        
        # 운동 데이터 (일주일간, 중재 요청에 필요한 부분만)
        exercise_data = []
        for record in exercise_records:
            exercise_data.append({
                'current_steps': record.current_steps,
            })
        
        # 직접 중재 서비스 호출
        try:
            # LLM_OSS 모듈 경로 추가
            llm_oss_path = os.path.join(os.path.dirname(__file__), 'llm_oss')
            if llm_oss_path not in sys.path:
                sys.path.append(llm_oss_path)
            
            # make_prompt_korean 모듈은 _run_intervention_inference 함수 내부에서 import됩니다
            
            start_time = time.time()
            
            # Ollama API 직접 호출을 위한 설정
            ollama_base_url = "http://127.0.0.1:11434"
            ollama_model = "gpt-oss:20b"
            
            # 음식 DB 로드
            food_db_path = os.path.join(llm_oss_path, "Food_list.xlsx")
            if not os.path.exists(food_db_path):
                raise Exception(f"음식 DB 파일을 찾을 수 없습니다: {food_db_path}")
            
            df = pd.read_excel(food_db_path)
            df.columns = [str(c).strip().lower() for c in df.columns]
            required = {"food", "fodmap", "fiber"}
            if not required.issubset(set(df.columns)):
                raise Exception(f"CSV에 필수 컬럼이 없습니다: {required} / 현재: {set(df.columns)}")
            
            table_food = df.to_csv(index=False)
            
            # 중재 추론 실행
            print("=== 중재 서비스 입력 파라미터 ===")
            print(f"ollama_base_url: {ollama_base_url}")
            print(f"ollama_model: {ollama_model}")
            print(f"allergies: {_format_allergies_list(user_profile_data)}")
            print(f"restrictions: {[]}")
            print(f"recent_3days: {_get_recent_food_names(food_data)}")
            print(f"use_rag: {True}")
            print(f"today_sleep: {sleep_data['sleep_hours'] if sleep_data else 7.0}")
            print(f"week_step: {_get_week_step_counts(exercise_data)}")
            print(f"today_diet: {today_diet}")
            print(f"table_food 길이: {len(table_food)} 문자")
            print("=== 중재 서비스 입력 파라미터 끝 ===")
            
            results = _run_intervention_inference(
                ollama_base_url=ollama_base_url,
                ollama_model=ollama_model,
                allergies=_format_allergies_list(user_profile_data),
                restrictions=[],
                recent_3days=_get_recent_food_names(food_data),
                use_rag=True,
                today_sleep=sleep_data['sleep_hours'] if sleep_data else 7.0,
                week_step=_get_week_step_counts(exercise_data),
                today_diet=today_diet,
                table_food=table_food
            )
            
            processing_time = time.time() - start_time
            
            # 결과 JSON 로그 출력
            print("=== 중재 서비스 결과 JSON ===")
            print(f"선택된 날짜: {selected_date}")
            print(f"처리 시간: {processing_time:.2f}초")
            print("최종 결과 데이터:")
            import json
            print(json.dumps(results, ensure_ascii=False, indent=2))
            print("=== 중재 서비스 결과 JSON 끝 ===")
            
            # 중재 결과를 데이터베이스에 저장
            try:
                from datetime import datetime, timedelta
                record_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
                target_date = record_date + timedelta(days=1)  # 하루 뒤 날짜
                
                # 기존 기록이 있으면 업데이트, 없으면 새로 생성
                intervention_record, created = InterventionRecord.objects.update_or_create(
                    user=user,
                    record_date=record_date,
                    defaults={
                        'target_date': target_date,
                        'diet_evaluation': results.get('diet', {}).get('Evaluation', ''),
                        'diet_target': results.get('diet', {}).get('Target', {}),
                        'sleep_evaluation': results.get('sleep', {}).get('Evaluation', ''),
                        'sleep_target': results.get('sleep', {}).get('Target', 0.0),
                        'exercise_evaluation': results.get('exercise', {}).get('Evaluation', ''),
                        'exercise_target': results.get('exercise', {}).get('Target', 0),
                        'processing_time': processing_time,
                        'error_message': None,  # 성공 시 오류 메시지는 None
                    }
                )
                
                action = '생성' if created else '업데이트'
                print(f"중재 결과 {action} 완료: {intervention_record}")
                
            except Exception as e:
                print(f"중재 결과 저장 중 오류: {e}")
            
            return Response({
                'message': 'Ollama gpt-oss-20b를 통한 중재 권고사항을 성공적으로 생성했습니다.',
                'results': results,
                'processing_time': processing_time,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            error_message = f"중재 서비스 오류: {str(e)}"
            print(error_message)
            
            # 오류 발생 시 오류 정보를 데이터베이스에 저장
            try:
                from datetime import datetime, timedelta
                record_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
                target_date = record_date + timedelta(days=1)  # 하루 뒤 날짜
                
                intervention_record, created = InterventionRecord.objects.update_or_create(
                    user=user,
                    record_date=record_date,
                    defaults={
                        'target_date': target_date,
                        'diet_evaluation': '',
                        'diet_target': {},
                        'sleep_evaluation': '',
                        'sleep_target': sleep_data['sleep_hours'] if sleep_data else 0.0,
                        'exercise_evaluation': '',
                        'exercise_target': 0,
                        'processing_time': 0.0,
                        'error_message': error_message,
                    }
                )
                
                action = '생성' if created else '업데이트'
                print(f"오류 중재 결과 {action} 완료: {intervention_record}")
                
            except Exception as db_error:
                print(f"오류 중재 결과 저장 중 오류: {db_error}")
            
            return Response({
                'error': error_message,
                'message': '중재 서비스에서 오류가 발생했습니다.',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        return Response(
            {'error': f'중재 권고사항 생성 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_intervention_record(request):
    """
    특정 날짜의 중재 기록 조회 API
    """
    try:
        record_date = request.GET.get('date')  # YYYY-MM-DD 형식
        
        if not record_date:
            return Response(
                {'error': '조회할 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 날짜의 중재 기록 조회
        intervention_record = InterventionRecord.objects.filter(
            user=request.user,
            record_date=record_date
        ).first()
        
        if not intervention_record:
            return Response(
                {
                    'message': '해당 날짜의 중재 기록이 없습니다.',
                    'intervention_record': None
                }, 
                status=status.HTTP_200_OK
            )
        
        return Response({
            'message': '중재 기록을 성공적으로 조회했습니다.',
            'intervention_record': {
                'id': intervention_record.id,
                'record_date': str(intervention_record.record_date),
                'target_date': str(intervention_record.target_date),
                'diet_evaluation': intervention_record.diet_evaluation,
                'diet_target': intervention_record.diet_target,
                'sleep_evaluation': intervention_record.sleep_evaluation,
                'sleep_target': intervention_record.sleep_target,
                'exercise_evaluation': intervention_record.exercise_evaluation,
                'exercise_target': intervention_record.exercise_target,
                'processing_time': intervention_record.processing_time,
                'error_message': intervention_record.error_message,
                'created_at': intervention_record.created_at.isoformat(),
                'updated_at': intervention_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'중재 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_latest_intervention_record(request):
    """
    사용자의 최근 중재 기록 조회 API
    """
    try:
        # 사용자의 가장 최근 중재 기록 조회
        latest_intervention_record = InterventionRecord.objects.filter(
            user=request.user
        ).order_by('-record_date').first()
        
        if not latest_intervention_record:
            return Response(
                {
                    'message': '중재 기록이 없습니다.',
                    'intervention_record': None
                }, 
                status=status.HTTP_200_OK
            )
        
        return Response({
            'message': '최근 중재 기록을 성공적으로 조회했습니다.',
            'intervention_record': {
                'id': latest_intervention_record.id,
                'record_date': str(latest_intervention_record.record_date),
                'target_date': str(latest_intervention_record.target_date),
                'diet_evaluation': latest_intervention_record.diet_evaluation,
                'diet_target': latest_intervention_record.diet_target,
                'sleep_evaluation': latest_intervention_record.sleep_evaluation,
                'sleep_target': latest_intervention_record.sleep_target,
                'exercise_evaluation': latest_intervention_record.exercise_evaluation,
                'exercise_target': latest_intervention_record.exercise_target,
                'processing_time': latest_intervention_record.processing_time,
                'error_message': latest_intervention_record.error_message,
                'created_at': latest_intervention_record.created_at.isoformat(),
                'updated_at': latest_intervention_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'최근 중재 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def batch_schedule_management(request):
    """
    배치 스케줄 관리 API
    """
    try:
        if request.method == 'GET':
            # 모든 배치 스케줄 조회
            schedules = BatchSchedule.objects.all().order_by('-created_at')
            
            schedules_data = []
            for schedule in schedules:
                schedules_data.append({
                    'id': schedule.id,
                    'name': schedule.name,
                    'frequency': schedule.frequency,
                    'frequency_display': schedule.get_frequency_display(),
                    'hour': schedule.hour,
                    'minute': schedule.minute,
                    'is_active': schedule.is_active,
                    'cron_expression': schedule.cron_expression,
                    'created_at': schedule.created_at.isoformat(),
                    'updated_at': schedule.updated_at.isoformat(),
                })
            
            # 스케줄 상태 정보 추가
            from .utils import get_schedule_status
            status = get_schedule_status()
            
            return Response({
                'schedules': schedules_data,
                'count': len(schedules_data),
                'status': status
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'POST':
            # 새 배치 스케줄 생성
            data = request.data
            
            required_fields = ['name', 'frequency', 'hour', 'minute']
            for field in required_fields:
                if field not in data:
                    return Response(
                        {'error': f'필수 필드가 누락되었습니다: {field}'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # 시간 유효성 검사
            if not (0 <= data['hour'] <= 23):
                return Response(
                    {'error': '시간은 0-23 사이의 값이어야 합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not (0 <= data['minute'] <= 59):
                return Response(
                    {'error': '분은 0-59 사이의 값이어야 합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            schedule = BatchSchedule.objects.create(
                name=data['name'],
                frequency=data['frequency'],
                hour=data['hour'],
                minute=data['minute'],
                is_active=data.get('is_active', True)
            )
            
            # 스케줄 동기화
            from .utils import sync_batch_schedules
            sync_success = sync_batch_schedules()
            
            return Response({
                'message': '배치 스케줄이 성공적으로 생성되었습니다.',
                'schedule': {
                    'id': schedule.id,
                    'name': schedule.name,
                    'frequency': schedule.frequency,
                    'frequency_display': schedule.get_frequency_display(),
                    'hour': schedule.hour,
                    'minute': schedule.minute,
                    'is_active': schedule.is_active,
                    'cron_expression': schedule.cron_expression,
                    'created_at': schedule.created_at.isoformat(),
                    'updated_at': schedule.updated_at.isoformat(),
                },
                'sync_success': sync_success
            }, status=status.HTTP_201_CREATED)
        
        elif request.method == 'PUT':
            # 배치 스케줄 업데이트
            schedule_id = request.data.get('id')
            if not schedule_id:
                return Response(
                    {'error': '스케줄 ID가 필요합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                schedule = BatchSchedule.objects.get(id=schedule_id)
            except BatchSchedule.DoesNotExist:
                return Response(
                    {'error': '해당 스케줄을 찾을 수 없습니다.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            data = request.data
            
            # 업데이트할 필드들
            if 'name' in data:
                schedule.name = data['name']
            if 'frequency' in data:
                schedule.frequency = data['frequency']
            if 'hour' in data:
                if not (0 <= data['hour'] <= 23):
                    return Response(
                        {'error': '시간은 0-23 사이의 값이어야 합니다.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                schedule.hour = data['hour']
            if 'minute' in data:
                if not (0 <= data['minute'] <= 59):
                    return Response(
                        {'error': '분은 0-59 사이의 값이어야 합니다.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                schedule.minute = data['minute']
            if 'is_active' in data:
                schedule.is_active = data['is_active']
            
            schedule.save()
            
            # 스케줄 동기화
            from .utils import sync_batch_schedules
            sync_success = sync_batch_schedules()
            
            return Response({
                'message': '배치 스케줄이 성공적으로 업데이트되었습니다.',
                'schedule': {
                    'id': schedule.id,
                    'name': schedule.name,
                    'frequency': schedule.frequency,
                    'frequency_display': schedule.get_frequency_display(),
                    'hour': schedule.hour,
                    'minute': schedule.minute,
                    'is_active': schedule.is_active,
                    'cron_expression': schedule.cron_expression,
                    'created_at': schedule.created_at.isoformat(),
                    'updated_at': schedule.updated_at.isoformat(),
                },
                'sync_success': sync_success
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'DELETE':
            # 배치 스케줄 삭제
            schedule_id = request.data.get('id')
            if not schedule_id:
                return Response(
                    {'error': '스케줄 ID가 필요합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                schedule = BatchSchedule.objects.get(id=schedule_id)
                schedule.delete()
                
                # 스케줄 동기화
                from .utils import sync_batch_schedules
                sync_success = sync_batch_schedules()
                
                return Response({
                    'message': '배치 스케줄이 성공적으로 삭제되었습니다.',
                    'sync_success': sync_success
                }, status=status.HTTP_200_OK)
            except BatchSchedule.DoesNotExist:
                return Response(
                    {'error': '해당 스케줄을 찾을 수 없습니다.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
    except Exception as e:
        return Response(
            {'error': f'배치 스케줄 관리 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_batch_schedules_api(request):
    """
    배치 스케줄 동기화 API
    """
    try:
        from .utils import sync_batch_schedules, get_schedule_status
        
        sync_success = sync_batch_schedules()
        status = get_schedule_status()
        
        return Response({
            'message': '배치 스케줄 동기화가 완료되었습니다.' if sync_success else '배치 스케줄 동기화 중 오류가 발생했습니다.',
            'sync_success': sync_success,
            'status': status
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'배치 스케줄 동기화 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_manual_batch(request):
    """
    수동으로 배치 작업을 실행하는 API
    """
    try:
        from .tasks import run_intervention_batch
        
        # 비동기로 배치 작업 실행
        task = run_intervention_batch.delay()
        
        return Response({
            'message': '배치 작업이 시작되었습니다.',
            'task_id': task.id,
            'status': 'PENDING'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'배치 작업 실행 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_batch_task_status(request):
    """
    배치 작업 상태 조회 API
    """
    try:
        task_id = request.GET.get('task_id')
        if not task_id:
            return Response(
                {'error': '작업 ID가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from celery.result import AsyncResult
        from backend.celery import app
        
        task_result = AsyncResult(task_id, app=app)
        
        return Response({
            'task_id': task_id,
            'status': task_result.status,
            'result': task_result.result if task_result.ready() else None,
            'ready': task_result.ready(),
            'successful': task_result.successful(),
            'failed': task_result.failed(),
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'작업 상태 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_active_notification_schedules(request):
    """
    활성화된 알림 스케줄 조회 API
    """
    try:
        # 활성화된 알림 스케줄만 조회
        schedules = NotificationSchedule.objects.filter(is_active=True).order_by('created_at')
        
        schedules_data = []
        for schedule in schedules:
            schedules_data.append({
                'id': schedule.id,
                'name': schedule.name,
                'description': schedule.description,
                'cron_expression': schedule.cron_expression,
                'title': schedule.title,
                'body': schedule.body,
                'is_active': schedule.is_active,
                'created_at': schedule.created_at.isoformat(),
                'updated_at': schedule.updated_at.isoformat(),
            })
        
        return Response({
            'schedules': schedules_data,
            'count': len(schedules_data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'알림 스케줄 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def notification_schedule_management(request):
    """
    알림 스케줄 관리 API (관리자용)
    """
    try:
        if request.method == 'GET':
            # 모든 알림 스케줄 조회
            schedules = NotificationSchedule.objects.all().order_by('-created_at')
            
            schedules_data = []
            for schedule in schedules:
                schedules_data.append({
                    'id': schedule.id,
                    'name': schedule.name,
                    'description': schedule.description,
                    'cron_expression': schedule.cron_expression,
                    'title': schedule.title,
                    'body': schedule.body,
                    'is_active': schedule.is_active,
                    'created_at': schedule.created_at.isoformat(),
                    'updated_at': schedule.updated_at.isoformat(),
                })
            
            return Response({
                'schedules': schedules_data,
                'count': len(schedules_data)
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'POST':
            # 새 알림 스케줄 생성
            data = request.data
            
            required_fields = ['name', 'cron_expression', 'title', 'body']
            for field in required_fields:
                if field not in data:
                    return Response(
                        {'error': f'필수 필드가 누락되었습니다: {field}'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            schedule = NotificationSchedule.objects.create(
                name=data['name'],
                description=data.get('description', ''),
                cron_expression=data['cron_expression'],
                title=data['title'],
                body=data['body'],
                is_active=data.get('is_active', True)
            )
            
            return Response({
                'message': '알림 스케줄이 성공적으로 생성되었습니다.',
                'schedule': {
                    'id': schedule.id,
                    'name': schedule.name,
                    'description': schedule.description,
                    'cron_expression': schedule.cron_expression,
                    'title': schedule.title,
                    'body': schedule.body,
                    'is_active': schedule.is_active,
                    'created_at': schedule.created_at.isoformat(),
                    'updated_at': schedule.updated_at.isoformat(),
                }
            }, status=status.HTTP_201_CREATED)
        
        elif request.method == 'PUT':
            # 알림 스케줄 업데이트
            schedule_id = request.data.get('id')
            if not schedule_id:
                return Response(
                    {'error': '스케줄 ID가 필요합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                schedule = NotificationSchedule.objects.get(id=schedule_id)
            except NotificationSchedule.DoesNotExist:
                return Response(
                    {'error': '해당 스케줄을 찾을 수 없습니다.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            data = request.data
            
            # 업데이트할 필드들
            if 'name' in data:
                schedule.name = data['name']
            if 'description' in data:
                schedule.description = data['description']
            if 'cron_expression' in data:
                schedule.cron_expression = data['cron_expression']
            if 'title' in data:
                schedule.title = data['title']
            if 'body' in data:
                schedule.body = data['body']
            if 'is_active' in data:
                schedule.is_active = data['is_active']
            
            schedule.save()
            
            return Response({
                'message': '알림 스케줄이 성공적으로 업데이트되었습니다.',
                'schedule': {
                    'id': schedule.id,
                    'name': schedule.name,
                    'description': schedule.description,
                    'cron_expression': schedule.cron_expression,
                    'title': schedule.title,
                    'body': schedule.body,
                    'is_active': schedule.is_active,
                    'created_at': schedule.created_at.isoformat(),
                    'updated_at': schedule.updated_at.isoformat(),
                }
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'DELETE':
            # 알림 스케줄 삭제
            schedule_id = request.data.get('id')
            if not schedule_id:
                return Response(
                    {'error': '스케줄 ID가 필요합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                schedule = NotificationSchedule.objects.get(id=schedule_id)
                schedule.delete()
                
                return Response({
                    'message': '알림 스케줄이 성공적으로 삭제되었습니다.'
                }, status=status.HTTP_200_OK)
            except NotificationSchedule.DoesNotExist:
                return Response(
                    {'error': '해당 스케줄을 찾을 수 없습니다.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
    except Exception as e:
        return Response(
            {'error': f'알림 스케줄 관리 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




def _format_allergies_list(user_profile_data):
    """알레르기 정보를 리스트로 포맷팅"""
    allergies = []
    if user_profile_data.get('has_gluten_allergy'):
        allergies.append('글루텐')
    if user_profile_data.get('has_lactose_allergy'):
        allergies.append('우유')
    if user_profile_data.get('has_nut_allergy'):
        allergies.append('견과류')
    if user_profile_data.get('has_seafood_allergy'):
        allergies.append('해산물')
    if user_profile_data.get('has_egg_allergy'):
        allergies.append('계란')
    if user_profile_data.get('has_soy_allergy'):
        allergies.append('대두')
    return allergies

def _get_recent_food_names(food_data):
    """최근 3일간 섭취한 음식 이름들 추출"""
    if not food_data:
        return []
    
    # 최근 3일간의 음식 이름들 수집
    recent_foods = []
    for food in food_data:
        food_name = food['food_name']
        if food_name not in recent_foods:
            recent_foods.append(food_name)
    
    # 최대 10개까지만 반환
    return recent_foods[:10]

def _get_week_step_counts(exercise_data):
    """일주일간 걸음 수 데이터 추출"""
    if not exercise_data:
        return []  # 데이터가 없으면 빈 리스트 반환
    
    # 최근 7일간의 걸음 수 반환
    step_counts = []
    for exercise in exercise_data:
        step_counts.append(exercise['current_steps'])
    
    return step_counts


def get_number(number):
    m = re.search(r'"\s*([0-9]+(?:\.[0-9]+)?)\s*"', number)
    num_str = m.group(1) if m else None   # '7'
    num = float(num_str) if num_str and '.' in num_str else int(num_str) 

    return num

def _run_intervention_inference(
    ollama_base_url,
    ollama_model,
    allergies,
    restrictions,
    recent_3days,
    use_rag,
    today_sleep,
    week_step,
    today_diet,
    table_food
):
    """
    중재 추론 실행 함수 (FastAPI 서비스의 run_inference 함수와 동일)
    """
    
    # 맥북 MPS 지원 확인 및 설정
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    
    print(f"사용 중인 디바이스: {device}")

    # --- 임베딩 및 VectorDB (함수 내부에서 import)
    try:
        # llm_oss 경로 추가
        llm_oss_path = os.path.join(os.path.dirname(__file__), 'llm_oss')
        if llm_oss_path not in sys.path:
            sys.path.append(llm_oss_path)
        
        from rag_utility import get_embedder, get_faiss_and_chunks
        
        embed_model = get_embedder()
        vectorDB, chunks = get_faiss_and_chunks()
    except Exception as e:
        print(f"RAG 모듈 import 오류: {e}")
        # RAG 기능 없이 계속 진행
        embed_model = None
        vectorDB = None
        chunks = None
    
    retrieval_queries = {
        "diet": "Clinical guidelines for IBS dietary management, low FODMAP diet, and recommended meals",
        "sleep": "Guidelines on sleep quality, sleep hygiene, and sleep disorders in IBS patients",
        "exercise": "Recommendations on physical activity and walking for symptom relief in IBS",
    }

    # 카테고리별 결과 저장
    contexts = {}
    outputs = {}

    for category in ["diet", "sleep", "exercise"]:
        # --- 컨텍스트 검색 (영어 쿼리)
        context = ""
        if use_rag and embed_model and vectorDB and chunks:
            try:
                composed_query = f"{retrieval_queries[category]}"
                query_embedding = embed_model.encode([composed_query])
                if category == 'diet':
                    _, top_indices = vectorDB["diet"].search(np.array(query_embedding), k=2)
                    context = "\n\n".join([str(chunks["diet"][i]) for i in top_indices[0]])
                elif category == 'sleep':
                    _, top_indices = vectorDB["sleep"].search(np.array(query_embedding), k=2)
                    context = "\n\n".join([str(chunks["sleep"][i]) for i in top_indices[0]])
                elif category == 'exercise':
                    _, top_indices = vectorDB["exercise"].search(np.array(query_embedding), k=2)
                    context = "\n\n".join([str(chunks["exercise"][i]) for i in top_indices[0]])
            except Exception as e:
                print(f"RAG 검색 오류 ({category}): {e}")
                context = ""
        contexts[category] = context

        # 중재 문장 생성 (함수 내부에서 import)
        try:
            # llm_oss 경로 추가
            llm_oss_path = os.path.join(os.path.dirname(__file__), 'llm_oss')
            if llm_oss_path not in sys.path:
                sys.path.append(llm_oss_path)
                
            from make_prompt_korean import build_prompt_ko_from_csv, make_sleep_prompt_ko, make_exercise_prompt_ko, make_prompt_evalution_diet
            
            if category == "diet":
                prompt_ko = build_prompt_ko_from_csv(table_food, allergies, restrictions, recent_3days)
                response = _call_ollama_api(ollama_base_url, ollama_model, prompt_ko)
            elif category == "sleep":
                prompt_ko = make_sleep_prompt_ko(context=context, today_sleep=today_sleep)
                response = _call_ollama_api(ollama_base_url, ollama_model, prompt_ko)
            else:  # exercise
                prompt_ko = make_exercise_prompt_ko(context=context, week_step=week_step)
                response = _call_ollama_api(ollama_base_url, ollama_model, prompt_ko)
        except Exception as e:
            print(f"프롬프트 생성 오류 ({category}): {e}")
            response = f"{category} 권고사항을 생성할 수 없습니다."

        outputs[category] = response
        print(f'=== {category} 완료 ===')
        print(f'{category} 프롬프트: {prompt_ko}')
        print(f'{category} 응답: {response}')
        print(f'=== {category} 완료 끝 ===')
        
        # 메모리 정리
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            # MPS에서는 empty_cache가 없으므로 gc만 실행
            pass

    # 오늘 식단 평가 생성
    try:
        prompt_diet_evaluation = make_prompt_evalution_diet(today_diet)
        print("=== 식단 평가 프롬프트 ===")
        print(f"식단 평가 프롬프트: {prompt_diet_evaluation}")
        print("=== 식단 평가 프롬프트 끝 ===")
        
        diet_evaluation = _call_ollama_api(ollama_base_url, ollama_model, prompt_diet_evaluation)
        print("=== 식단 평가 응답 ===")
        print(f"식단 평가 원본 응답: {diet_evaluation}")
        print("=== 식단 평가 응답 끝 ===")
        
    except Exception as e:
        print(f"식단 평가 생성 오류: {e}")
        diet_evaluation = "오늘 식단을 평가할 수 없습니다."

    try:
    
        print("###1###")
        diet_evaluation = diet_evaluation.lstrip()
        print("###2###")
        diet_breakfast = outputs["diet"].split('\n')[0].split(':')[-1].lstrip()
        print("###3###")
        diet_lunch = outputs["diet"].split('\n')[1].split(':')[-1].lstrip()
        print("###4###")
        diet_dinner = outputs["diet"].split('\n')[2].split(':')[-1].lstrip()
        print("###5###")
        diet_summary = outputs["diet"].split('\n')[3].split(':')[-1].lstrip()
        print("###6###")
        sleep_evaluation = outputs["sleep"].split('\n')[0].split(":")[-1].lstrip()
        print("###7###")
        sleep_target = get_number(outputs["sleep"].split('\n')[1].split(":")[-1].lstrip())
        print("###8###")
        exercise_evaluation = outputs["exercise"].split('\n')[0].split(":")[-1].lstrip()
        print("###9###")
        exercise_target = get_number(outputs["exercise"].split('\n')[1].split(":")[-1].lstrip())    
        print("###10###")


        # 결과를 JSON 형태로 구조화 (새로운 구조에 맞게)
        results = {
            "diet": {
                "Evaluation": diet_evaluation,
                "Target": {
                    "Breakfast" : diet_breakfast,
                    "Lunch" : diet_lunch,
                    "Dinner" : diet_dinner,
                    "Summary" : diet_summary,
                }
            },
            "sleep": {
                "Evaluation": sleep_evaluation,
                "Target": sleep_target,
            },
            "exercise": {
                "Evaluation": exercise_evaluation,
                "Target": exercise_target,
            },
        }
        
        # diet 결과 파싱
        diet_output = outputs.get("diet", "")
        if diet_output:
            lines = diet_output.split('\n')
            for line in lines:
                if line.startswith('아침:'):
                    results["diet"]["Target"]["Breakfast"] = line.split(':', 1)[1].strip()
                elif line.startswith('점심:'):
                    results["diet"]["Target"]["Lunch"] = line.split(':', 1)[1].strip()
                elif line.startswith('저녁:'):
                    results["diet"]["Target"]["Dinner"] = line.split(':', 1)[1].strip()
                elif line.startswith('요약:'):
                    results["diet"]["Target"]["Summary"] = line.split(':', 1)[1].strip()

    except Exception as e:
        error_message = f"결과 파싱 오류: {str(e)}"
        print(f"결과 구조화 오류: {error_message}")
        
        # 오류 발생 시 빈 results와 outputs 반환
        empty_results = {
            "diet": {
                "Evaluation": "",
                "Target": {
                    "Breakfast": "",
                    "Lunch": "",
                    "Dinner": "",
                    "Summary": "",
                }
            },
            "sleep": {
                "Evaluation": "",
                "Target": 0.0,
            },
            "exercise": {
                "Evaluation": "",
                "Target": 0,
            },
        }
        
        return empty_results, outputs, error_message
    
    # sleep 결과 파싱
    try:
        sleep_output = outputs.get("sleep", "")
        if sleep_output:
            lines = sleep_output.split('\n')
            for line in lines:
                if line.startswith('Evaluation:'):
                    results["sleep"]["Evaluation"] = line.split(':', 1)[1].strip()
                elif line.startswith('Target:'):
                    target_text = line.split(':', 1)[1].strip()
                    # 숫자만 추출
                    import re
                    numbers = re.findall(r'\d+\.?\d*', target_text)
                    if numbers:
                        results["sleep"]["Target"] = float(numbers[0])
    except Exception as e:
        print(f"수면 결과 파싱 오류: {e}")
    
    # exercise 결과 파싱
    try:
        exercise_output = outputs.get("exercise", "")
        if exercise_output:
            lines = exercise_output.split('\n')
            for line in lines:
                if line.startswith('Evaluation:'):
                    results["exercise"]["Evaluation"] = line.split(':', 1)[1].strip()
                elif line.startswith('Target:'):
                    target_text = line.split(':', 1)[1].strip()
                    # 숫자만 추출
                    import re
                    numbers = re.findall(r'\d+', target_text)
                    if numbers:
                        results["exercise"]["Target"] = int(numbers[0])
    except Exception as e:
        print(f"운동 결과 파싱 오류: {e}")
    
    return results, outputs, ""


def _call_ollama_api(base_url, model, prompt):
    """
    Ollama API를 직접 호출하는 함수
    """
    try:
        import requests
        import json
        
        url = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        print(f"Ollama API 호출 시작: {url}")
        print(f"모델: {model}")
        print(f"프롬프트 길이: {len(prompt)} 문자")
        
        # 타임아웃을 더 길게 설정 (10분)
        response = requests.post(url, json=payload, timeout=1500)
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '응답을 생성할 수 없습니다.')
            print(f"Ollama API 응답 성공: {len(response_text)} 문자")
            return response_text
        else:
            print(f"Ollama API 오류: {response.status_code} - {response.text}")
            return f"API 호출 오류: {response.status_code}"
            
    except requests.exceptions.Timeout as e:
        print(f"Ollama API 타임아웃 오류: {e}")
        return f"API 타임아웃: 요청이 너무 오래 걸렸습니다."
    except requests.exceptions.ConnectionError as e:
        print(f"Ollama API 연결 오류: {e}")
        return f"API 연결 실패: Ollama 서버에 연결할 수 없습니다."
    except Exception as e:
        print(f"Ollama API 호출 중 오류: {e}")
        return f"API 호출 실패: {str(e)}"


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_medication_record(request):
    """
    복용약 기록 생성 API
    """
    try:
        print("=== 복용약 기록 생성 API 호출됨 ===")
        print(f"요청 데이터: {request.data}")
        print(f"요청 사용자: {request.user}")
        
        data = request.data
        medication_name = data.get('medication_name')
        has_breakfast = data.get('has_breakfast', False)
        has_lunch = data.get('has_lunch', False)
        has_dinner = data.get('has_dinner', False)
        has_as_needed = data.get('has_as_needed', False)
        taken_breakfast = data.get('taken_breakfast', False)
        taken_lunch = data.get('taken_lunch', False)
        taken_dinner = data.get('taken_dinner', False)
        taken_as_needed = data.get('taken_as_needed', False)
        record_date = data.get('record_date')
        
        print(f"약 이름: {medication_name}")
        print(f"기록 날짜: {record_date}")
        print(f"복용 스케줄: 아침={has_breakfast}, 점심={has_lunch}, 저녁={has_dinner}, 필요시={has_as_needed}")
        print(f"복용 여부: 아침={taken_breakfast}, 점심={taken_lunch}, 저녁={taken_dinner}, 필요시={taken_as_needed}")
        
        if not medication_name or not record_date:
            return Response(
                {'error': '약 이름과 기록 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 기존 기록이 있으면 업데이트, 없으면 생성
        medication_record, created = MedicationRecord.objects.update_or_create(
            user=request.user,
            medication_name=medication_name,
            record_date=record_date,
            defaults={
                'has_breakfast': has_breakfast,
                'has_lunch': has_lunch,
                'has_dinner': has_dinner,
                'has_as_needed': has_as_needed,
                'taken_breakfast': taken_breakfast,
                'taken_lunch': taken_lunch,
                'taken_dinner': taken_dinner,
                'taken_as_needed': taken_as_needed,
            }
        )
        
        action = "생성" if created else "업데이트"
        print(f"복용약 기록 {action} 성공: {medication_record.id}")
        
        return Response({
            'message': f'복용약 기록이 {action}되었습니다.',
            'medication_record': {
                'id': medication_record.id,
                'medication_name': medication_record.medication_name,
                'has_breakfast': medication_record.has_breakfast,
                'has_lunch': medication_record.has_lunch,
                'has_dinner': medication_record.has_dinner,
                'has_as_needed': medication_record.has_as_needed,
                'taken_breakfast': medication_record.taken_breakfast,
                'taken_lunch': medication_record.taken_lunch,
                'taken_dinner': medication_record.taken_dinner,
                'taken_as_needed': medication_record.taken_as_needed,
                'record_date': str(medication_record.record_date),
                'created_at': medication_record.created_at.isoformat(),
                'updated_at': medication_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except Exception as e:
        print(f"복용약 기록 생성 중 오류: {e}")
        return Response(
            {'error': f'복용약 기록 생성 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_medication_record(request):
    """
    특정 날짜의 복용약 기록 조회 API
    """
    try:
        date = request.GET.get('date')  # YYYY-MM-DD 형식
        
        if not date:
            return Response(
                {'error': '날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 날짜의 복용약 기록 조회
        medication_records = MedicationRecord.objects.filter(
            user=request.user,
            record_date=date
        ).order_by('medication_name')
        
        records = []
        for record in medication_records:
            records.append({
                'id': record.id,
                'medication_name': record.medication_name,
                'has_breakfast': record.has_breakfast,
                'has_lunch': record.has_lunch,
                'has_dinner': record.has_dinner,
                'has_as_needed': record.has_as_needed,
                'taken_breakfast': record.taken_breakfast,
                'taken_lunch': record.taken_lunch,
                'taken_dinner': record.taken_dinner,
                'taken_as_needed': record.taken_as_needed,
                'record_date': str(record.record_date),
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat(),
            })
        
        return Response({
            'message': '복용약 기록을 성공적으로 조회했습니다.',
            'medication_record': records[0] if records else None
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'복용약 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_medication_records(request):
    """
    특정 날짜의 복용약 기록 목록 조회 API
    """
    try:
        date = request.GET.get('date')  # YYYY-MM-DD 형식
        
        if not date:
            return Response(
                {'error': '날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 날짜의 복용약 기록 조회
        medication_records = MedicationRecord.objects.filter(
            user=request.user,
            record_date=date
        ).order_by('medication_name')
        
        records = []
        for record in medication_records:
            records.append({
                'id': record.id,
                'medication_name': record.medication_name,
                'has_breakfast': record.has_breakfast,
                'has_lunch': record.has_lunch,
                'has_dinner': record.has_dinner,
                'has_as_needed': record.has_as_needed,
                'taken_breakfast': record.taken_breakfast,
                'taken_lunch': record.taken_lunch,
                'taken_dinner': record.taken_dinner,
                'taken_as_needed': record.taken_as_needed,
                'record_date': str(record.record_date),
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat(),
            })
        
        return Response({
            'message': '복용약 기록 목록을 성공적으로 조회했습니다.',
            'medication_records': records
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'복용약 기록 목록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_medication_records_by_date_range(request):
    """
    기간별 복용약 기록 조회 API
    """
    try:
        start_date = request.GET.get('start_date')  # YYYY-MM-DD 형식
        end_date = request.GET.get('end_date')      # YYYY-MM-DD 형식
        
        if not start_date or not end_date:
            return Response(
                {'error': '시작 날짜와 종료 날짜가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(f"=== 기간별 복용약 기록 조회 API 호출됨 ===")
        print(f"시작 날짜: {start_date}")
        print(f"종료 날짜: {end_date}")
        print(f"요청 사용자: {request.user}")
        
        # 기간별 복용약 기록 조회
        medication_records = MedicationRecord.objects.filter(
            user=request.user,
            record_date__range=[start_date, end_date]
        ).order_by('record_date', 'medication_name')
        
        print(f"조회된 기록 수: {medication_records.count()}")
        
        records = []
        for record in medication_records:
            records.append({
                'id': record.id,
                'medication_name': record.medication_name,
                'has_breakfast': record.has_breakfast,
                'has_lunch': record.has_lunch,
                'has_dinner': record.has_dinner,
                'has_as_needed': record.has_as_needed,
                'taken_breakfast': record.taken_breakfast,
                'taken_lunch': record.taken_lunch,
                'taken_dinner': record.taken_dinner,
                'taken_as_needed': record.taken_as_needed,
                'record_date': str(record.record_date),
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat(),
            })
        
        print(f"반환할 기록 수: {len(records)}")
        
        return Response({
            'message': '기간별 복용약 기록을 성공적으로 조회했습니다.',
            'medication_records': records
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"기간별 복용약 기록 조회 중 오류: {str(e)}")
        return Response(
            {'error': f'기간별 복용약 기록 조회 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_medication_record(request, id):
    """
    복용약 기록 수정 API
    """
    try:
        print(f"=== 복용약 기록 수정 API 호출됨 (ID: {id}) ===")
        print(f"요청 데이터: {request.data}")
        print(f"요청 사용자: {request.user}")
        
        data = request.data
        taken_breakfast = data.get('taken_breakfast')
        taken_lunch = data.get('taken_lunch')
        taken_dinner = data.get('taken_dinner')
        taken_as_needed = data.get('taken_as_needed')
        
        # 해당 기록 조회
        try:
            medication_record = MedicationRecord.objects.get(
                id=id,
                user=request.user
            )
        except MedicationRecord.DoesNotExist:
            return Response(
                {'error': '해당 복용약 기록을 찾을 수 없습니다.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 복용 여부 업데이트
        if taken_breakfast is not None:
            medication_record.taken_breakfast = taken_breakfast
        if taken_lunch is not None:
            medication_record.taken_lunch = taken_lunch
        if taken_dinner is not None:
            medication_record.taken_dinner = taken_dinner
        if taken_as_needed is not None:
            medication_record.taken_as_needed = taken_as_needed
        
        medication_record.save()
        
        print(f"복용약 기록 수정 성공: {medication_record.id}")
        
        return Response({
            'message': '복용약 기록이 수정되었습니다.',
            'medication_record': {
                'id': medication_record.id,
                'medication_name': medication_record.medication_name,
                'has_breakfast': medication_record.has_breakfast,
                'has_lunch': medication_record.has_lunch,
                'has_dinner': medication_record.has_dinner,
                'has_as_needed': medication_record.has_as_needed,
                'taken_breakfast': medication_record.taken_breakfast,
                'taken_lunch': medication_record.taken_lunch,
                'taken_dinner': medication_record.taken_dinner,
                'taken_as_needed': medication_record.taken_as_needed,
                'record_date': str(medication_record.record_date),
                'created_at': medication_record.created_at.isoformat(),
                'updated_at': medication_record.updated_at.isoformat(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"복용약 기록 수정 중 오류: {e}")
        return Response(
            {'error': f'복용약 기록 수정 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_medication_record(request, id):
    """
    복용약 기록 삭제 API
    """
    try:
        # 해당 기록 조회
        try:
            medication_record = MedicationRecord.objects.get(
                id=id,
                user=request.user
            )
        except MedicationRecord.DoesNotExist:
            return Response(
                {'error': '해당 복용약 기록을 찾을 수 없습니다.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        medication_record.delete()
        
        return Response({
            'message': '복용약 기록이 삭제되었습니다.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'복용약 기록 삭제 중 오류가 발생했습니다: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


