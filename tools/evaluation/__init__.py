#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evaluation 패키지 - 평가 관련 기능

이 패키지는 시험지 평가 기능을 제공합니다:
- MultipleChoiceEvaluator: 객관식 문제 평가 (O/X 문제 포함)
- evaluate_essay_answer: 서술형 문제 평가
"""

# 서술형 평가 함수들
from .evaluate_essay_model import (
    get_set_dir_name,
    evaluate_essay_answer,
    calculate_statistics,
    evaluate_single_model,
)

# 객관식 평가 클래스 및 함수들
try:
    from .multiple_eval_by_model import (
        MultipleChoiceEvaluator,
        run_eval_pipeline,
        load_data_from_directory,
        save_results_to_excel,
        print_evaluation_summary,
    )
except ImportError:
    MultipleChoiceEvaluator = None
    run_eval_pipeline = None
    load_data_from_directory = None
    save_results_to_excel = None
    print_evaluation_summary = None


__all__ = [
    # 객관식 평가
    'MultipleChoiceEvaluator',
    'run_eval_pipeline',
    'load_data_from_directory',
    'save_results_to_excel',
    'print_evaluation_summary',
    # 서술형 평가
    'get_set_dir_name',
    'evaluate_essay_answer',
    'calculate_statistics',
    'evaluate_single_model',
]
