#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8단계: 변형 문제를 포함한 시험지 생성
- 4_multiple_exam의 각 세트(1st~5th) 시험지의 객관식들을 pick_right, pick_wrong, pick_abcd result.json 파일에서 찾아서
- 각각 금융일반/금융심화/금융실무1/금융실무2_exam_transformed.json 파일로 만들어서 8_multiple_exam_+에 저장

변형 규칙:
1. 기존 시험지의 question, options, answer를 변형된 문제의 것으로 교체
2. 기존 시험지의 explanation을 original_explanation으로 키 이름 변경
3. 변형된 문제의 explanation을 explanation 키에 넣기
"""

import os
import json
import logging
from typing import Dict, List, Any, Tuple
from ..base import PipelineBase
from core.logger import setup_step_logger


class Step8CreateTransformedExam(PipelineBase):
    """8단계: 변형 문제를 포함한 시험지 생성"""
    
    def __init__(self, base_path: str = None, config_path: str = None, 
                 onedrive_path: str = None, project_root_path: str = None):
        super().__init__(base_path, config_path, onedrive_path, project_root_path)
        self._step_log_handler = None
    
    def execute(self, sets: List[int] = None) -> Dict[str, Any]:
        """
        8단계: 변형 문제를 포함한 시험지 생성
        
        Args:
            sets: 처리할 세트 번호 리스트 (None이면 1~5 모두 처리)
        """
        if sets is None:
            sets = [1, 2, 3, 4, 5]
        
        self.logger.info(f"=== 8단계: 변형 문제를 포함한 시험지 생성 (세트: {sets}) ===")
        
        # 로깅 설정
        self._setup_step_logging('create_transformed_exam')
        
        try:
            # 세트 이름 매핑
            set_names = {
                1: '1st',
                2: '2nd',
                3: '3rd',
                4: '4th',
                5: '5th'
            }
            
            # 변형된 문제들 로드
            self.logger.info("1. 변형된 문제 로드 중...")
            transformed_questions = self._load_transformed_questions()
            
            total_transformed = (
                len(transformed_questions['pick_abcd']) +
                len(transformed_questions['pick_right']) +
                len(transformed_questions['pick_wrong'])
            )
            self.logger.info(f"총 변형된 문제 수:")
            self.logger.info(f"  - pick_abcd: {len(transformed_questions['pick_abcd'])}개")
            self.logger.info(f"  - pick_right: {len(transformed_questions['pick_right'])}개")
            self.logger.info(f"  - pick_wrong: {len(transformed_questions['pick_wrong'])}개")
            self.logger.info(f"  - 총계: {total_transformed}개")
            
            # 시험지 파일 목록
            exam_files = {
                '금융일반': '금융일반_exam.json',
                '금융심화': '금융심화_exam.json',
                '금융실무1': '금융실무1_exam.json',
                '금융실무2': '금융실무2_exam.json'
            }
            
            # 각 세트별로 처리
            for set_num in sets:
                set_name = set_names.get(set_num, f"{set_num}th")
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"세트 {set_name} 처리 중...")
                self.logger.info(f"{'='*60}")
                
                # 원본 시험지 디렉토리
                original_exam_dir = os.path.join(
                    self.onedrive_path,
                    'evaluation', 'eval_data', '4_multiple_exam', set_name
                )
                
                # 출력 디렉토리
                output_dir = os.path.join(
                    self.onedrive_path,
                    'evaluation', 'eval_data', '8_multiple_exam_+', set_name
                )
                os.makedirs(output_dir, exist_ok=True)
                
                # 세트별 통계 수집용
                set_statistics = {}
                
                # 각 시험지 처리
                for exam_name, exam_filename in exam_files.items():
                    original_exam_path = os.path.join(original_exam_dir, exam_filename)
                    
                    if not os.path.exists(original_exam_path):
                        self.logger.warning(f"  ⚠️  원본 시험지를 찾을 수 없습니다: {original_exam_path}")
                        continue
                    
                    self.logger.info(f"\n  [{exam_name}] 처리 중...")
                    
                    # 원본 시험지 로드
                    original_exam = self.json_handler.load(original_exam_path)
                    if not isinstance(original_exam, list):
                        original_exam = []
                    self.logger.info(f"    원본 문제 수: {len(original_exam)}개")
                    
                    # 변형된 시험지 생성
                    transformed_exam, missing_questions, transform_stats = self._create_transformed_exam(
                        original_exam, transformed_questions
                    )
                    self.logger.info(f"    변형된 시험지 문제 수: {len(transformed_exam)}개")
                    
                    # 변형된 문제 개수 확인
                    transformed_count = 0
                    for q in transformed_exam:
                        file_id = q.get('file_id', '')
                        tag = q.get('tag', '')
                        if file_id and tag:
                            question_id = self._create_question_id(file_id, tag)
                            if (question_id in transformed_questions['pick_abcd'] or
                                question_id in transformed_questions['pick_right'] or
                                question_id in transformed_questions['pick_wrong']):
                                transformed_count += 1
                    
                    self.logger.info(f"    변형된 문제 수: {transformed_count}개")
                    self.logger.info(f"    변형되지 않은 문제 수: {len(missing_questions)}개")
                    
                    # 변형된 시험지 저장
                    output_filename = f"{exam_name}_exam_transformed.json"
                    output_path = os.path.join(output_dir, output_filename)
                    self.json_handler.save(transformed_exam, output_path)
                    self.logger.info(f"    ✅ 저장 완료: {output_path}")
                    
                    # 누락된 문제들 저장
                    if missing_questions:
                        missing_filename = f"{exam_name}_missing.json"
                        missing_path = os.path.join(output_dir, missing_filename)
                        self.json_handler.save(missing_questions, missing_path)
                        self.logger.info(f"    ✅ 누락된 문제 저장 완료: {missing_path}")
                    
                    # 통계를 메모리에 저장 (세트별 집계용)
                    set_statistics[exam_name] = transform_stats
                    self._log_statistics(transform_stats, exam_name)
                
                # 세트별 통계 집계 및 마크다운 생성
                self.logger.info(f"\n  세트 {set_name} 통계 집계 중...")
                set_stats = self._aggregate_set_statistics_from_memory(set_statistics)
                markdown_path = os.path.join(output_dir, f"STATS_{set_name}.md")
                self._save_statistics_markdown(set_stats, set_name, markdown_path)
                self.logger.info(f"    ✅ 세트 통계 마크다운 저장 완료: {markdown_path}")
            
            self.logger.info(f"\n{'='*60}")
            self.logger.info("완료!")
            self.logger.info(f"{'='*60}")
            
            # 로그 핸들러 제거
            self._remove_step_logging()
            
            return {'success': True, 'message': '변형 문제를 포함한 시험지 생성 완료'}
            
        except Exception as e:
            self.logger.error(f"오류 발생: {e}", exc_info=True)
            # 오류 발생 시에도 로그 핸들러 제거
            self._remove_step_logging()
            return {'success': False, 'error': str(e)}
    
    def _create_question_id(self, file_id: str, tag: str) -> str:
        """question_id 생성 (file_id_tag 형식)"""
        return f"{file_id}_{tag}"
    
    def _load_transformed_questions(self) -> Dict[str, Dict[str, Any]]:
        """
        pick_right, pick_wrong, pick_abcd의 result.json 파일들을 모두 로드하여
        question_id를 키로 하는 딕셔너리로 반환
        각 항목에 transform_type과 set_num 정보도 포함
        """
        transformed = {
            'pick_right': {},
            'pick_wrong': {},
            'pick_abcd': {}
        }
        
        # pick_abcd는 루트에 result.json이 있음
        abcd_path = os.path.join(
            self.onedrive_path,
            'evaluation', 'eval_data', '7_multiple_rw', 'pick_abcd', 'result.json'
        )
        if os.path.exists(abcd_path):
            abcd_data = self.json_handler.load(abcd_path)
            if not isinstance(abcd_data, list):
                abcd_data = []
            self.logger.info(f"pick_abcd: {len(abcd_data)}개 문제 로드")
            for item in abcd_data:
                file_id = item.get('file_id', '')
                tag = item.get('tag', '')
                if file_id and tag:
                    question_id = self._create_question_id(file_id, tag)
                    # 세트 정보 추가 (pick_abcd는 세트 정보 없음)
                    item_with_meta = item.copy()
                    item_with_meta['_transform_type'] = 'pick_abcd'
                    item_with_meta['_set_num'] = None
                    transformed['pick_abcd'][question_id] = item_with_meta
        
        # pick_right와 pick_wrong은 여러 세트 폴더에 있음 (2, 3, 4, 5)
        for transform_type in ['pick_right', 'pick_wrong']:
            transform_dir = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '7_multiple_rw', transform_type
            )
            if not os.path.exists(transform_dir):
                self.logger.warning(f"디렉토리를 찾을 수 없습니다: {transform_dir}")
                continue
            
            # 각 세트 폴더 확인 (2, 3, 4, 5)
            for set_num in [2, 3, 4, 5]:
                result_path = os.path.join(transform_dir, str(set_num), 'result.json')
                if os.path.exists(result_path):
                    data = self.json_handler.load(result_path)
                    if not isinstance(data, list):
                        data = []
                    self.logger.info(f"{transform_type}/{set_num}: {len(data)}개 문제 로드")
                    for item in data:
                        # question_id가 있으면 사용, 없으면 file_id와 tag로 생성
                        # pick_right와 pick_wrong 모두 file_id와 tag 구조로 통일됨
                        question_id = item.get('question_id', '')
                        if not question_id:
                            # file_id와 tag로 question_id 생성
                            file_id = item.get('file_id', '')
                            tag = item.get('tag', '')
                            if file_id and tag:
                                question_id = self._create_question_id(file_id, tag)
                        
                        if question_id:
                            # 세트 정보 추가
                            item_with_meta = item.copy()
                            item_with_meta['_transform_type'] = transform_type
                            item_with_meta['_set_num'] = set_num
                            # 이미 있으면 덮어쓰기 (나중 세트가 우선)
                            transformed[transform_type][question_id] = item_with_meta
        
        return transformed
    
    def _create_transformed_exam(self, original_exam: List[Dict[str, Any]], 
                                 transformed_questions: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        원본 시험지의 각 문제에 대해 변형된 문제를 찾아서 새로운 시험지 생성
        - 기존 시험지의 question, options, answer를 변형된 문제의 것으로 교체
        - 기존 시험지의 explanation을 original_explanation으로 키 이름 변경
        - 변형된 문제의 explanation을 explanation 키에 넣기
        
        Returns:
            tuple: (변형된 시험지, 변형되지 않은 문제 리스트, 통계 정보)
        """
        new_exam = []
        missing_questions = []  # 변형되지 않은 문제들
        
        # 통계 수집용
        stats = {
            'total_questions': len(original_exam),
            'transformed_count': 0,
            'not_transformed_count': 0,
            'pick_abcd': 0,
            'pick_right_2': 0,
            'pick_right_3': 0,
            'pick_right_4': 0,
            'pick_right_5': 0,
            'pick_wrong_2': 0,
            'pick_wrong_3': 0,
            'pick_wrong_4': 0,
            'pick_wrong_5': 0,
            'breakdown': {
                'pick_abcd': [],
                'pick_right_2': [],
                'pick_right_3': [],
                'pick_right_4': [],
                'pick_right_5': [],
                'pick_wrong_2': [],
                'pick_wrong_3': [],
                'pick_wrong_4': [],
                'pick_wrong_5': []
            }
        }
        
        for original_q in original_exam:
            file_id = original_q.get('file_id', '')
            tag = original_q.get('tag', '')
            
            if not file_id or not tag:
                # file_id나 tag가 없으면 원본 그대로 추가하고 누락으로 표시
                new_exam.append(original_q)
                missing_questions.append(original_q)
                stats['not_transformed_count'] += 1
                continue
            
            question_id = self._create_question_id(file_id, tag)
            
            # 변형된 문제 찾기 (우선순위: pick_abcd > pick_right > pick_wrong)
            transformed_q = None
            transform_type = None
            set_num = None
            
            if question_id in transformed_questions['pick_abcd']:
                transformed_q = transformed_questions['pick_abcd'][question_id]
                transform_type = 'pick_abcd'
                set_num = transformed_q.get('_set_num')
            elif question_id in transformed_questions['pick_right']:
                transformed_q = transformed_questions['pick_right'][question_id]
                transform_type = 'pick_right'
                set_num = transformed_q.get('_set_num')
            elif question_id in transformed_questions['pick_wrong']:
                transformed_q = transformed_questions['pick_wrong'][question_id]
                transform_type = 'pick_wrong'
                set_num = transformed_q.get('_set_num')
            
            # 새로운 문제 객체 생성 (원본의 모든 필드를 복사)
            new_q = original_q.copy()
            
            if transformed_q:
                # 변형된 문제가 있으면 question, options, answer 교체
                new_q['question'] = transformed_q.get('question', original_q.get('question', ''))
                new_q['options'] = transformed_q.get('options', original_q.get('options', []))
                new_q['answer'] = transformed_q.get('answer', original_q.get('answer', ''))
                
                # explanation 처리
                # 기존 시험지의 explanation을 original_explanation으로
                original_explanation = original_q.get('explanation', '')
                if original_explanation:
                    new_q['original_explanation'] = original_explanation
                
                # 변형된 문제의 explanation을 explanation으로
                transformed_explanation = transformed_q.get('explanation', '')
                if transformed_explanation:
                    new_q['explanation'] = transformed_explanation
                elif 'explanation' in new_q:
                    # 변형된 문제에 explanation이 없으면 원본 유지
                    pass
                
                # 통계 업데이트
                stats['transformed_count'] += 1
                stat_key = None
                if transform_type == 'pick_abcd':
                    stats['pick_abcd'] += 1
                    stat_key = 'pick_abcd'
                elif transform_type == 'pick_right' and set_num:
                    stats[f'pick_right_{set_num}'] += 1
                    stat_key = f'pick_right_{set_num}'
                elif transform_type == 'pick_wrong' and set_num:
                    stats[f'pick_wrong_{set_num}'] += 1
                    stat_key = f'pick_wrong_{set_num}'
                
                # breakdown에 question_id 추가
                if stat_key and stat_key in stats['breakdown']:
                    stats['breakdown'][stat_key].append(question_id)
            else:
                # 변형된 문제가 없으면 원본 그대로 (explanation은 그대로 유지)
                missing_questions.append(original_q)
                stats['not_transformed_count'] += 1
            
            new_exam.append(new_q)
        
        return new_exam, missing_questions, stats
    
    def _setup_step_logging(self, step_name: str):
        """단계별 로그 파일 설정"""
        step_logger, file_handler = setup_step_logger(
            step_name=step_name,
            step_number=8
        )
        # 이전 핸들러 제거 (중복 방지)
        if self._step_log_handler:
            self.logger.removeHandler(self._step_log_handler)
        
        # 기존 로거에 핸들러 추가
        self.logger.addHandler(file_handler)
        self._step_log_handler = file_handler
    
    def _remove_step_logging(self):
        """단계별 로그 파일 핸들러 제거"""
        if self._step_log_handler:
            self.logger.removeHandler(self._step_log_handler)
            self._step_log_handler.close()
            self._step_log_handler = None
    
    def _log_statistics(self, stats: Dict[str, Any], exam_name: str):
        """통계 정보를 로그로 출력"""
        self.logger.info(f"\n    [{exam_name}] 변형 통계:")
        self.logger.info(f"      총 문제 수: {stats['total_questions']}개")
        self.logger.info(f"      변형된 문제: {stats['transformed_count']}개")
        self.logger.info(f"      변형되지 않은 문제: {stats['not_transformed_count']}개")
        self.logger.info(f"      - pick_abcd: {stats['pick_abcd']}개")
        self.logger.info(f"      - pick_right_2: {stats['pick_right_2']}개")
        self.logger.info(f"      - pick_right_3: {stats['pick_right_3']}개")
        self.logger.info(f"      - pick_right_4: {stats['pick_right_4']}개")
        self.logger.info(f"      - pick_right_5: {stats['pick_right_5']}개")
        self.logger.info(f"      - pick_wrong_2: {stats['pick_wrong_2']}개")
        self.logger.info(f"      - pick_wrong_3: {stats['pick_wrong_3']}개")
        self.logger.info(f"      - pick_wrong_4: {stats['pick_wrong_4']}개")
        self.logger.info(f"      - pick_wrong_5: {stats['pick_wrong_5']}개")
    
    def _aggregate_set_statistics_from_memory(self, set_statistics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        메모리의 모든 시험지 통계를 집계
        
        Args:
            set_statistics: 시험지별 통계 딕셔너리
            
        Returns:
            집계된 통계 정보
        """
        aggregated = {
            'total_questions': 0,
            'transformed_count': 0,
            'not_transformed_count': 0,
            'pick_abcd': 0,
            'pick_right_2': 0,
            'pick_right_3': 0,
            'pick_right_4': 0,
            'pick_right_5': 0,
            'pick_wrong_2': 0,
            'pick_wrong_3': 0,
            'pick_wrong_4': 0,
            'pick_wrong_5': 0,
            'by_exam': {}
        }
        
        for exam_name, stats in set_statistics.items():
            aggregated['by_exam'][exam_name] = stats
            
            # 집계
            aggregated['total_questions'] += stats.get('total_questions', 0)
            aggregated['transformed_count'] += stats.get('transformed_count', 0)
            aggregated['not_transformed_count'] += stats.get('not_transformed_count', 0)
            aggregated['pick_abcd'] += stats.get('pick_abcd', 0)
            aggregated['pick_right_2'] += stats.get('pick_right_2', 0)
            aggregated['pick_right_3'] += stats.get('pick_right_3', 0)
            aggregated['pick_right_4'] += stats.get('pick_right_4', 0)
            aggregated['pick_right_5'] += stats.get('pick_right_5', 0)
            aggregated['pick_wrong_2'] += stats.get('pick_wrong_2', 0)
            aggregated['pick_wrong_3'] += stats.get('pick_wrong_3', 0)
            aggregated['pick_wrong_4'] += stats.get('pick_wrong_4', 0)
            aggregated['pick_wrong_5'] += stats.get('pick_wrong_5', 0)
        
        return aggregated
    
    def _save_statistics_markdown(self, stats: Dict[str, Any], set_name: str, output_path: str):
        """
        통계 정보를 마크다운 형식으로 저장
        
        Args:
            stats: 집계된 통계 정보
            set_name: 세트 이름 (예: '1st', '2nd')
            output_path: 출력 파일 경로
        """
        lines = []
        lines.append(f"# {set_name} 세트 변형 통계")
        lines.append("")
        lines.append("## 전체 요약")
        lines.append("")
        lines.append("| 항목 | 개수 |")
        lines.append("|------|------|")
        lines.append(f"| 총 문제 수 | {stats['total_questions']} |")
        lines.append(f"| 변형된 문제 | {stats['transformed_count']} |")
        lines.append(f"| 변형되지 않은 문제 | {stats['not_transformed_count']} |")
        lines.append("")
        
        lines.append("## 변형 타입별 통계")
        lines.append("")
        lines.append("| 변형 타입 | 개수 |")
        lines.append("|----------|------|")
        lines.append(f"| pick_abcd | {stats['pick_abcd']} |")
        lines.append(f"| pick_right_2 | {stats['pick_right_2']} |")
        lines.append(f"| pick_right_3 | {stats['pick_right_3']} |")
        lines.append(f"| pick_right_4 | {stats['pick_right_4']} |")
        lines.append(f"| pick_right_5 | {stats['pick_right_5']} |")
        lines.append(f"| pick_wrong_2 | {stats['pick_wrong_2']} |")
        lines.append(f"| pick_wrong_3 | {stats['pick_wrong_3']} |")
        lines.append(f"| pick_wrong_4 | {stats['pick_wrong_4']} |")
        lines.append(f"| pick_wrong_5 | {stats['pick_wrong_5']} |")
        lines.append("")
        
        # pick_right 합계
        pick_right_total = stats['pick_right_2'] + stats['pick_right_3'] + stats['pick_right_4'] + stats['pick_right_5']
        # pick_wrong 합계
        pick_wrong_total = stats['pick_wrong_2'] + stats['pick_wrong_3'] + stats['pick_wrong_4'] + stats['pick_wrong_5']
        
        lines.append("### 변형 타입별 합계")
        lines.append("")
        lines.append("| 변형 타입 | 개수 |")
        lines.append("|----------|------|")
        lines.append(f"| pick_abcd | {stats['pick_abcd']} |")
        lines.append(f"| pick_right (전체) | {pick_right_total} |")
        lines.append(f"| pick_wrong (전체) | {pick_wrong_total} |")
        lines.append("")
        
        lines.append("## 시험지별 상세 통계")
        lines.append("")
        
        for exam_name, exam_stats in stats['by_exam'].items():
            lines.append(f"### {exam_name}")
            lines.append("")
            lines.append("| 항목 | 개수 |")
            lines.append("|------|------|")
            lines.append(f"| 총 문제 수 | {exam_stats.get('total_questions', 0)} |")
            lines.append(f"| 변형된 문제 | {exam_stats.get('transformed_count', 0)} |")
            lines.append(f"| 변형되지 않은 문제 | {exam_stats.get('not_transformed_count', 0)} |")
            lines.append("")
            lines.append("| 변형 타입 | 개수 |")
            lines.append("|----------|------|")
            lines.append(f"| pick_abcd | {exam_stats.get('pick_abcd', 0)} |")
            lines.append(f"| pick_right_2 | {exam_stats.get('pick_right_2', 0)} |")
            lines.append(f"| pick_right_3 | {exam_stats.get('pick_right_3', 0)} |")
            lines.append(f"| pick_right_4 | {exam_stats.get('pick_right_4', 0)} |")
            lines.append(f"| pick_right_5 | {exam_stats.get('pick_right_5', 0)} |")
            lines.append(f"| pick_wrong_2 | {exam_stats.get('pick_wrong_2', 0)} |")
            lines.append(f"| pick_wrong_3 | {exam_stats.get('pick_wrong_3', 0)} |")
            lines.append(f"| pick_wrong_4 | {exam_stats.get('pick_wrong_4', 0)} |")
            lines.append(f"| pick_wrong_5 | {exam_stats.get('pick_wrong_5', 0)} |")
            lines.append("")
        
        # 마크다운 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

