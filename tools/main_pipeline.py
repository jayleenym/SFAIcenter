#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인 파이프라인 - 전체 프로세스 실행

단계:
  1. extract_qna_w_domain: 문제 추출 (Lv2, Lv3_4)
  2. create_exam: 시험문제 만들기 (5세트)
  3. transform_questions: 객관식 문제 변형
  4. create_transformed_exam: 변형 시험지 생성
  5. evaluate_exams: 시험지 평가
  6. evaluate_essay: 서술형 문제 평가
"""

import os
import sys
import argparse

# 프로젝트 루트 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, current_dir)

if __name__ == "__main__":
    from core.logger import setup_logger
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    logger = setup_logger(name=__name__, log_file=f'{script_name}.log', use_console=True, use_file=True)

from pipeline import Pipeline


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='전체 파이프라인 실행',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 1단계만 실행
  python main_pipeline.py --steps extract_qna_w_domain --cycle 1

  # 2단계 시험 생성 (랜덤 모드)
  python main_pipeline.py --steps create_exam --random

  # 5단계 평가 (기본)
  python main_pipeline.py --steps evaluate_exams --eval_models gpt-4 claude-3

  # 5단계 평가 (변형 시험지, vLLM 서버 모드)
  python main_pipeline.py --steps evaluate_exams --eval_exam_dir /path/to/exam --eval_models model_path --eval_use_server_mode --eval_batch_size 1 --transformed
        """
    )
    
    # === 기본 옵션 ===
    basic = parser.add_argument_group('기본 옵션')
    basic.add_argument('--steps', nargs='+',
                       choices=['extract_qna_w_domain', 'create_exam', 'transform_questions', 
                                'create_transformed_exam', 'evaluate_exams', 'evaluate_essay'],
                       help='실행할 단계 (미지정시 전체 실행)')
    basic.add_argument('--cycle', type=int, choices=[1, 2, 3],
                       help='사이클 번호 (1단계에서 사용)')
    basic.add_argument('--debug', action='store_true', help='디버그 모드')
    
    # === Q&A 추출 (1단계) ===
    extract = parser.add_argument_group('Q&A 추출 (extract_qna_w_domain)')
    extract.add_argument('--levels', nargs='+', choices=['Lv2', 'Lv3_4', 'Lv5'],
                         help='처리할 레벨 (미지정시 전체: Lv2, Lv3_4, Lv5)')
    extract.add_argument('--model', type=str, default='x-ai/grok-4-fast',
                         help='도메인 분류에 사용할 LLM 모델 (기본값: x-ai/grok-4-fast)')
    
    # === 경로 옵션 ===
    path = parser.add_argument_group('경로 옵션')
    path.add_argument('--config_path', type=str, help='LLM 설정 파일 경로')
    path.add_argument('--base_path', type=str, help='기본 데이터 경로')
    
    # === 시험 생성 (2단계) ===
    exam = parser.add_argument_group('시험 생성 (create_exam)')
    exam.add_argument('--num_sets', type=int, default=5, help='시험 세트 개수 (기본값: 5)')
    exam.add_argument('--random', action='store_true', help='랜덤 모드 (새로 문제 뽑기)')
    
    # === 문제 변형 (3단계) ===
    transform = parser.add_argument_group('문제 변형 (transform_questions)')
    transform.add_argument('--transform_data', type=str, dest='transform_classified_data_path',
                           help='분류된 데이터 파일 경로')
    transform.add_argument('--transform_classify', action='store_true', help='분류 단계 실행')
    transform.add_argument('--transform_input', type=str, dest='transform_input_data_path',
                           help='변형 입력 데이터 경로 (--transform_classify 사용시)')
    transform.add_argument('--transform_types', nargs='+', 
                           choices=['wrong_to_right', 'right_to_wrong', 'abcd'],
                           help='수행할 변형 종류')
    transform.add_argument('--transform_classify_model', type=str, default='openai/gpt-5',
                           help='분류에 사용할 모델 (기본값: openai/gpt-5)')
    transform.add_argument('--transform_classify_batch_size', type=int, default=10,
                           help='분류 배치 크기 (기본값: 10)')
    transform.add_argument('--transform_model', type=str, default='openai/o3',
                           help='변형에 사용할 모델 (기본값: openai/o3)')
    transform.add_argument('--transform_seed', type=int, default=42,
                           help='랜덤 시드 (기본값: 42)')
    
    # === 변형 시험지 생성 (4단계) ===
    trans_exam = parser.add_argument_group('변형 시험지 생성 (create_transformed_exam)')
    trans_exam.add_argument('--transformed_sets', type=int, nargs='+', choices=[1, 2, 3, 4, 5],
                            dest='create_transformed_exam_sets',
                            help='생성할 세트 번호 (미지정시 전체)')
    
    # === 평가 (5단계) ===
    evaluate = parser.add_argument_group('시험 평가 (evaluate_exams)')
    evaluate.add_argument('--eval_models', nargs='+', help='평가 모델 목록')
    evaluate.add_argument('--eval_sets', type=int, nargs='+', choices=[1, 2, 3, 4, 5],
                          help='평가할 세트 번호')
    evaluate.add_argument('--eval_transformed', '--transformed', action='store_true', 
                          dest='eval_transformed', help='변형 시험지 평가')
    evaluate.add_argument('--eval_server_mode', '--eval_use_server_mode', action='store_true', 
                          dest='eval_use_server_mode', help='vLLM 서버 모드')
    evaluate.add_argument('--eval_exam_dir', type=str,
                          help='시험지 디렉토리/파일 경로 (미지정시 기본 경로 사용)')
    evaluate.add_argument('--eval_batch_size', type=int, default=10,
                          help='평가 배치 크기 (기본값: 10)')
    evaluate.add_argument('--eval_use_ox_support', action='store_true', default=True,
                          help='O, X 문제 지원 활성화 (기본값: True)')
    evaluate.add_argument('--eval_no_ox_support', action='store_false', dest='eval_use_ox_support',
                          help='O, X 문제 지원 비활성화')
    evaluate.add_argument('--eval_essay', action='store_true',
                          help='서술형 평가(9_multiple_to_essay)도 함께 수행')
    
    # === 서술형 평가 (6단계) ===
    essay = parser.add_argument_group('서술형 평가 (evaluate_essay)')
    essay.add_argument('--essay_models', nargs='+', help='서술형 평가 모델 목록')
    essay.add_argument('--essay_sets', type=int, nargs='+', choices=[1, 2, 3, 4, 5],
                       help='처리할 세트 번호')
    essay.add_argument('--essay_server_mode', action='store_true', dest='essay_use_server_mode',
                       help='서술형 평가 vLLM 서버 모드')
    essay.add_argument('--essay_steps', type=int, nargs='+', choices=[1, 2, 3, 4, 5],
                       help='실행할 단계 번호 (1: 문제선별, 2: 시험분류, 3: 서술형변환, 4: 키워드추출, 5: 모범답안생성)')
    
    args = parser.parse_args()
    
    # 디버그 모드
    if args.debug:
        import logging
        for name in ['', 'pipeline', 'evaluation']:
            logging.getLogger(name).setLevel(logging.DEBUG)
    
    # config_path 절대 경로 변환
    config_path = args.config_path
    if config_path and not os.path.isabs(config_path):
        config_path = os.path.normpath(os.path.join(project_root, config_path))
    
    # transform_types 파싱
    transform_wrong_to_right = False
    transform_right_to_wrong = False
    transform_abcd = False
    if args.transform_types:
        transform_wrong_to_right = 'wrong_to_right' in args.transform_types
        transform_right_to_wrong = 'right_to_wrong' in args.transform_types
        transform_abcd = 'abcd' in args.transform_types
    
    # 파이프라인 실행
    pipeline = Pipeline(base_path=args.base_path, config_path=config_path)
    
    results = pipeline.run_full_pipeline(
        cycle=args.cycle,
        steps=args.steps,
        levels=args.levels,
        model=args.model,
        num_sets=args.num_sets,
        random_mode=args.random,
        eval_models=args.eval_models,
        eval_batch_size=args.eval_batch_size,
        eval_use_ox_support=args.eval_use_ox_support,
        eval_use_server_mode=args.eval_use_server_mode,
        eval_exam_dir=args.eval_exam_dir,
        eval_sets=args.eval_sets,
        eval_transformed=args.eval_transformed,
        eval_essay=args.eval_essay,
        transform_classified_data_path=args.transform_classified_data_path,
        transform_input_data_path=args.transform_input_data_path,
        transform_run_classify=args.transform_classify,
        transform_classify_model=args.transform_classify_model,
        transform_classify_batch_size=args.transform_classify_batch_size,
        transform_model=args.transform_model,
        transform_wrong_to_right=transform_wrong_to_right,
        transform_right_to_wrong=transform_right_to_wrong,
        transform_abcd=transform_abcd,
        transform_seed=args.transform_seed,
        create_transformed_exam_sets=args.create_transformed_exam_sets,
        essay_models=args.essay_models,
        essay_sets=args.essay_sets,
        essay_use_server_mode=args.essay_use_server_mode,
        essay_steps=args.essay_steps,
        debug=args.debug
    )
    
    if not results.get('success'):
        sys.exit(1)


if __name__ == "__main__":
    main()
