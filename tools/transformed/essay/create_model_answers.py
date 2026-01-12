#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
서술형 문제 모델 답변 생성
"""

import os
import json
import argparse
import random
import configparser
from tqdm import tqdm

from tools import ONEDRIVE_PATH, PROJECT_ROOT_PATH
from tools.core.llm_query import LLMQuery


def get_api_key():
    """llm_config.ini에서 API 키 읽기"""
    config_path = os.path.join(PROJECT_ROOT_PATH, 'llm_config.ini')
    if os.path.exists(config_path):
        try:
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            if config.has_option("OPENROUTER", "key_evaluate"):
                return config.get("OPENROUTER", "key_evaluate")
            elif config.has_option("OPENROUTER", "key_essay"):
                return config.get("OPENROUTER", "key_essay")
            elif config.has_option("OPENROUTER", "key"):
                return config.get("OPENROUTER", "key")
        except Exception as e:
            print(f"경고: 설정 파일에서 API 키를 읽는 중 오류 발생: {e}")
    return None


def process_essay_questions(model, round_number, round_folder, selected_questions, api_key=None, use_server_mode=False):
    """특정 모델과 회차에 대해 서술형 문제를 처리하는 함수
    
    Args:
        model: 모델 이름
        round_number: 회차 번호 (예: '1', '2', '3', '4', '5')
        round_folder: 회차 폴더명 (예: '1st', '2nd', '3rd', '4th', '5th') - 파일명에 사용
        selected_questions: 선택된 문제 리스트
        api_key: API 키
        use_server_mode: 서버 모드 사용 여부
    """
    llm = LLMQuery(api_key=api_key)
    
    # 서버 모드일 때 모델 로드
    if use_server_mode:
        print(f"[VLLM] 모델 로드 중: {model}")
        llm.load_vllm_model(model)
        print(f"[VLLM] 모델 로드 완료: {model}")
    
    eval_model_answer = []
    mode_str = "[VLLM]" if use_server_mode else "[API]"
    print(f"\n{mode_str} 답변 모델: {model}, 회차: {round_number}, 선택된 문제 수: {len(selected_questions)}")
    
    for q in tqdm(selected_questions, desc=f"{model} - {round_number}"):
        user_prompt = f"""
서술형 질문: {q['essay_question']}
키워드: {q['essay_keyword']}
"""
        system_prompt = "주어진 키워드를 모두 사용하여 서술형 문제에 대한 답변을 작성해주세요."
        
        if use_server_mode:
            answer = llm.query_vllm(system_prompt, user_prompt)
        else:
            answer = llm.query_openrouter(system_prompt, user_prompt, model_name=model)
        
        answers = {
            'file_id': q['file_id'],
            'tag': q['tag'],
            'question': q['essay_question'],
            'keyword': q['essay_keyword'],
            'answer': answer
        }
        eval_model_answer.append(answers)
    
    # 모델 이름에서 슬래시를 언더스코어로 변경하여 파일명에 사용
    model_name_for_file = model.replace('/', '_')
    # 4단계 출력: {model_name}_{round_number}.json
    output_filename = f'{model_name_for_file}_{round_number}.json'
    
    # 저장 경로: 9_multiple_to_essay/answers/{round_folder}/
    output_dir = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '9_multiple_to_essay', 'answers', round_folder)
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, output_filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(eval_model_answer, f, ensure_ascii=False, indent=4)
    
    print(f"결과가 {output_path}에 저장되었습니다.")


def generate_essay_answers(model, round_number, round_folder, selected_questions, api_key=None, use_server_mode=False):
    """process_essay_questions의 별칭 (하위 호환성)"""
    return process_essay_questions(model, round_number, round_folder, selected_questions, api_key, use_server_mode)


def main():
    parser = argparse.ArgumentParser(description='서술형 문제 답변 생성')
    parser.add_argument('--models', type=str, required=True, help='모델 이름 (예: google/gemini-2.5-pro 또는 로컬 모델 경로)')
    parser.add_argument('--sets', type=str, nargs='+', help='회차 리스트 (예: 1 2 3 또는 생략 시 전체 회차)')
    parser.add_argument('--servermode', action='store_true', help='vLLM 서버 모드 사용 (로컬 모델 로드)')
    
    args = parser.parse_args()
    
    use_server_mode = args.servermode
    
    # API 키 읽기 (서버 모드가 아닐 때만 필요)
    api_key = None
    if not use_server_mode:
        api_key = get_api_key()
        if api_key is None:
            print("경고: llm_config.ini에서 API 키를 찾을 수 없습니다. API 키 없이 진행합니다.")
    else:
        print("[VLLM] 서버 모드: API 키가 필요하지 않습니다.")
    
    model = args.models
    
    # 회차에 따른 폴더명 매핑
    round_folders = {'1': '1st', '2': '2nd', '3': '3rd', '4': '4th', '5': '5th'}
    
    # --sets가 없으면 전체 회차(1, 2, 3, 4, 5) 실행
    if args.sets is None:
        sets_to_process = ['1', '2', '3', '4', '5']
    else:
        sets_to_process = args.sets
        # 유효성 검사
        for s in sets_to_process:
            if s not in round_folders:
                print(f"오류: 회차 {s}는 유효하지 않습니다. 회차는 1, 2, 3, 4, 5 중 하나여야 합니다.")
                return
    
    # 각 회차별로 순차적으로 처리
    for round_number in sets_to_process:
        round_folder = round_folders[round_number]
        
        # 각 회차별 파일에서 데이터 로드
        input_file = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '9_multiple_to_essay', f'essay_w_keyword_{round_folder}.json')
        
        if not os.path.exists(input_file):
            print(f"경고: 파일을 찾을 수 없습니다: {input_file}")
            continue
        
        print(f"\n[{round_folder}] 파일 로드 중: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            full_explanation = json.load(f)
        
        print(f"[{round_folder}] 전체 문제 수: {len(full_explanation)}")
        
        # seed 고정하여 랜덤으로 150문제 추출 (각 회차마다 독립적으로)
        random.seed(42)
        selected_questions = random.sample(full_explanation, min(150, len(full_explanation)))
        
        print(f"[{round_folder}] 선택된 문제 수: {len(selected_questions)}")
        
        # 해당 회차 처리 및 저장
        process_essay_questions(model, round_number, round_folder, selected_questions, api_key, use_server_mode)


if __name__ == '__main__':
    main()

