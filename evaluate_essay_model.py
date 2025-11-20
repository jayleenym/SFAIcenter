#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
서술형 문제 모델 평가 및 통계 생성 스크립트

사용법:
    python evaluate_essay_model.py --model_name <model>
    python evaluate_essay_model.py --model_name <model> --sets <set1> [<set2> ...]
    
예시:
    python evaluate_essay_model.py --model_name google/gemini-2.5-pro
    python evaluate_essay_model.py --model_name google/gemini-2.5-pro --sets 1 2 3
    # --sets가 없으면 1~5까지 모두 처리
"""

import os
import json
import re
import sys
import argparse
from typing import Dict, List, Any, Optional
from tqdm import tqdm
from collections import defaultdict

from tools.pipeline.config import ONEDRIVE_PATH
from tools.core.llm_query import LLMQuery




def evaluate_essay_answer(question_data: Dict, model_answer: str, llm_instance: LLMQuery, 
                         keyword_check_model: str = 'google/gemini-2.5-flash',
                         scoring_model: str = 'google/gemini-3-pro-preview', 
                         best_answer: str = None) -> Dict[str, Any]:
    """
    서술형 답변 평가 함수
    
    Args:
        question_data: 문제 데이터 (essay_question, essay_keyword, essay_answer 포함)
        model_answer: 평가할 모델 답변
        llm_instance: LLMQuery 인스턴스
        keyword_check_model: 키워드 포함 여부 확인에 사용할 LLM 모델명
        scoring_model: 점수 평가에 사용할 LLM 모델명
        best_answer: 모범답안 (선택사항)
    
    Returns:
        dict: {
            'has_all_keywords': bool,
            'keyword_scores': dict,  # 키워드별 점수 (1~5점)
            'final_score': float,    # 최종 점수 (100점 만점)
            'keyword_check_response': str,
            'scoring_response': str
        }
    """
    result = {
        'has_all_keywords': False,
        'keyword_scores': {},
        'final_score': 0.0,
        'keyword_check_response': '',
        'scoring_response': ''
    }
    
    # 1단계: 키워드 포함 여부 판단 (LLM 1번 호출)
    keyword_check_system_prompt = """
당신은 서술형 문제 채점자입니다.
다음 모델 답변에 제시된 키워드가 모두 포함되어있는지 판단해주세요.
키워드가 모두 포함되어있다면 True, 하나라도 포함되어있지 않다면 False를 반환해주세요.
반드시 True 또는 False만 반환하세요.
"""
    
    keyword_check_user_prompt = f"""
서술형 질문: {question_data['essay_question']}
키워드: {question_data['essay_keyword']}
-----
모델 답변(평가대상): {model_answer}
"""
    
    keyword_response = llm_instance.query_openrouter(
        keyword_check_system_prompt, 
        keyword_check_user_prompt, 
        model_name=keyword_check_model
    )
    result['keyword_check_response'] = keyword_response
    
    has_all_keywords = 'True' in keyword_response or 'true' in keyword_response.lower()
    result['has_all_keywords'] = has_all_keywords
    
    # 키워드가 모두 포함되지 않은 경우
    if not has_all_keywords:
        result['final_score'] = 0.0
        return result
    
    # 2단계: 키워드별 모순/오류 평가 (LLM 2번 호출)
    scoring_system_prompt = """
당신은 서술형 문제 채점자입니다.
모범답안과 모델 답변을 비교하여, 각 키워드에 대한 설명이 모범답안과 얼마나 일치하는지 평가해주세요.

평가 기준:
- 1점: 전혀 다른 이야기
- 2점: 심각한 모순
- 3점: 약간의 모순
- 4점: 모순 없음
- 5점: 모범답안과 동일

각 키워드별로 1~5점을 부여하고, JSON 형식으로 반환해주세요.
예시 형식: {"키워드1": 5, "키워드2": 4, "키워드3": 3}
"""
    
    # 모범답안 우선순위: best_answer 파라미터 > question_data의 essay_answer
    best_ans = best_answer if best_answer is not None else question_data.get('essay_answer', '모범답안이 없습니다.')
    
    scoring_user_prompt = f"""
서술형 질문: {question_data['essay_question']}
키워드: {question_data['essay_keyword']}

모범답안:
{best_ans}

모델 답변(평가대상):
{model_answer}

각 키워드별로 1~5점을 부여하여 JSON 형식으로 반환해주세요.
"""
    
    scoring_response = llm_instance.query_openrouter(
        scoring_system_prompt, 
        scoring_user_prompt, 
        model_name=scoring_model
    )
    result['scoring_response'] = scoring_response
    
    # JSON 파싱 (중첩된 JSON도 처리)
    # JSON 객체 찾기 (중첩된 중괄호도 처리)
    brace_count = 0
    start_idx = -1
    json_parsed = False
    for i, char in enumerate(scoring_response):
        if char == '{':
            if start_idx == -1:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                json_str = scoring_response[start_idx:i+1]
                try:
                    keyword_scores = json.loads(json_str)
                    result['keyword_scores'] = keyword_scores
                    
                    # 100점 척도로 변환
                    scores = list(keyword_scores.values())
                    if scores:
                        avg_score = sum(scores) / len(scores)
                        final_score = (avg_score / 5) * 100  # 5점 만점을 100점 만점으로 변환
                        result['final_score'] = final_score
                    json_parsed = True
                    break
                except json.JSONDecodeError:
                    continue
    
    if not json_parsed:
        print(f"JSON 파싱 실패: {scoring_response}")
        result['final_score'] = 0.0
    
    return result


def calculate_statistics(evaluation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    평가 결과 통계 계산
    
    Args:
        evaluation_results: 평가 결과 리스트
    
    Returns:
        dict: 통계 정보
    """
    stats = {
        'total_count': len(evaluation_results),
        'keyword_inclusion_rate': 0.0,
        'average_score': 0.0,
        'score_distribution': {},
        'keyword_avg_scores': defaultdict(list),
        'min_score': 100.0,
        'max_score': 0.0,
        'zero_score_count': 0,
        'perfect_score_count': 0
    }
    
    if not evaluation_results:
        return stats
    
    # 키워드 포함 여부 통계
    keyword_included = sum(1 for r in evaluation_results if r.get('has_all_keywords', False))
    stats['keyword_inclusion_rate'] = (keyword_included / len(evaluation_results)) * 100
    
    # 점수 통계
    scores = [r.get('final_score', 0.0) for r in evaluation_results]
    stats['average_score'] = sum(scores) / len(scores) if scores else 0.0
    stats['min_score'] = min(scores) if scores else 0.0
    stats['max_score'] = max(scores) if scores else 0.0
    stats['zero_score_count'] = sum(1 for s in scores if s == 0.0)
    stats['perfect_score_count'] = sum(1 for s in scores if s == 100.0)
    
    # 점수 분포 (10점 단위)
    for score in scores:
        bucket = int(score // 10) * 10
        stats['score_distribution'][f"{bucket}-{bucket+9}점"] = stats['score_distribution'].get(f"{bucket}-{bucket+9}점", 0) + 1
    
    # 키워드별 평균 점수
    for result in evaluation_results:
        keyword_scores = result.get('keyword_scores', {})
        for keyword, score in keyword_scores.items():
            stats['keyword_avg_scores'][keyword].append(score)
    
    # 키워드별 평균 계산
    keyword_avg = {}
    for keyword, score_list in stats['keyword_avg_scores'].items():
        if score_list:
            keyword_avg[keyword] = sum(score_list) / len(score_list)
    stats['keyword_avg_scores'] = keyword_avg
    
    return stats


def print_statistics(stats: Dict[str, Any], model_name: str):
    """
    통계 출력
    
    Args:
        stats: 통계 정보
        model_name: 평가한 모델명
    """
    print("\n" + "="*60)
    print(f"모델 평가 통계: {model_name}")
    print("="*60)
    print(f"\n[기본 통계]")
    print(f"  총 평가 문제 수: {stats['total_count']}개")
    print(f"  키워드 포함 비율: {stats['keyword_inclusion_rate']:.2f}%")
    print(f"  평균 점수: {stats['average_score']:.2f}점")
    print(f"  최고 점수: {stats['max_score']:.2f}점")
    print(f"  최저 점수: {stats['min_score']:.2f}점")
    print(f"  0점 문제 수: {stats['zero_score_count']}개")
    print(f"  100점 문제 수: {stats['perfect_score_count']}개")
    
    print(f"\n[점수 분포]")
    for bucket in sorted(stats['score_distribution'].keys(), key=lambda x: int(x.split('-')[0])):
        count = stats['score_distribution'][bucket]
        percentage = (count / stats['total_count']) * 100
        print(f"  {bucket}: {count}개 ({percentage:.1f}%)")
    
    if stats['keyword_avg_scores']:
        print(f"\n[키워드별 평균 점수 (5점 만점)]")
        for keyword, avg_score in sorted(stats['keyword_avg_scores'].items()):
            print(f"  {keyword}: {avg_score:.2f}점")
    
    print("="*60 + "\n")


def evaluate_single_model(model_name: str, question_file: str, 
                          keyword_check_model: str = 'google/gemini-2.5-flash',
                          scoring_model: str = 'google/gemini-3-pro-preview',
                          set_num: Optional[int] = None, best_answers_dict: Optional[Dict] = None):
    """
    단일 모델 평가 수행
    
    Args:
        model_name: 평가할 모델명
        question_file: 문제 파일 경로
        keyword_check_model: 키워드 포함 여부 확인에 사용할 LLM 모델명
        scoring_model: 점수 평가에 사용할 LLM 모델명
        set_num: 세트 번호 (1~5, None이면 기본 경로 사용)
        best_answers_dict: 모범답안 딕셔너리 {(file_id, tag): answer}
    
    Returns:
        tuple: (evaluation_results, detailed_results, stats)
    """
    base_dir = os.path.dirname(question_file)
    model_safe_name = model_name.replace("/", "_")
    
    # 세트 번호가 있으면 해당 디렉토리에서 파일 읽기
    if set_num is not None:
        answer_file = os.path.join(base_dir, str(set_num), f'{model_safe_name}_answer.json')
    else:
        answer_file = os.path.join(base_dir, f'{model_safe_name}_answer.json')
    
    # 파일 존재 확인
    if not os.path.exists(answer_file):
        print(f"경고: 모델 답변 파일을 찾을 수 없습니다: {answer_file}")
        print(f"먼저 multi_essay_answer.py를 실행하여 모델 답변을 생성하세요.")
        return None, None, None
    
    # 데이터 로드
    print(f"\n[모델: {model_name}]")
    if set_num is not None:
        print(f"[세트: {set_num}]")
    print(f"문제 데이터 로드 중: {question_file}")
    with open(question_file, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    print(f"모델 답변 데이터 로드 중: {answer_file}")
    with open(answer_file, 'r', encoding='utf-8') as f:
        model_answers = json.load(f)
    
    print(f"총 {len(questions)}개의 문제를 평가합니다.")
    print(f"키워드 확인 모델: {keyword_check_model}")
    print(f"점수 평가 모델: {scoring_model}\n")
    
    # LLM 인스턴스 생성
    llm = LLMQuery(api_key = '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')
    
    # 평가 수행
    evaluation_results = []
    detailed_results = []
    
    # 모델 답변을 딕셔너리로 변환하여 빠른 조회 (file_id + tag를 키로 사용)
    answer_dict = {}
    for ma in model_answers:
        key = (ma.get('file_id'), ma.get('tag'))
        answer_dict[key] = ma.get('answer', '')
    
    for q in tqdm(questions, desc=f"평가 진행 [{model_name}]"):
        # 모델 답변 찾기 (file_id와 tag로 매칭)
        key = (q.get('file_id'), q.get('tag'))
        model_answer = answer_dict.get(key)
        
        if model_answer is None:
            # 순서대로 매칭 시도 (인덱스 기반, 같은 순서로 저장된 경우)
            q_idx = questions.index(q)
            if q_idx < len(model_answers):
                model_answer = model_answers[q_idx].get('answer', '')
            else:
                print(f"경고: 모델 답변을 찾을 수 없습니다. (file_id: {q.get('file_id')}, tag: {q.get('tag')})")
                continue
        
        # 모범답안 찾기
        best_answer = None
        if best_answers_dict:
            key = (q.get('file_id'), q.get('tag'))
            best_answer = best_answers_dict.get(key)
        
        # 평가 수행
        result = evaluate_essay_answer(q, model_answer, llm, keyword_check_model, scoring_model, best_answer)
        
        # 결과 저장
        evaluation_results.append(result)
        detailed_results.append({
            'file_id': q.get('file_id'),
            'tag': q.get('tag'),
            'question': q.get('essay_question'),
            'keyword': q.get('essay_keyword'),
            'has_all_keywords': result['has_all_keywords'],
            'final_score': result['final_score'],
            'keyword_scores': result['keyword_scores']
        })
    
    # 통계 계산
    stats = calculate_statistics(evaluation_results)
    
    return evaluation_results, detailed_results, stats


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='서술형 문제 모델 평가 및 통계 생성',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python evaluate_essay_model.py --model_name google/gemini-2.5-pro
  python evaluate_essay_model.py --model_name google/gemini-2.5-pro --sets 1 2 3
  python evaluate_essay_model.py --model_name google/gemini-2.5-pro --keyword_check_model google/gemini-2.5-flash --scoring_model google/gemini-3-pro-preview
  # --sets가 없으면 1~5까지 모두 처리
        """
    )
    parser.add_argument('--model_name', type=str, required=True,
                       help='평가할 모델명 (예: google/gemini-2.5-pro)')
    parser.add_argument('--sets', nargs='+', type=str, default=None,
                       help='처리할 세트 목록 (예: 1 2 3). None이면 1~5 모두 처리')
    parser.add_argument('--keyword_check_model', type=str, default='google/gemini-2.5-flash',
                       help='키워드 포함 여부 확인에 사용할 LLM 모델명 (기본값: google/gemini-2.5-flash)')
    parser.add_argument('--scoring_model', type=str, default='google/gemini-3-pro-preview',
                       help='점수 평가에 사용할 LLM 모델명 (기본값: google/gemini-3-pro-preview)')
    parser.add_argument('--base_dir', type=str, default=None,
                       help='기본 데이터 디렉토리 (None이면 ONEDRIVE_PATH/evaluation/eval_data/9_multiple_to_essay 사용)')
    
    args = parser.parse_args()
    
    # 경로 설정
    if args.base_dir:
        base_dir = args.base_dir
    else:
        base_dir = os.path.join(ONEDRIVE_PATH, 'evaluation', 'eval_data', '9_multiple_to_essay')
    
    # 모범답안 로드
    best_ans_file = os.path.join(base_dir, 'best_ans.json')
    best_answers_dict = {}
    if os.path.exists(best_ans_file):
        print(f"모범답안 로드 중: {best_ans_file}")
        with open(best_ans_file, 'r', encoding='utf-8') as f:
            best_answers = json.load(f)
        # file_id와 tag를 키로 하는 딕셔너리 생성
        for ba in best_answers:
            key = (ba.get('file_id'), ba.get('tag'))
            best_answers_dict[key] = ba.get('essay_answer', ba.get('answer', ''))
        print(f"모범답안 {len(best_answers_dict)}개 로드 완료")
    else:
        print(f"경고: 모범답안 파일을 찾을 수 없습니다: {best_ans_file}")
    
    # 문제 파일 경로 (기본적으로 essay_w_keyword.json 사용)
    question_file = os.path.join(base_dir, 'essay_w_keyword.json')
    if not os.path.exists(question_file):
        print(f"오류: 문제 파일을 찾을 수 없습니다: {question_file}")
        sys.exit(1)
    
    # 세트 처리
    if args.sets:
        # 지정된 세트만 처리
        set_numbers = []
        for set_name in args.sets:
            if set_name.isdigit():
                set_num = int(set_name)
                if 1 <= set_num <= 5:
                    set_numbers.append(set_num)
                else:
                    print(f"경고: 세트 번호는 1~5 사이여야 합니다: {set_name}")
            else:
                print(f"경고: 숫자가 아닌 세트 이름은 무시됩니다: {set_name}")
        if not set_numbers:
            print("오류: 유효한 세트 번호가 없습니다.")
            sys.exit(1)
    else:
        # --sets가 없으면 1~5 모두 처리
        set_numbers = [1, 2, 3, 4, 5]
    
    # 각 세트에 대해 평가 수행
    for set_num in set_numbers:
        print(f"\n{'='*60}")
        print(f"세트: {set_num}")
        print(f"{'='*60}")
        
        # 평가 수행
        evaluation_results, detailed_results, stats = evaluate_single_model(
            args.model_name, question_file, args.keyword_check_model, args.scoring_model, 
            set_num, best_answers_dict
        )
        
        if evaluation_results is None:
            continue
        
        # 통계 출력
        display_name = f"{args.model_name} (세트: {set_num})"
        print_statistics(stats, display_name)
        
        # 결과 저장
        output_dir = os.path.join(base_dir, 'evaluation_results')
        os.makedirs(output_dir, exist_ok=True)
        
        # 파일명 생성
        model_safe_name = args.model_name.replace("/", "_")
        set_suffix = f"_set{set_num}"
        
        # 상세 결과 저장
        detailed_output_file = os.path.join(output_dir, f'{model_safe_name}{set_suffix}_detailed_results.json')
        with open(detailed_output_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_results, f, ensure_ascii=False, indent=2)
        print(f"상세 결과 저장: {detailed_output_file}")
        
        # 통계 저장
        stats_output_file = os.path.join(output_dir, f'{model_safe_name}{set_suffix}_statistics.json')
        # JSON 직렬화를 위해 defaultdict를 dict로 변환
        stats_for_save = dict(stats)
        stats_for_save['keyword_avg_scores'] = dict(stats['keyword_avg_scores'])
        with open(stats_output_file, 'w', encoding='utf-8') as f:
            json.dump(stats_for_save, f, ensure_ascii=False, indent=2)
        print(f"통계 저장: {stats_output_file}")


if __name__ == '__main__':
    main()

