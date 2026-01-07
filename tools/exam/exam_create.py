#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시험문제 생성 모듈
- 1st/2nd/3rd/4th/5th 총 5세트의 시험문제를 만듬
- exam_config.json 파일 참고하여 갯수 지정
"""

import os
import json
import random
import copy
from typing import Dict, Any, List, Tuple, Set, Optional
from core.exam_config import ExamConfig
from exam.exam_validator import ExamValidator
from qna.extraction.tag_processor import TagProcessor
from exam.extract_exam_question_list import load_question_lists

class ExamMaker:
    """시험문제 생성 클래스"""
    
    def __init__(self, onedrive_path: str, logger: Any):
        self.onedrive_path = onedrive_path
        self.logger = logger
        self._extracted_qna_cache = {}
        
    def _find_extracted_qna_file(self, file_id: str) -> str:
        """file_id에 해당하는 _extracted_qna.json 파일 경로를 찾습니다."""
        workbook_base = os.path.join(self.onedrive_path, 'evaluation', 'workbook_data')
        for root, dirs, files in os.walk(workbook_base):
            for file in files:
                if file == f'{file_id}_extracted_qna.json':
                    return os.path.join(root, file)
        return None
    
    def _load_extracted_qna_item(self, file_id: str, tag: str) -> Dict[str, Any]:
        """_extracted_qna.json 파일에서 특정 file_id와 tag에 해당하는 항목을 로드합니다."""
        cache_key = file_id
        if cache_key not in self._extracted_qna_cache:
            extracted_qna_file = self._find_extracted_qna_file(file_id)
            if not extracted_qna_file:
                self.logger.debug(f"_extracted_qna.json 파일을 찾을 수 없음: {file_id}")
                return None
            try:
                with open(extracted_qna_file, 'r', encoding='utf-8') as f:
                    self._extracted_qna_cache[cache_key] = json.load(f)
            except Exception as e:
                self.logger.warning(f"_extracted_qna.json 파일 로드 실패 ({extracted_qna_file}): {e}")
                return None
        
        extracted_qna_data = self._extracted_qna_cache[cache_key]
        
        # 태그 정규화: 중괄호 제거하여 비교
        tag_normalized = tag.strip('{}') if tag else ''
        
        # _extracted_qna.json의 각 항목을 직접 확인
        for item in extracted_qna_data:
            # qna_data에서 tag 추출
            qna_data = item.get('qna_data', {})
            item_tag = qna_data.get('tag', '')
            
            # 태그 비교 (중괄호 제거하여 비교)
            item_tag_normalized = item_tag.strip('{}') if item_tag else ''
            
            if item_tag_normalized == tag_normalized:
                return item
        
        # 태그를 찾지 못한 경우 디버깅 정보 출력
        self.logger.debug(f"태그를 찾을 수 없음: file_id={file_id}, tag={tag}")
        if extracted_qna_data:
            sample_tags = [item.get('qna_data', {}).get('tag', '') for item in extracted_qna_data[:3]]
            self.logger.debug(f"  샘플 태그 (처음 3개): {sample_tags}")
        
        return None

    def create_exams(self, num_sets: int = 5, seed: int = 42, debug: bool = False, random_mode: bool = True) -> Dict[str, Any]:
        """
        시험문제 생성 실행
        
        Args:
            num_sets: 생성할 시험 세트 개수 (기본값: 5)
            seed: 랜덤 시드 값 (기본값: 42, 랜덤 모드에서만 사용)
            debug: 디버그 모드 (기존 파일 백업 및 활용, 기본값: False)
            random_mode: 랜덤 모드 (True: exam_config.json 조건에 맞게 랜덤 선택, 
                                   False: exam_question_lists.json에서 문제 번호 로드)
        """
        # 랜덤 모드일 때만 seed 고정
        if random_mode:
            random.seed(seed)
        
        mode_str = f"랜덤 모드 (seed={seed})" if random_mode else "저장된 리스트 사용 모드"
        self.logger.info(f"=== 시험문제 만들기 ({num_sets}세트, debug={debug}, {mode_str}) ===")
        
        try:
            set_names = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 5: '5th'}
            
            # exam_config.json 로드
            try:
                exam_config = ExamConfig(onedrive_path=self.onedrive_path)
                stats = exam_config.get_exam_statistics()
                self.logger.info("exam_config.json에서 통계 정보 로드 완료")
            except Exception as e:
                self.logger.error(f"exam_config.json 파일 로드 실패: {e}")
                return {'success': False, 'error': f'설정 파일 로드 실패: {e}'}
            
            # 전체 데이터 로드
            all_data_file = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '2_subdomain', 'multiple-choice_subdomain_classified_ALL.json'
            )
            if not os.path.exists(all_data_file):
                return {'success': False, 'error': f'데이터 파일 없음: {all_data_file}'}
            
            with open(all_data_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            
            self.logger.info(f"전체 데이터 로딩 완료: {len(all_data)}개 문제")
            used_questions = set()
            
            exam_dir = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '4_multiple_exam')
            os.makedirs(exam_dir, exist_ok=True)
            
            # all_data를 (file_id, tag)로 인덱싱 (리스트 모드에서 빠른 검색용)
            all_data_index = {}
            for item in all_data:
                file_id = item.get('file_id', '')
                tag = item.get('tag', '')
                if file_id and tag:
                    all_data_index[(file_id, tag)] = item
            
            # 저장된 문제 번호 리스트 로드 (random_mode가 False일 때)
            question_lists = None
            if not random_mode:
                question_list_file = os.path.join(exam_dir, 'exam_question_lists.json')
                if os.path.exists(question_list_file):
                    try:
                        question_lists = load_question_lists(question_list_file)
                        self.logger.info(f"저장된 문제 번호 리스트 로드 완료: {question_list_file}")
                    except Exception as e:
                        self.logger.error(f"문제 번호 리스트 로드 실패: {e}")
                        return {'success': False, 'error': f'문제 번호 리스트 로드 실패: {e}'}
                else:
                    self.logger.error(f"문제 번호 리스트 파일을 찾을 수 없습니다: {question_list_file}")
                    return {'success': False, 'error': f'문제 번호 리스트 파일 없음: {question_list_file}'}
            
            for exam_name in stats.keys():
                self._process_exam_subject(
                    exam_name, stats, num_sets, set_names, exam_dir, 
                    all_data, all_data_index, used_questions, debug, 
                    random_mode, question_lists
                )
            
            self._save_remaining_questions(all_data, used_questions)
            
            return {
                'success': True,
                'total_questions': len(all_data),
                'used_questions': len(used_questions),
                'remaining_questions': len(all_data) - len(used_questions)
            }
            
        except Exception as e:
            self.logger.error(f"시험문제 생성 중 오류 발생: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _process_exam_subject(self, exam_name: str, stats: Dict, num_sets: int, set_names: Dict, 
                            exam_dir: str, all_data: List[Dict], all_data_index: Dict, 
                            used_questions: Set, debug: bool = False,
                            random_mode: bool = False, question_lists: Optional[Dict[str, Dict[str, List[Dict[str, str]]]]] = None):
        """과목별 시험문제 처리"""
        self.logger.info(f"{'='*50}")
        self.logger.info(f"과목: {exam_name}")
        
        total_exam_questions = sum(stats[exam_name][d]['exam_questions'] for d in stats[exam_name].keys())
        
        sets_to_create = []
        sets_to_update = []
        existing_exams_data = {}
        
        for set_num in range(num_sets):
            set_dir = os.path.join(exam_dir, set_names[set_num+1])
            os.makedirs(set_dir, exist_ok=True)
            output_file = os.path.join(set_dir, f'{exam_name}_exam.json')
            
            # 랜덤 모드: 기존 파일 무시하고 무조건 새로 생성
            if random_mode:
                sets_to_create.append(set_num)
                self.logger.info(f"  ====> {set_names[set_num+1]}세트: 랜덤 모드 - 새로 생성 예정")
            elif os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_exam_data = json.load(f)
                
                meets_requirements, _ = ExamValidator.check_exam_meets_requirements(
                    existing_exam_data, exam_name, stats
                )
                
                if meets_requirements:
                    self.logger.info(f"  ====> {set_names[set_num+1]}세트: 요구사항 만족, 변경 없음")
                    for question in existing_exam_data:
                        used_questions.add((question.get('file_id', ''), question.get('tag', '')))
                else:
                    self.logger.info(f"  ====> {set_names[set_num+1]}세트: 요구사항 미만족, 업데이트 필요")
                    sets_to_update.append(set_num)
                    existing_exams_data[set_num] = existing_exam_data
            else:
                sets_to_create.append(set_num)
        
        if sets_to_create:
            self._create_new_sets(exam_name, stats, sets_to_create, set_names, exam_dir, all_data, all_data_index, used_questions, total_exam_questions, debug, random_mode, question_lists)
            
        if sets_to_update:
            self._update_sets(exam_name, stats, sets_to_update, set_names, exam_dir, existing_exams_data, all_data, all_data_index, used_questions, total_exam_questions, debug, random_mode, question_lists)

    def _create_new_sets(self, exam_name: str, stats: Dict, sets_to_create: List[int], set_names: Dict, 
                       exam_dir: str, all_data: List[Dict], all_data_index: Dict, used_questions: Set, 
                       total_exam_questions: int, debug: bool = False,
                       random_mode: bool = False, question_lists: Optional[Dict[str, Dict[str, List[Dict[str, str]]]]] = None):
        """새로운 세트 생성"""
        exam_data_sets = [[] for _ in range(len(set_names) + 1)]  # 1-based indexing support
        
        if random_mode:
            # 랜덤 모드: exam_config.json 조건에 맞게 subdomain별로 문제 랜덤 선택
            self._select_questions_random(exam_name, stats, sets_to_create, all_data, used_questions, exam_data_sets)
        else:
            # 리스트 모드: exam_question_lists.json에서 문제 번호 로드
            self._select_questions_from_list(exam_name, sets_to_create, set_names, question_lists, all_data_index, used_questions, exam_data_sets)

        # 각 세트 저장
        for set_num in sets_to_create:
            set_dir = os.path.join(exam_dir, set_names[set_num+1])
            output_file = os.path.join(set_dir, f'{exam_name}_exam.json')
            
            exam_data_with_tags_replaced = self._replace_tags(exam_data_sets[set_num])
            
            # debug 모드일 때는 기존 파일 백업
            if debug and os.path.exists(output_file):
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"{output_file}.backup_{timestamp}"
                try:
                    import shutil
                    shutil.copy2(output_file, backup_path)
                    self.logger.info(f"  ====> 기존 파일 백업: {backup_path}")
                except Exception as e:
                    self.logger.warning(f"  ====> 백업 실패: {e}")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(exam_data_with_tags_replaced, f, ensure_ascii=False, indent=4)
            self.logger.info(f"  ====> {set_names[set_num+1]}세트: 새로 생성 완료")
    
    def _select_questions_random(self, exam_name: str, stats: Dict, sets_to_process: List[int], 
                                  all_data: List[Dict], used_questions: Set, exam_data_sets: List[List[Dict]]):
        """
        랜덤 모드: exam_config.json 조건에 맞게 subdomain별로 문제 랜덤 선택
        
        Args:
            exam_name: 시험 과목명
            stats: exam_config에서 가져온 통계 정보
            sets_to_process: 처리할 세트 번호 리스트
            all_data: 전체 문제 데이터
            used_questions: 이미 사용된 문제 set
            exam_data_sets: 결과를 저장할 리스트
        """
        for domain in stats[exam_name].keys():
            domain_data = [d for d in all_data if d.get('domain') == domain]
            
            for subdomain, needed_count in stats[exam_name][domain]['exam_subdomain_distribution'].items():
                # 해당 subdomain의 미사용 문제만 필터링
                subdomain_data = [
                    d for d in domain_data 
                    if d.get('subdomain') == subdomain
                    and (d.get('file_id', ''), d.get('tag', '')) not in used_questions
                ]
                random.shuffle(subdomain_data)
                
                remaining_data = subdomain_data.copy()
                for set_num in sets_to_process:
                    if len(remaining_data) >= needed_count:
                        sample = random.sample(remaining_data, needed_count)
                        remaining_data = [d for d in remaining_data if d not in sample]
                    else:
                        sample = remaining_data[:needed_count] if remaining_data else []
                        remaining_data = remaining_data[needed_count:] if len(remaining_data) > needed_count else []
                        if len(sample) < needed_count:
                            self.logger.warning(f"  - {subdomain}: 데이터 부족 (필요: {needed_count}, 가용: {len(sample)})")
                    
                    for item in sample:
                        used_questions.add((item.get('file_id', ''), item.get('tag', '')))
                    exam_data_sets[set_num].extend(sample)
    
    def _select_questions_from_list(self, exam_name: str, sets_to_process: List[int], set_names: Dict,
                                     question_lists: Dict, all_data_index: Dict, used_questions: Set, 
                                     exam_data_sets: List[List[Dict]]):
        """
        리스트 모드: exam_question_lists.json에서 문제 번호를 읽어서 해당 문제 로드
        
        Args:
            exam_name: 시험 과목명
            sets_to_process: 처리할 세트 번호 리스트
            set_names: 세트 번호 -> 이름 매핑
            question_lists: 저장된 문제 번호 리스트
            all_data_index: (file_id, tag) -> 문제 데이터 인덱스
            used_questions: 이미 사용된 문제 set
            exam_data_sets: 결과를 저장할 리스트
        """
        for set_num in sets_to_process:
            set_name = set_names[set_num + 1]
            
            if set_name not in question_lists:
                self.logger.error(f"  {set_name} 세트의 문제 번호 리스트를 찾을 수 없습니다.")
                continue
            
            if exam_name not in question_lists[set_name]:
                self.logger.error(f"  {set_name}/{exam_name}의 문제 번호 리스트를 찾을 수 없습니다.")
                continue
            
            # 저장된 문제 번호 리스트에서 문제 가져오기
            question_ids = question_lists[set_name][exam_name]
            found_count = 0
            missing_count = 0
            
            for qid in question_ids:
                file_id = qid.get('file_id', '')
                tag = qid.get('tag', '')
                key = (file_id, tag)
                
                if key in all_data_index:
                    item = all_data_index[key]
                    exam_data_sets[set_num].append(item)
                    used_questions.add(key)
                    found_count += 1
                else:
                    missing_count += 1
                    self.logger.warning(f"  문제를 찾을 수 없음: {file_id}_{tag}")
            
            self.logger.info(f"  {set_name} 세트: {found_count}개 문제 로드 (누락: {missing_count}개)")

    def _update_sets(self, exam_name: str, stats: Dict, sets_to_update: List[int], set_names: Dict, 
                   exam_dir: str, existing_exams_data: Dict, all_data: List[Dict], all_data_index: Dict,
                   used_questions: Set, total_exam_questions: int, debug: bool = False,
                   random_mode: bool = False, question_lists: Optional[Dict[str, Dict[str, List[Dict[str, str]]]]] = None):
        """기존 세트 업데이트"""
        exam_data_sets = [[] for _ in range(len(set_names) + 1)]  # 1-based indexing support
        
        if random_mode:
            # 랜덤 모드: ExamValidator를 사용하여 기존 시험 업데이트
            for set_num in sets_to_update:
                existing_exam_data = existing_exams_data[set_num]
                updated_exam_data = ExamValidator.update_existing_exam(
                    existing_exam_data, exam_name, stats, all_data, used_questions, self.logger
                )
                exam_data_sets[set_num] = updated_exam_data
        else:
            # 리스트 모드: exam_question_lists.json에서 문제 번호 로드
            self._select_questions_from_list(exam_name, sets_to_update, set_names, question_lists, all_data_index, used_questions, exam_data_sets)
        
        # 각 세트 저장
        for set_num in sets_to_update:
            set_dir = os.path.join(exam_dir, set_names[set_num+1])
            output_file = os.path.join(set_dir, f'{exam_name}_exam.json')
            
            updated_exam_data_with_tags_replaced = self._replace_tags(exam_data_sets[set_num])
            
            # debug 모드일 때는 기존 파일 백업
            if debug and os.path.exists(output_file):
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"{output_file}.backup_{timestamp}"
                try:
                    import shutil
                    shutil.copy2(output_file, backup_path)
                    self.logger.info(f"  ====> 기존 파일 백업: {backup_path}")
                except Exception as e:
                    self.logger.warning(f"  ====> 백업 실패: {e}")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(updated_exam_data_with_tags_replaced, f, ensure_ascii=False, indent=4)
            self.logger.info(f"  ====> {set_names[set_num+1]}세트: 업데이트 완료")

    def _replace_tags(self, exam_data: List[Dict]) -> List[Dict]:
        """태그 대치 수행"""
        import re
        
        exam_data_with_tags_replaced = []
        replaced_count = 0
        not_found_count = 0
        no_tag_data_count = 0
        
        for item in exam_data:
            file_id = item.get('file_id', '')
            tag = item.get('tag', '')
            
            # 깊은 복사로 원본 데이터 보호
            item_copy = copy.deepcopy(item)
            
            # 태그 대치 전에 태그가 있는지 확인 (TagProcessor와 동일한 패턴 사용)
            tag_pattern = r'\{(f_\d{4}_\d{4}|tb_\d{4}_\d{4}|note_\d{4}_\d{4}|etc_\d{4}_\d{4})\}'
            has_tags_before = False
            qna_data = item_copy.get('qna_data', {})
            if 'description' in qna_data:
                desc = qna_data['description']
                content_fields = [
                    desc.get('question', ''),
                    desc.get('answer', ''),
                    desc.get('explanation', '')
                ]
                if desc.get('options'):
                    content_fields.extend(desc['options'] if isinstance(desc['options'], list) else [desc['options']])
                
                for field_content in content_fields:
                    if field_content and re.search(tag_pattern, str(field_content)):
                        has_tags_before = True
                        break
            
            extracted_qna_item = self._load_extracted_qna_item(file_id, tag)
            if extracted_qna_item:
                additional_tag_data = extracted_qna_item.get('additional_tag_data', [])
                if additional_tag_data:
                    # 태그 대치 수행
                    item_copy = TagProcessor.replace_tags_in_qna_data(item_copy, additional_tag_data)
                    
                    # 태그 대치 후 확인
                    has_tags_after = False
                    qna_data_after = item_copy.get('qna_data', {})
                    if 'description' in qna_data_after:
                        desc_after = qna_data_after['description']
                        content_fields_after = [
                            desc_after.get('question', ''),
                            desc_after.get('answer', ''),
                            desc_after.get('explanation', '')
                        ]
                        if desc_after.get('options'):
                            content_fields_after.extend(desc_after['options'] if isinstance(desc_after['options'], list) else [desc_after['options']])
                        
                        for field_content in content_fields_after:
                            if field_content and re.search(tag_pattern, str(field_content)):
                                has_tags_after = True
                                break
                    
                    if has_tags_before and not has_tags_after:
                        replaced_count += 1
                        self.logger.debug(f"태그 대치 성공: {file_id}_{tag}")
                    elif has_tags_before and has_tags_after:
                        self.logger.warning(f"태그 대치 후에도 태그가 남아있음: {file_id}_{tag}")
                else:
                    no_tag_data_count += 1
                    self.logger.debug(f"additional_tag_data 없음: {file_id}_{tag}")
            else:
                not_found_count += 1
                self.logger.warning(f"_extracted_qna.json에서 항목을 찾을 수 없음: {file_id}_{tag}")
            
            # additional_tag_data 필드 제거 (exam 파일에는 불필요)
            item_cleaned = {k: v for k, v in item_copy.items() if k != 'additional_tag_data'}
            exam_data_with_tags_replaced.append(item_cleaned)
        
        self.logger.info(f"태그 대치 완료: 성공={replaced_count}, 찾을 수 없음={not_found_count}, 태그데이터 없음={no_tag_data_count}, 전체={len(exam_data)}")
        return exam_data_with_tags_replaced

    def _save_remaining_questions(self, all_data: List[Dict], used_questions: Set):
        """사용되지 않은 문제 저장"""
        remaining_data = [
            item for item in all_data 
            if (item.get('file_id', ''), item.get('tag', '')) not in used_questions
        ]
        
        remaining_file = os.path.join(
            self.onedrive_path,
            'evaluation', 'eval_data', '4_multiple_exam', 'multiple_remaining.json'
        )
        os.makedirs(os.path.dirname(remaining_file), exist_ok=True)
        with open(remaining_file, 'w', encoding='utf-8') as f:
            json.dump(remaining_data, f, ensure_ascii=False, indent=4)
        self.logger.info(f"나머지 문제 저장 완료: {len(remaining_data)}개")
