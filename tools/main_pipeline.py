#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인 파이프라인 - 전체 프로세스 실행

전체 프로세스:
0. 텍스트 전처리 (Lv2 폴더) - 문장내 엔터 제거, 빈 챕터정보 채우기, 문단 병합(안함), 선지 텍스트 정규화
1. 문제 추출 (Lv2, Lv3_4) - 문제/선지/정답/해설 추출 및 포맷화
2. 전체 문제 추출 (Lv3, Lv3_4, Lv5) - 태그들을 재귀로 돌면서 전체 대치 시키고 ~_extracted_qna.json으로 저장
3. qna_type별 분류 - multiple/short/essay/etc로 분류 및 필터링
4. domain/subdomain/classification_reason/is_calculation 빈칸 채우기 - openrouter 사용, 실패한 것들은 따로 저장해서 재처리
5. 시험문제 만들기 - 5세트의 시험문제를 exam_statistics.json 참고하여 만들기
6. 시험지 평가 - 만들어진 시험지(1st/2nd/3rd/4th/5th) 모델별 답변 평가 (10문제씩 배치화하여 호출)
"""

import os
import sys
import argparse
from pathlib import Path

# 프로젝트 루트 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from pipeline import Pipeline


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='전체 파이프라인 실행')
    parser.add_argument('--cycle', type=int, default=None, choices=[1, 2, 3],
                       help='사이클 번호 (1, 2, 3) - 0, 1, 2, 3단계에서만 필요')
    parser.add_argument('--steps', nargs='+',
                       choices=['preprocess', 'extract_basic', 'extract_full', 'classify', 'fill_domain', 'create_exam', 'evaluate_exams'],
                       default=None,
                       help='실행할 단계 (기본값: 전체 실행)')
    parser.add_argument('--base_path', type=str, default=None, 
                       help='기본 데이터 경로 (None이면 ONEDRIVE_PATH 사용)')
    parser.add_argument('--config_path', type=str, default=None, 
                       help='LLM 설정 파일 경로 (None이면 PROJECT_ROOT_PATH/llm_config.ini 사용)')
    parser.add_argument('--onedrive_path', type=str, default=None,
                       help='OneDrive 경로 (None이면 자동 감지 또는 환경 변수 사용)')
    parser.add_argument('--project_root_path', type=str, default=None,
                       help='프로젝트 루트 경로 (None이면 자동 감지 또는 환경 변수 사용)')
    parser.add_argument('--qna_type', type=str, default='multiple',
                       choices=['multiple', 'short', 'essay'],
                       help='QnA 타입 (4단계에서 사용)')
    parser.add_argument('--model', type=str, default='x-ai/grok-4-fast',
                       help='사용할 모델 (4단계에서 사용)')
    parser.add_argument('--num_sets', type=int, default=5,
                       help='시험 세트 개수 (5단계에서 사용)')
    parser.add_argument('--eval_models', nargs='+',
                       default=None,
                       help='평가할 모델 목록 (6단계에서 사용, 기본값: 자동 설정)')
    parser.add_argument('--eval_batch_size', type=int, default=10,
                       help='평가 배치 크기 (6단계에서 사용, 기본값: 10)')
    parser.add_argument('--eval_use_ox_support', action='store_true', default=True,
                       help='O, X 문제 지원 활성화 (6단계에서 사용)')
    parser.add_argument('--eval_use_server_mode', action='store_true',
                       help='vLLM 서버 모드 사용 (6단계에서 사용)')
    parser.add_argument('--eval_reasoning', action='store_true',
                       help='추론 모델 여부 (6단계에서 사용)')
    parser.add_argument('--eval_exam_dir', type=str, default=None,
                       help='시험지 디렉토리 경로 (6단계에서 사용, None이면 기본 경로 사용)')
    parser.add_argument('--eval_sets', type=int, nargs='+', default=None,
                       choices=[1, 2, 3, 4, 5],
                       help='평가할 세트 번호 (6단계에서 사용, 예: --eval_sets 1 또는 --eval_sets 1 2 3, None이면 모든 세트 평가)')
    parser.add_argument('--debug', action='store_true',
                       help='디버그 로그 활성화')
    
    args = parser.parse_args()
    
    # 디버그 모드 설정
    if args.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        # pipeline 모듈의 로거도 DEBUG 레벨로 설정
        logging.getLogger('pipeline').setLevel(logging.DEBUG)
        logging.getLogger('evaluation').setLevel(logging.DEBUG)
    
    # 파이프라인 실행
    pipeline = Pipeline(
        base_path=args.base_path,
        config_path=args.config_path,
        onedrive_path=args.onedrive_path,
        project_root_path=args.project_root_path
    )
    
    results = pipeline.run_full_pipeline(
        cycle=args.cycle,
        steps=args.steps,
        qna_type=args.qna_type,
        model=args.model,
        num_sets=args.num_sets,
        eval_models=args.eval_models,
        eval_batch_size=args.eval_batch_size,
        eval_use_ox_support=args.eval_use_ox_support,
        eval_use_server_mode=args.eval_use_server_mode,
        eval_reasoning=args.eval_reasoning,
        eval_exam_dir=args.eval_exam_dir,
        eval_sets=args.eval_sets
    )
    
    # 결과 출력
    print("\n=== 실행 결과 ===")
    print(f"성공: {results.get('success', False)}")
    
    for step_name, step_result in results.items():
        if step_name != 'success' and step_name != 'error':
            print(f"\n{step_name}: {step_result.get('success', False)}")
            if step_result.get('success'):
                if 'processed_files' in step_result:
                    print(f"  - 처리된 파일: {step_result['processed_files']}개")
                if 'total_extracted' in step_result:
                    print(f"  - 추출된 Q&A: {step_result['total_extracted']}개")
    
    if not results.get('success'):
        print(f"\n오류: {results.get('error', '알 수 없는 오류')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
