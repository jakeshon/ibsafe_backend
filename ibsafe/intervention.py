import os
import sys
import time
import torch
import numpy as np
import re
import gc
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.utils import timezone
import pytz

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from .models import (
    UserProfile, UserSleepRecord, UserFoodRecord, UserWaterRecord, 
    UserExerciseRecord, IBSSSSRecord, IBSQOLRecord, PSSStressRecord,
    InterventionRecord, BatchSchedule
)

# rule.py에서 함수들 import
from .rule import recommend_diet, recommend_sleep, recommend_step


def get_number(number):
    """
    문자열에서 숫자를 추출하는 함수
    """
    m = re.search(r'"\s*([0-9]+(?:\.[0-9]+)?)\s*"', number)
    num_str = m.group(1) if m else None   # '7'
    num = float(num_str) if num_str and '.' in num_str else int(num_str) 

    return num


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


def format_allergies_list(user_profile_data):
    """
    사용자 프로필 데이터에서 알레르기 정보를 리스트로 변환
    """
    allergies = []
    if user_profile_data.get('has_gluten_allergy'):
        allergies.append('글루텐')
    if user_profile_data.get('has_lactose_allergy'):
        allergies.append('유당')
    if user_profile_data.get('has_nut_allergy'):
        allergies.append('견과류')
    if user_profile_data.get('has_seafood_allergy'):
        allergies.append('해산물')
    if user_profile_data.get('has_egg_allergy'):
        allergies.append('계란')
    if user_profile_data.get('has_soy_allergy'):
        allergies.append('대두')
    if user_profile_data.get('has_lactose_intolerance'):
        allergies.append('유당불내증')
    return allergies


def get_recent_food_names(food_data):
    """
    최근 음식 데이터에서 음식 이름만 추출
    """
    food_names = []
    for record in food_data:
        if 'food_name' in record:
            food_names.append(record['food_name'])
    return food_names


def get_week_step_counts(exercise_data):
    """
    일주일간 운동 데이터에서 걸음수만 추출
    """
    step_counts = []
    for record in exercise_data:
        if 'current_steps' in record:
            step_counts.append(record['current_steps'])
    return step_counts


def inference_rule(
    allergies,
    restrictions,
    recent_3days,
    today_sleep,
    week_step
):
    """
    Rule-based 중재 추론 함수
    """
    try:
        outputs = {}
        # 결과를 JSON 형태로 구조화 (새로운 구조에 맞게)
        EXCEL_PATH = os.path.join(os.path.dirname(__file__), "llm_oss", "Food_list.xlsx")
        diet_recommendations = recommend_diet(excel_path=EXCEL_PATH,
                                        recent_3days=recent_3days,
                                        allergies=allergies,
                                        restrictions=restrictions,
                                        random_seed=None)
        
        diet_breakfast = diet_recommendations['아침']
        diet_lunch = diet_recommendations['점심']
        diet_dinner = diet_recommendations['저녁']

        sleep_evaluation = recommend_sleep(today_sleep)
        sleep_target = 8

        exercise_evaluation, exercise_target = recommend_step(week_step)

        results = {
            "diet": {
                "Evaluation": "식단 권고사항이 생성되었습니다.",
                "Target": {
                    "Breakfast": diet_breakfast,
                    "Lunch": diet_lunch,
                    "Dinner": diet_dinner,
                    "Summary": "균형 잡힌 식단을 권장합니다.",
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
        
        print(f"Rule-based 중재 완료")
        return results, outputs, ""
        
    except Exception as e:
        error_message = f"Rule-based 중재 오류: {str(e)}"
        print(f"중재 오류: {error_message}")
        
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
        
        return empty_results, {}, error_message


def inference_llm(
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
    LLM 기반 중재 추론 함수
    """
    try:
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
            diet_evaluation = diet_evaluation.split(":")[-1].lstrip()
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
                        "Breakfast": diet_breakfast,
                        "Lunch": diet_lunch,
                        "Dinner": diet_dinner,
                        "Summary": diet_summary,
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
        
        return results, outputs, ""
        
    except Exception as e:
        error_message = f"LLM 중재 오류: {str(e)}"
        print(f"LLM 중재 오류: {error_message}")
        
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
        
        return empty_results, {}, error_message


def inference_rule_sleep(today_sleep):
    """
    Rule-based 수면 중재 추론 함수
    """
    try:
        # Rule-based 수면 권고사항
        sleep_evaluation = recommend_sleep(today_sleep)
        sleep_target = 8

        results = {
            "sleep": {
                "Evaluation": sleep_evaluation,
                "Target": sleep_target,
            }
        }
        
        print(f"Rule-based 수면 중재 완료")
        return results, ""
        
    except Exception as e:
        error_message = f"Rule-based 수면 중재 오류: {str(e)}"
        print(f"수면 중재 오류: {error_message}")
        
        empty_results = {
            "sleep": {
                "Evaluation": "",
                "Target": 0.0,
            }
        }
        
        return empty_results, error_message


def inference_llm_sleep(
    ollama_base_url,
    ollama_model,
    today_sleep,
    use_rag=True
):
    """
    LLM 기반 수면 중재 추론 함수
    """
    try:
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
        
        # 수면 관련 컨텍스트 검색
        context = ""
        if use_rag and embed_model and vectorDB and chunks:
            try:
                retrieval_query = "Guidelines on sleep quality, sleep hygiene, and sleep disorders in IBS patients"
                query_embedding = embed_model.encode([retrieval_query])
                _, top_indices = vectorDB["sleep"].search(np.array(query_embedding), k=2)
                context = "\n\n".join([str(chunks["sleep"][i]) for i in top_indices[0]])
            except Exception as e:
                print(f"RAG 검색 오류 (sleep): {e}")
                context = ""

        # 수면 중재 문장 생성
        try:
            # llm_oss 경로 추가
            llm_oss_path = os.path.join(os.path.dirname(__file__), 'llm_oss')
            if llm_oss_path not in sys.path:
                sys.path.append(llm_oss_path)
                
            from make_prompt_korean import make_sleep_prompt_ko
            
            prompt_ko = make_sleep_prompt_ko(context=context, today_sleep=today_sleep)
            response = _call_ollama_api(ollama_base_url, ollama_model, prompt_ko)
        except Exception as e:
            print(f"수면 프롬프트 생성 오류: {e}")
            response = "수면 권고사항을 생성할 수 없습니다."

        print(f'=== 수면 중재 완료 ===')
        print(f'수면 프롬프트: {prompt_ko}')
        print(f'수면 응답: {response}')
        print(f'=== 수면 중재 완료 끝 ===')
        
        # 메모리 정리
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            # MPS에서는 empty_cache가 없으므로 gc만 실행
            pass

        try:
            # 수면 결과 파싱
            sleep_evaluation = response.split('\n')[0].split(":")[-1].lstrip()
            sleep_target = get_number(response.split('\n')[1].split(":")[-1].lstrip())

            # 결과를 JSON 형태로 구조화
            results = {
                "sleep": {
                    "Evaluation": sleep_evaluation,
                    "Target": sleep_target,
                }
            }
            
        except Exception as e:
            error_message = f"수면 결과 파싱 오류: {str(e)}"
            print(f"수면 결과 파싱 오류: {error_message}")
            
            # 오류 발생 시 빈 results 반환
            empty_results = {
                "sleep": {
                    "Evaluation": "",
                    "Target": 0.0,
                }
            }
            
            return empty_results, error_message
        
        return results, ""
        
    except Exception as e:
        error_message = f"LLM 수면 중재 오류: {str(e)}"
        print(f"LLM 수면 중재 오류: {error_message}")
        
        empty_results = {
            "sleep": {
                "Evaluation": "",
                "Target": 0.0,
            }
        }
        
        return empty_results, error_message


def run_intervention_inference_sleep(
    ollama_base_url,
    ollama_model,
    today_sleep,
    use_rag=True,
    mode='RULE'
):
    """
    수면 중재 추론 실행 함수
    """
    print(f"수면 중재 추론 시작 - 모드: {mode}")
    
    if mode == 'RULE':
        return inference_rule_sleep(today_sleep)
    else:  # LLM 모드
        return inference_llm_sleep(
            ollama_base_url=ollama_base_url,
            ollama_model=ollama_model,
            today_sleep=today_sleep,
            use_rag=use_rag
        )


def run_intervention_inference(
    ollama_base_url,
    ollama_model,
    allergies,
    restrictions,
    recent_3days,
    use_rag,
    today_sleep,
    week_step,
    today_diet,
    table_food,
    mode='RULE'
):
    """
    통합 중재 추론 실행 함수
    """
    print(f"통합 중재 추론 시작 - 모드: {mode}")
    
    if mode == 'RULE':
        return inference_rule(
            allergies=allergies,
            restrictions=restrictions,
            recent_3days=recent_3days,
            today_sleep=today_sleep,
            week_step=week_step
        )
    else:  # LLM 모드
        return inference_llm(
            ollama_base_url=ollama_base_url,
            ollama_model=ollama_model,
            allergies=allergies,
            restrictions=restrictions,
            recent_3days=recent_3days,
            use_rag=use_rag,
            today_sleep=today_sleep,
            week_step=week_step,
            today_diet=today_diet,
            table_food=table_food
        )


def process_user_intervention(user, record_date, mode='RULE'):
    """
    특정 사용자의 중재 처리를 위한 통합 함수
    """
    print(f"사용자 {user.username} 중재 처리 시작 - 모드: {mode}")
    
    try:
        # 사용자 프로필 정보
        profile = user.profile
        user_profile_data = {
            'has_gluten_allergy': profile.has_gluten_allergy,
            'has_lactose_allergy': profile.has_lactose_allergy,
            'has_nut_allergy': profile.has_nut_allergy,
            'has_seafood_allergy': profile.has_seafood_allergy,
            'has_egg_allergy': profile.has_egg_allergy,
            'has_soy_allergy': profile.has_soy_allergy,
            'has_lactose_intolerance': profile.has_lactose_intolerance,
        }
        
        # 수면 데이터
        sleep_record = UserSleepRecord.objects.get(user=user, record_date=record_date)
        sleep_data = {
            'sleep_hours': sleep_record.sleep_hours,
        }
        
        # 음식 데이터 (최근 3일간)
        three_days_start = record_date - timedelta(days=2)
        food_records = UserFoodRecord.objects.filter(
            user=user,
            record_date__range=[three_days_start, record_date]
        ).select_related('food').order_by('record_date', 'meal_type')
        
        food_data = []
        for record in food_records:
            food_data.append({
                'food_name': record.food.food_name,
            })
        
        # 오늘 음식 데이터 (today_diet용)
        today_food_records = UserFoodRecord.objects.filter(
            user=user,
            record_date=record_date
        ).select_related('food').order_by('meal_type')
        
        today_diet = []
        for record in today_food_records:
            food_name = record.food.food_name
            if food_name not in today_diet:
                today_diet.append(food_name)
        
        # 운동 데이터 (일주일간)
        week_start = record_date - timedelta(days=6)
        exercise_records = UserExerciseRecord.objects.filter(
            user=user,
            record_date__range=[week_start, record_date]
        ).order_by('record_date')
        
        exercise_data = []
        for record in exercise_records:
            exercise_data.append({
                'current_steps': record.current_steps,
            })
        
        # 음식 DB 로드
        llm_oss_path = os.path.join(os.path.dirname(__file__), 'llm_oss')
        food_db_path = os.path.join(llm_oss_path, "Food_list.xlsx")
        
        if not os.path.exists(food_db_path):
            raise Exception(f"음식 DB 파일을 찾을 수 없습니다: {food_db_path}")
        
        import pandas as pd
        df = pd.read_excel(food_db_path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        required = {"food", "fodmap", "fiber"}
        if not required.issubset(set(df.columns)):
            raise Exception(f"CSV에 필수 컬럼이 없습니다: {required} / 현재: {set(df.columns)}")
        
        table_food = df.to_csv(index=False)
        
        # 중재 추론 실행
        start_time = time.time()
        
        results, outputs, error_message = run_intervention_inference(
            ollama_base_url="http://127.0.0.1:29005",
            ollama_model="gpt-oss:20b",
            allergies=format_allergies_list(user_profile_data),
            restrictions=[],
            recent_3days=get_recent_food_names(food_data),
            use_rag=True,
            today_sleep=sleep_data['sleep_hours'],
            week_step=get_week_step_counts(exercise_data),
            today_diet=today_diet,
            table_food=table_food,
            mode=mode
        )
        
        processing_time = time.time() - start_time
        
        # 중재 결과를 데이터베이스에 저장
        target_date = record_date + timedelta(days=1)
        
        intervention_record = InterventionRecord.objects.create(
            user=user,
            record_date=record_date,
            target_date=target_date,
            diet_evaluation=results.get('diet', {}).get('Evaluation', ''),
            diet_target=results.get('diet', {}).get('Target', {}),
            sleep_evaluation=results.get('sleep', {}).get('Evaluation', ''),
            sleep_target=results.get('sleep', {}).get('Target', 0.0),
            exercise_evaluation=results.get('exercise', {}).get('Evaluation', ''),
            exercise_target=results.get('exercise', {}).get('Target', 0),
            processing_time=processing_time,
            error_message=error_message,
            # 입력 파라미터 저장
            input_allergies=format_allergies_list(user_profile_data),
            input_restrictions=[],
            input_recent_3days=get_recent_food_names(food_data),
            input_today_sleep=sleep_data['sleep_hours'],
            input_week_step=get_week_step_counts(exercise_data),
            input_today_diet=today_diet,
            input_use_rag=True,
            input_ollama_model="RULE" if mode == 'RULE' else "gpt-oss:20b",
            # LLM 출력 결과 저장
            outputs=outputs,
        )
        
        print(f"사용자 {user.username}: 중재 권고사항 생성 완료 (처리시간: {processing_time:.2f}초)")
        return True, processing_time, error_message
        
    except Exception as e:
        error_message = f"사용자 중재 처리 오류: {str(e)}"
        print(f"사용자 {user.username}: {error_message}")
        
        # 오류 정보를 데이터베이스에 저장
        target_date = record_date + timedelta(days=1)
        InterventionRecord.objects.create(
            user=user,
            record_date=record_date,
            target_date=target_date,
            diet_evaluation='',
            diet_target={},
            sleep_evaluation='',
            sleep_target=sleep_data.get('sleep_hours', 0),
            exercise_evaluation='',
            exercise_target=0,
            processing_time=0.0,
            error_message=error_message,
            # 입력 파라미터 저장
            input_allergies=format_allergies_list(user_profile_data),
            input_restrictions=[],
            input_recent_3days=get_recent_food_names(food_data),
            input_today_sleep=sleep_data.get('sleep_hours', 0),
            input_week_step=get_week_step_counts(exercise_data),
            input_today_diet=today_diet,
            input_use_rag=True,
            input_ollama_model="RULE" if mode == 'RULE' else "gpt-oss:20b",
            # LLM 출력 결과 저장 (오류 시 빈 딕셔너리)
            outputs={},
        )
        return False, 0.0, error_message


def process_user_sleep_intervention(user, record_date, mode='RULE'):
    """
    특정 사용자의 수면 중재 처리를 위한 통합 함수
    """
    print(f"사용자 {user.username} 수면 중재 처리 시작 - 모드: {mode}")
    
    try:
        # 수면 데이터
        sleep_record = UserSleepRecord.objects.get(user=user, record_date=record_date)
        sleep_data = {
            'sleep_hours': sleep_record.sleep_hours,
        }
        
        # 수면 중재 추론 실행
        start_time = time.time()
        
        results, error_message = run_intervention_inference_sleep(
            ollama_base_url="http://127.0.0.1:29005",
            ollama_model="gpt-oss:20b",
            today_sleep=sleep_data['sleep_hours'],
            use_rag=True,
            mode=mode
        )
        
        processing_time = time.time() - start_time
        
        # 수면 중재 결과를 데이터베이스에 저장
        target_date = record_date + timedelta(days=1)
        
        intervention_record = InterventionRecord.objects.create(
            user=user,
            record_date=record_date,
            target_date=target_date,
            diet_evaluation='',  # 수면 중재이므로 빈 값
            diet_target={},      # 수면 중재이므로 빈 값
            sleep_evaluation=results.get('sleep', {}).get('Evaluation', ''),
            sleep_target=results.get('sleep', {}).get('Target', 0.0),
            exercise_evaluation='',  # 수면 중재이므로 빈 값
            exercise_target=0,       # 수면 중재이므로 빈 값
            processing_time=processing_time,
            error_message=error_message,
            # 입력 파라미터 저장
            input_allergies=[],
            input_restrictions=[],
            input_recent_3days=[],
            input_today_sleep=sleep_data['sleep_hours'],
            input_week_step=[],
            input_today_diet=[],
            input_use_rag=True,
            input_ollama_model="RULE" if mode == 'RULE' else "gpt-oss:20b",
            # LLM 출력 결과 저장
            outputs=results,
        )
        
        print(f"사용자 {user.username}: 수면 중재 권고사항 생성 완료 (처리시간: {processing_time:.2f}초)")
        return True, processing_time, error_message
        
    except Exception as e:
        error_message = f"사용자 수면 중재 처리 오류: {str(e)}"
        print(f"사용자 {user.username}: {error_message}")
        
        # 오류 정보를 데이터베이스에 저장
        target_date = record_date + timedelta(days=1)
        InterventionRecord.objects.create(
            user=user,
            record_date=record_date,
            target_date=target_date,
            diet_evaluation='',
            diet_target={},
            sleep_evaluation='',
            sleep_target=sleep_data.get('sleep_hours', 0),
            exercise_evaluation='',
            exercise_target=0,
            processing_time=0.0,
            error_message=error_message,
            # 입력 파라미터 저장
            input_allergies=[],
            input_restrictions=[],
            input_recent_3days=[],
            input_today_sleep=sleep_data.get('sleep_hours', 0),
            input_week_step=[],
            input_today_diet=[],
            input_use_rag=True,
            input_ollama_model="RULE" if mode == 'RULE' else "gpt-oss:20b",
            # LLM 출력 결과 저장 (오류 시 빈 딕셔너리)
            outputs={},
        )
        return False, 0.0, error_message
