#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8_multiple_exam_+의 missing.json 문제들을 7_multiple_rw 프로세스에 태우기
- 기존 7_multiple_rw 결과물에 missing 문제들이 있는지 확인
- 없다면 분류하고 문제 변형
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Set

# 경로 설정 (직접 실행 시에도 작동하도록)
current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_dir = os.path.dirname(current_dir)  # pipeline/steps -> pipeline
tools_dir = os.path.dirname(pipeline_dir)  # pipeline -> tools
project_root = os.path.dirname(tools_dir)  # tools -> project root

# 경로 추가
sys.path.insert(0, tools_dir)
sys.path.insert(0, project_root)

# 독립 실행 시 파일명.log로 로깅 설정
if __name__ == "__main__":
    from core.logger import setup_logger
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    _standalone_logger = setup_logger(
        name=__name__,
        log_file=f'{script_name}.log',
        use_console=True,
        use_file=True
    )

# 상대 import 시도, 실패 시 절대 import
try:
    from ..pipeline.base import PipelineBase
    from ..pipeline.config import SFAICENTER_PATH
except ImportError:
    # 직접 실행 시 절대 import
    from pipeline.base import PipelineBase
    from pipeline.config import SFAICENTER_PATH

# AnswerTypeClassifier import
try:
    from qna.processing.answer_type_classifier import AnswerTypeClassifier
except ImportError:
    AnswerTypeClassifier = None

# Step7 import
try:
    from ..pipeline.steps.step7_transform_multiple_choice import Step7TransformMultipleChoice
except ImportError:
    try:
        from pipeline.steps.step7_transform_multiple_choice import Step7TransformMultipleChoice
    except ImportError:
        Step7TransformMultipleChoice = None


class ProcessMissingQuestions(PipelineBase):
    """missing 문제 처리 클래스"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        
        if AnswerTypeClassifier is None:
            self.logger.warning("AnswerTypeClassifier를 import할 수 없습니다.")
        
        if Step7TransformMultipleChoice is None:
            self.logger.warning("Step7TransformMultipleChoice를 import할 수 없습니다.")
    
    def execute(self, 
                classify_model: str = 'openai/gpt-5', 
                classify_batch_size: int = 10,
                transform_model: str = 'openai/o3',
                transform_wrong_to_right: bool = True,
                transform_right_to_wrong: bool = True,
                transform_abcd: bool = True,
                seed: int = 42,
                sets: List[int] = None) -> Dict[str, Any]:
        """
        missing 문제 처리 실행
        
        Args:
            classify_model: 분류에 사용할 모델
            classify_batch_size: 분류 배치 크기
            transform_model: 변형에 사용할 모델
            transform_wrong_to_right: wrong -> right 변형 수행 여부
            transform_right_to_wrong: right -> wrong 변형 수행 여부
            transform_abcd: abcd 변형 수행 여부
            seed: 랜덤 시드
            sets: 처리할 세트 리스트 (None이면 1~5 모두 처리)
        
        Returns:
            실행 결과
        """
        self.logger.info("=== missing 문제 처리 시작 ===")
        
        if self.llm_query is None:
            self.logger.error("LLMQuery가 초기화되지 않았습니다.")
            return {'success': False, 'error': 'LLMQuery 초기화 실패'}
        
        if AnswerTypeClassifier is None:
            self.logger.error("AnswerTypeClassifier를 import할 수 없습니다.")
            return {'success': False, 'error': 'AnswerTypeClassifier import 실패'}
        
        if Step7TransformMultipleChoice is None:
            self.logger.error("Step7TransformMultipleChoice를 import할 수 없습니다.")
            return {'success': False, 'error': 'Step7TransformMultipleChoice import 실패'}
        
        # 1. missing.json 파일들 수집
        self.logger.info("1단계: missing.json 파일 수집 중...")
        missing_questions = self._collect_missing_questions(sets)
        
        if not missing_questions:
            self.logger.warning("missing 문제가 없습니다.")
            return {'success': True, 'message': 'missing 문제 없음', 'total': 0}
        
        self.logger.info(f"총 {len(missing_questions)}개 missing 문제 수집")
        
        # 2. 기존 7_multiple_rw 결과물에서 이미 있는 문제 확인
        self.logger.info("2단계: 기존 7_multiple_rw 결과물 확인 중...")
        existing_question_ids = self._get_existing_question_ids()
        
        self.logger.info(f"기존 7_multiple_rw에 {len(existing_question_ids)}개 문제 존재")
        
        # 3. 없는 문제들만 필터링
        new_questions = []
        for q in missing_questions:
            question_id = q.get('file_id', '') + '_' + q.get('tag', '')
            if question_id not in existing_question_ids:
                new_questions.append(q)
        
        if not new_questions:
            self.logger.info("모든 missing 문제가 이미 7_multiple_rw에 존재합니다.")
            return {
                'success': True, 
                'message': '모든 missing 문제가 이미 존재함',
                'total': len(missing_questions),
                'existing': len(missing_questions),
                'new': 0
            }
        
        self.logger.info(f"새로운 missing 문제: {len(new_questions)}개 (기존: {len(missing_questions) - len(new_questions)}개)")
        
        # 4. 새로운 문제들 분류
        self.logger.info("3단계: 새로운 문제 분류 중...")
        # AnswerTypeClassifier가 이미 파일을 저장하므로, 기존 파일을 먼저 백업하고 병합
        classified_questions = self._classify_questions(new_questions, classify_model, classify_batch_size)
        
        if not classified_questions:
            self.logger.error("분류 실패")
            return {'success': False, 'error': '분류 실패'}
        
        # 5. 기존 분류 결과에 추가 (AnswerTypeClassifier가 이미 저장했지만, 기존 데이터와 병합)
        self.logger.info("4단계: 기존 분류 결과에 추가 중...")
        self._merge_classified_questions(classified_questions)
        
        # 6. 변형 수행
        self.logger.info("5단계: 문제 변형 시작...")
        step7 = Step7TransformMultipleChoice(
            config_path=None,  # 기본 경로 사용
            onedrive_path=self.onedrive_path,
            project_root_path=self.project_root_path
        )
        
        transform_results = step7.execute(
            classified_data_path=None,  # 기본 경로 사용
            run_classify=False,  # 이미 분류했으므로 False
            transform_model=transform_model,
            transform_wrong_to_right=transform_wrong_to_right,
            transform_right_to_wrong=transform_right_to_wrong,
            transform_abcd=transform_abcd,
            seed=seed
        )
        
        self.logger.info("=== missing 문제 처리 완료 ===")
        
        return {
            'success': True,
            'total_missing': len(missing_questions),
            'existing': len(missing_questions) - len(new_questions),
            'new': len(new_questions),
            'classified': len(classified_questions),
            'transform_results': transform_results
        }
    
    def _collect_missing_questions(self, sets: List[int] = None) -> List[Dict[str, Any]]:
        """8_multiple_exam_+의 모든 missing.json 파일에서 문제 수집"""
        if sets is None:
            sets = [1, 2, 3, 4, 5]
        
        exam_dir = os.path.join(
            self.onedrive_path,
            'evaluation', 'eval_data', '8_multiple_exam_+'
        )
        
        if not os.path.exists(exam_dir):
            self.logger.error(f"8_multiple_exam_+ 디렉토리가 없습니다: {exam_dir}")
            return []
        
        all_questions = []
        seen_ids = set()  # 중복 제거용
        
        # 세트 디렉토리 이름 매핑
        set_names = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 5: '5th'}
        
        for set_num in sets:
            set_name = set_names.get(set_num, f"{set_num}th")
            set_dir = os.path.join(exam_dir, set_name)
            
            if not os.path.exists(set_dir):
                self.logger.warning(f"세트 디렉토리가 없습니다: {set_dir}")
                continue
            
            # missing.json 파일들 찾기
            for file_name in os.listdir(set_dir):
                if file_name.endswith('_missing.json'):
                    file_path = os.path.join(set_dir, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            questions = json.load(f)
                            
                            if not isinstance(questions, list):
                                questions = [questions]
                            
                            for q in questions:
                                question_id = q.get('file_id', '') + '_' + q.get('tag', '')
                                if question_id not in seen_ids:
                                    seen_ids.add(question_id)
                                    all_questions.append(q)
                    
                    except Exception as e:
                        self.logger.warning(f"파일 로드 실패 ({file_path}): {e}")
        
        return all_questions
    
    def _get_existing_question_ids(self) -> Set[str]:
        """기존 7_multiple_rw 결과물에서 question_id 목록 추출"""
        question_ids = set()
        
        # answer_type_classified.json에서 확인
        classified_file = os.path.join(
            self.onedrive_path,
            'evaluation', 'eval_data', '7_multiple_rw', 'answer_type_classified.json'
        )
        
        if os.path.exists(classified_file):
            try:
                with open(classified_file, 'r', encoding='utf-8') as f:
                    classified_questions = json.load(f)
                    
                    if not isinstance(classified_questions, list):
                        classified_questions = [classified_questions]
                    
                    for q in classified_questions:
                        question_id = q.get('file_id', '') + '_' + q.get('tag', '')
                        if question_id:
                            question_ids.add(question_id)
            
            except Exception as e:
                self.logger.warning(f"분류된 파일 읽기 실패 ({classified_file}): {e}")
        
        # 변형 결과 파일들에서도 확인 (pick_right, pick_wrong, pick_abcd)
        result_dirs = [
            os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '7_multiple_rw', 'pick_right'),
            os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '7_multiple_rw', 'pick_wrong'),
            os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '7_multiple_rw', 'pick_abcd')
        ]
        
        for result_dir in result_dirs:
            if not os.path.exists(result_dir):
                continue
            
            # 하위 디렉토리 탐색 (2, 3, 4, 5 등)
            for subdir in os.listdir(result_dir):
                subdir_path = os.path.join(result_dir, subdir)
                if not os.path.isdir(subdir_path):
                    continue
                
                result_file = os.path.join(subdir_path, 'result.json')
                if os.path.exists(result_file):
                    try:
                        with open(result_file, 'r', encoding='utf-8') as f:
                            results = json.load(f)
                            
                            if not isinstance(results, list):
                                results = [results]
                            
                            for item in results:
                                if isinstance(item, dict):
                                    qid = item.get('question_id')
                                    if qid:
                                        question_ids.add(qid)
                    except Exception as e:
                        self.logger.warning(f"결과 파일 읽기 실패 ({result_file}): {e}")
            
            # 루트의 result.json도 확인 (pick_abcd의 경우)
            root_result_file = os.path.join(result_dir, 'result.json')
            if os.path.exists(root_result_file):
                try:
                    with open(root_result_file, 'r', encoding='utf-8') as f:
                        results = json.load(f)
                        
                        if not isinstance(results, list):
                            results = [results]
                        
                        for item in results:
                            if isinstance(item, dict):
                                qid = item.get('question_id')
                                if qid:
                                    question_ids.add(qid)
                except Exception as e:
                    self.logger.warning(f"결과 파일 읽기 실패 ({root_result_file}): {e}")
        
        return question_ids
    
    def _classify_questions(self, questions: List[Dict[str, Any]], 
                          model: str, batch_size: int) -> List[Dict[str, Any]]:
        """문제 분류"""
        classifier = AnswerTypeClassifier(
            config_path=os.path.join(self.project_root_path, 'llm_config.ini') if self.llm_query else None,
            onedrive_path=self.onedrive_path
        )
        
        classified_questions = classifier.process_all_questions(
            questions=questions,
            model=model,
            batch_size=batch_size
        )
        
        # 분류 결과 통계
        answer_type_counts = {}
        for item in classified_questions:
            answer_type = item.get('answer_type', 'unknown')
            answer_type_counts[answer_type] = answer_type_counts.get(answer_type, 0) + 1
        
        self.logger.info("분류 결과:")
        for answer_type, count in sorted(answer_type_counts.items()):
            self.logger.info(f"  {answer_type}: {count}")
        
        return classified_questions
    
    def _merge_classified_questions(self, new_classified_questions: List[Dict[str, Any]]):
        """새로 분류된 문제들을 기존 answer_type_classified.json에 병합"""
        classified_file = os.path.join(
            self.onedrive_path,
            'evaluation', 'eval_data', '7_multiple_rw', 'answer_type_classified.json'
        )
        
        # 기존 파일 로드
        existing_questions = []
        if os.path.exists(classified_file):
            try:
                with open(classified_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_questions = existing_data
                    else:
                        existing_questions = [existing_data]
            except Exception as e:
                self.logger.warning(f"기존 분류 파일 읽기 실패 ({classified_file}): {e}")
                existing_questions = []
        
        # 기존 question_id 추출
        existing_ids = set()
        for q in existing_questions:
            question_id = q.get('file_id', '') + '_' + q.get('tag', '')
            if question_id:
                existing_ids.add(question_id)
        
        # 새로운 문제들 추가 (중복 제거)
        added_count = 0
        for q in new_classified_questions:
            question_id = q.get('file_id', '') + '_' + q.get('tag', '')
            if question_id and question_id not in existing_ids:
                existing_questions.append(q)
                existing_ids.add(question_id)
                added_count += 1
        
        # 저장
        os.makedirs(os.path.dirname(classified_file), exist_ok=True)
        with open(classified_file, 'w', encoding='utf-8') as f:
            json.dump(existing_questions, f, ensure_ascii=False, indent=4)
        
        self.logger.info(f"기존 분류 파일에 {added_count}개 문제 추가 (총 {len(existing_questions)}개)")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='missing 문제 처리')
    parser.add_argument('--classify_model', type=str, default='openai/gpt-5',
                       help='분류에 사용할 모델 (기본값: openai/gpt-5)')
    parser.add_argument('--classify_batch_size', type=int, default=10,
                       help='분류 배치 크기 (기본값: 10)')
    parser.add_argument('--transform_model', type=str, default='openai/o3',
                       help='변형에 사용할 모델 (기본값: openai/o3)')
    # 변형 옵션: 기본값은 True, --no_* 옵션으로 비활성화 가능
    parser.add_argument('--no_transform_wrong_to_right', action='store_false', dest='transform_wrong_to_right',
                       default=True, help='wrong -> right 변형 비활성화 (기본값: 활성화)')
    parser.add_argument('--no_transform_right_to_wrong', action='store_false', dest='transform_right_to_wrong',
                       default=True, help='right -> wrong 변형 비활성화 (기본값: 활성화)')
    parser.add_argument('--no_transform_abcd', action='store_false', dest='transform_abcd',
                       default=True, help='abcd 변형 비활성화 (기본값: 활성화)')
    parser.add_argument('--seed', type=int, default=42,
                       help='랜덤 시드 (기본값: 42)')
    parser.add_argument('--sets', type=int, nargs='+', default=None,
                       help='처리할 세트 리스트 (예: 1 2 3, 기본값: 모두)')
    parser.add_argument('--config', type=str, default=None,
                       help='설정 파일 경로')
    parser.add_argument('--onedrive_path', type=str, default=None,
                       help='OneDrive 경로')
    
    args = parser.parse_args()
    
    # 처리기 초기화
    processor = ProcessMissingQuestions(
        config_path=args.config,
        onedrive_path=args.onedrive_path
    )
    
    # 실행
    try:
        results = processor.execute(
            classify_model=args.classify_model,
            classify_batch_size=args.classify_batch_size,
            transform_model=args.transform_model,
            transform_wrong_to_right=args.transform_wrong_to_right,
            transform_right_to_wrong=args.transform_right_to_wrong,
            transform_abcd=args.transform_abcd,
            seed=args.seed,
            sets=args.sets
        )
        
        if results.get('success'):
            print("\n처리 완료!")
            print(f"총 missing 문제: {results.get('total_missing', 0)}개")
            print(f"기존 문제: {results.get('existing', 0)}개")
            print(f"새로운 문제: {results.get('new', 0)}개")
            print(f"분류된 문제: {results.get('classified', 0)}개")
        else:
            print(f"\n처리 실패: {results.get('error', '알 수 없는 오류')}")
            sys.exit(1)
    
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

