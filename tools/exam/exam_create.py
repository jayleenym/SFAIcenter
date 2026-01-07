#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시험문제 생성 모듈
- 금융일반/금융심화/금융실무1/금융실무2 총 4개의 시험문제 파일 생성
- exam_config.json 파일 참고하여 domain/subdomain별 갯수 지정
- is_table=false, is_calculation=false 인 문제만 대상
"""

import os
import json
import random
import copy
from typing import Dict, Any, List, Tuple, Set, Optional
from tools.core.exam_config import ExamConfig
from tools.qna.extraction.tag_processor import TagProcessor


class ExamMaker:
    """시험문제 생성 클래스"""
    
    # 과목별 총 문제 수
    QUESTIONS_PER_EXAM = 1250
    
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

    def _is_valid_question(self, item: Dict[str, Any]) -> bool:
        """
        문제가 유효한지 확인 (is_table=false, is_calculation=false인 문제만 대상)
        
        Args:
            item: 문제 데이터
            
        Returns:
            유효한 문제인 경우 True
        """
        # is_calculation 확인 (문자열 "False" 또는 boolean False)
        is_calculation = item.get('is_calculation', False)
        if isinstance(is_calculation, str):
            is_calculation = is_calculation.lower() == 'true'
        
        # is_table 확인 (question에 {tb_ 패턴이 있는지)
        question = item.get('question', '')
        is_table = '{tb_' in question
        
        # 둘 다 False인 경우에만 유효
        return not is_calculation and not is_table

    def create_exams(self, seed: int = 42, debug: bool = False, random_mode: bool = False) -> Dict[str, Any]:
        """
        시험문제 생성 실행
        
        Args:
            seed: 랜덤 시드 값 (기본값: 42, 랜덤 모드에서만 사용)
            debug: 디버그 모드 (기존 파일 백업, 기본값: False)
            random_mode: 랜덤 모드 (True: exam_config.json 조건에 맞게 랜덤 선택, 
                                   False: exam_question_lists.json에서 문제 번호 로드)
        
        Returns:
            생성 결과 딕셔너리
        """
        # 랜덤 모드일 때만 seed 고정
        if random_mode:
            random.seed(seed)
        
        mode_str = f"랜덤 모드 (seed={seed})" if random_mode else "저장된 리스트 사용 모드"
        self.logger.info(f"=== 시험문제 만들기 (4개 과목, 각 {self.QUESTIONS_PER_EXAM}문제, {mode_str}) ===")
        
        try:
            # exam_config.json 로드
            try:
                exam_config = ExamConfig(onedrive_path=self.onedrive_path)
                exams_config = exam_config.get_exams_config()
                self.logger.info("exam_config.json 로드 완료")
            except Exception as e:
                self.logger.error(f"exam_config.json 파일 로드 실패: {e}")
                return {'success': False, 'error': f'설정 파일 로드 실패: {e}'}
            
            # 전체 데이터 로드
            all_data_file = os.path.join(
                self.onedrive_path,
                'evaluation', 'eval_data', '2_subdomain', 'multiple-choice_DST.json'
            )
            if not os.path.exists(all_data_file):
                return {'success': False, 'error': f'데이터 파일 없음: {all_data_file}'}
            
            with open(all_data_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            
            self.logger.info(f"전체 데이터 로딩 완료: {len(all_data)}개 문제")
            
            # 유효한 문제만 필터링 (is_table=false, is_calculation=false)
            valid_data = [item for item in all_data if self._is_valid_question(item)]
            self.logger.info(f"유효한 문제 (is_table=false, is_calculation=false): {len(valid_data)}개")
            
            # all_data를 (file_id, tag)로 인덱싱 (리스트 모드에서 빠른 검색용)
            all_data_index = {}
            for item in valid_data:
                file_id = item.get('file_id', '')
                tag = item.get('tag', '')
                if file_id and tag:
                    all_data_index[(file_id, tag)] = item
            
            used_questions = set()
            
            exam_dir = os.path.join(self.onedrive_path, 'evaluation', 'eval_data', '4_multiple_exam')
            os.makedirs(exam_dir, exist_ok=True)
            
            # 저장된 문제 번호 리스트 로드 (random_mode가 False일 때)
            question_lists = None
            if not random_mode:
                question_list_file = os.path.join(exam_dir, 'exam_question_lists.json')
                if os.path.exists(question_list_file):
                    try:
                        question_lists = self._load_question_lists(question_list_file)
                        self.logger.info(f"저장된 문제 번호 리스트 로드 완료: {question_list_file}")
                    except Exception as e:
                        self.logger.error(f"문제 번호 리스트 로드 실패: {e}")
                        return {'success': False, 'error': f'문제 번호 리스트 로드 실패: {e}'}
                else:
                    self.logger.error(f"문제 번호 리스트 파일을 찾을 수 없습니다: {question_list_file}")
                    return {'success': False, 'error': f'문제 번호 리스트 파일 없음: {question_list_file}'}
            
            results = {}
            
            # 각 과목별로 처리
            for exam_name, exam_info in exams_config.items():
                self.logger.info(f"\n{'='*50}")
                self.logger.info(f"과목: {exam_name}")
                
                if random_mode:
                    # 랜덤 모드: exam_config.json 조건에 맞게 subdomain별로 문제 랜덤 선택
                    exam_data = self._create_exam_random(
                        exam_name, exam_info, valid_data, used_questions
                    )
                else:
                    # 리스트 모드: exam_question_lists.json에서 문제 번호 로드
                    exam_data = self._create_exam_from_list(
                        exam_name, question_lists, all_data_index, used_questions
                    )
                
                if exam_data:
                    # 태그 대치 수행
                    exam_data_with_tags_replaced = self._replace_tags(exam_data)
                    
                    # 파일 저장
                    output_file = os.path.join(exam_dir, f'{exam_name}_exam.json')
                    
                    # debug 모드일 때는 기존 파일 백업
                    if debug and os.path.exists(output_file):
                        from datetime import datetime
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        backup_path = f"{output_file}.backup_{timestamp}"
                        try:
                            import shutil
                            shutil.copy2(output_file, backup_path)
                            self.logger.info(f"  기존 파일 백업: {backup_path}")
                        except Exception as e:
                            self.logger.warning(f"  백업 실패: {e}")
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(exam_data_with_tags_replaced, f, ensure_ascii=False, indent=4)
                    
                    self.logger.info(f"  저장 완료: {output_file} ({len(exam_data_with_tags_replaced)}개 문제)")
                    results[exam_name] = len(exam_data_with_tags_replaced)
                else:
                    self.logger.warning(f"  {exam_name}: 문제 생성 실패")
                    results[exam_name] = 0
            
            # 사용되지 않은 문제 저장
            self._save_remaining_questions(all_data, used_questions)
            
            # 랜덤 모드일 때 문제 번호 리스트 저장 (나중에 동일하게 재생성 가능하도록)
            if random_mode:
                self._save_question_lists(exam_dir, exams_config, valid_data, results)
            
            # 시험 통계 파일 생성
            self._save_exam_statistics(exam_dir, exams_config, results)
            
            return {
                'success': True,
                'total_questions': len(all_data),
                'valid_questions': len(valid_data),
                'used_questions': len(used_questions),
                'remaining_questions': len(valid_data) - len(used_questions),
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"시험문제 생성 중 오류 발생: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _load_question_lists(self, question_list_file: str) -> Dict[str, List[Dict[str, str]]]:
        """
        저장된 문제 번호 리스트 로드
        
        Args:
            question_list_file: 문제 번호 리스트 JSON 파일 경로
        
        Returns:
            {
                "금융일반": [{"file_id": "...", "tag": "..."}, ...],
                "금융심화": [...],
                ...
            }
        """
        with open(question_list_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_question_lists(self, exam_dir: str, exams_config: Dict[str, Any], 
                             valid_data: List[Dict], results: Dict[str, int]):
        """
        문제 번호 리스트 저장 (랜덤 모드로 생성 시 저장)
        
        Args:
            exam_dir: 시험 디렉토리 경로
            exams_config: 시험 설정
            valid_data: 유효한 문제 데이터
            results: 각 과목별 생성된 문제 수
        """
        question_lists = {}
        
        for exam_name in exams_config.keys():
            exam_file = os.path.join(exam_dir, f'{exam_name}_exam.json')
            if os.path.exists(exam_file):
                try:
                    with open(exam_file, 'r', encoding='utf-8') as f:
                        exam_data = json.load(f)
                    
                    question_ids = []
                    for question in exam_data:
                        file_id = question.get('file_id', '')
                        tag = question.get('tag', '')
                        if file_id and tag:
                            question_ids.append({
                                'file_id': file_id,
                                'tag': tag
                            })
                    
                    question_lists[exam_name] = question_ids
                    self.logger.info(f"  {exam_name}: {len(question_ids)}개 문제 번호 추출")
                except Exception as e:
                    self.logger.warning(f"  {exam_name} 문제 번호 추출 실패: {e}")
        
        # 저장
        output_file = os.path.join(exam_dir, 'exam_question_lists.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(question_lists, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"문제 번호 리스트 저장 완료: {output_file}")

    def _create_exam_random(self, exam_name: str, exam_info: Dict[str, Any], 
                            valid_data: List[Dict], used_questions: Set) -> List[Dict]:
        """
        랜덤 모드: exam_config.json 조건에 맞게 subdomain별로 문제 랜덤 선택
        
        Args:
            exam_name: 과목명 (금융일반/금융심화/금융실무1/금융실무2)
            exam_info: exam_config에서 가져온 과목 정보
            valid_data: 유효한 문제 데이터
            used_questions: 이미 사용된 문제 set
            
        Returns:
            선택된 문제 리스트
        """
        exam_data = []
        domain_details = exam_info.get('domain_details', {})
        
        for domain_name, domain_info in domain_details.items():
            subdomains = domain_info.get('subdomains', {})
            
            for subdomain_name, subdomain_info in subdomains.items():
                needed_count = subdomain_info.get('count', 0)
                
                # 해당 domain/subdomain의 미사용 문제 필터링
                available_questions = [
                    item for item in valid_data
                    if item.get('domain') == domain_name
                    and item.get('subdomain') == subdomain_name
                    and (item.get('file_id', ''), item.get('tag', '')) not in used_questions
                ]
                
                # 랜덤 섞기
                random.shuffle(available_questions)
                
                # 필요한 만큼 선택
                if len(available_questions) >= needed_count:
                    selected = available_questions[:needed_count]
                else:
                    selected = available_questions
                    if len(selected) < needed_count:
                        self.logger.warning(
                            f"  - {domain_name}/{subdomain_name}: 데이터 부족 "
                            f"(필요: {needed_count}, 가용: {len(selected)})"
                        )
                
                # 사용된 문제 등록
                for item in selected:
                    used_questions.add((item.get('file_id', ''), item.get('tag', '')))
                
                exam_data.extend(selected)
                self.logger.info(f"  - {domain_name}/{subdomain_name}: {len(selected)}/{needed_count}개 선택")
        
        self.logger.info(f"  총 {len(exam_data)}개 문제 선택 (목표: {self.QUESTIONS_PER_EXAM})")
        
        return exam_data

    def _create_exam_from_list(self, exam_name: str, question_lists: Dict[str, List[Dict[str, str]]], 
                                all_data_index: Dict, used_questions: Set) -> List[Dict]:
        """
        리스트 모드: exam_question_lists.json에서 문제 번호를 읽어서 해당 문제 로드
        
        Args:
            exam_name: 과목명
            question_lists: 저장된 문제 번호 리스트
            all_data_index: (file_id, tag) -> 문제 데이터 인덱스
            used_questions: 이미 사용된 문제 set
            
        Returns:
            선택된 문제 리스트
        """
        if exam_name not in question_lists:
            self.logger.error(f"  {exam_name}의 문제 번호 리스트를 찾을 수 없습니다.")
            return []
        
        exam_data = []
        question_ids = question_lists[exam_name]
        found_count = 0
        missing_count = 0
        
        for qid in question_ids:
            file_id = qid.get('file_id', '')
            tag = qid.get('tag', '')
            key = (file_id, tag)
            
            if key in all_data_index:
                item = all_data_index[key]
                exam_data.append(item)
                used_questions.add(key)
                found_count += 1
            else:
                missing_count += 1
                self.logger.warning(f"  문제를 찾을 수 없음: {file_id}_{tag}")
        
        self.logger.info(f"  {exam_name}: {found_count}개 문제 로드 (누락: {missing_count}개)")
        
        return exam_data

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
        """사용되지 않은 문제 저장 및 분류"""
        # 사용되지 않은 모든 문제 필터링
        remaining_data = [
            item for item in all_data 
            if (item.get('file_id', ''), item.get('tag', '')) not in used_questions
        ]
        
        exam_dir = os.path.join(
            self.onedrive_path,
            'evaluation', 'eval_data', '4_multiple_exam'
        )
        os.makedirs(exam_dir, exist_ok=True)
        
        # multiple_remaining.json 저장 (기존 로직)
        remaining_file = os.path.join(exam_dir, 'multiple_remaining.json')
        with open(remaining_file, 'w', encoding='utf-8') as f:
            json.dump(remaining_data, f, ensure_ascii=False, indent=4)
        self.logger.info(f"나머지 문제 저장 완료: {len(remaining_data)}개")
        
        # is_table = True인 문제들 분류
        table_data = []
        non_table_data = []
        
        for item in remaining_data:
            # is_table 확인 (question에 {tb_ 패턴이 있는지)
            question = item.get('question', '')
            is_table = '{tb_' in question
            
            if is_table:
                table_data.append(item)
            else:
                non_table_data.append(item)
        
        # multiple_table.json 저장
        if table_data:
            table_file = os.path.join(exam_dir, 'multiple_table.json')
            with open(table_file, 'w', encoding='utf-8') as f:
                json.dump(table_data, f, ensure_ascii=False, indent=4)
            self.logger.info(f"테이블 문제 저장 완료: {len(table_data)}개 -> {table_file}")
        
        # 그 외 문제들 중 is_calculation = True인 문제들 분류
        calculation_data = []
        for item in non_table_data:
            # is_calculation 확인 (문자열 "True" 또는 boolean True)
            is_calculation = item.get('is_calculation', False)
            if isinstance(is_calculation, str):
                is_calculation = is_calculation.lower() == 'true'
            
            if is_calculation:
                calculation_data.append(item)
        
        # multiple_calculation.json 저장
        if calculation_data:
            calculation_file = os.path.join(exam_dir, 'multiple_calculation.json')
            with open(calculation_file, 'w', encoding='utf-8') as f:
                json.dump(calculation_data, f, ensure_ascii=False, indent=4)
            self.logger.info(f"계산 문제 저장 완료: {len(calculation_data)}개 -> {calculation_file}")

    def _save_exam_statistics(self, exam_dir: str, exams_config: Dict[str, Any], results: Dict[str, int]):
        """
        시험 통계를 마크다운 파일로 저장
        
        Args:
            exam_dir: 시험 디렉토리 경로
            exams_config: exam_config.json에서 로드한 설정
            results: 각 과목별 생성된 문제 수
        """
        from datetime import datetime
        
        lines = []
        lines.append("# 시험문제 통계")
        lines.append("")
        lines.append(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 전체 요약
        total_questions = sum(results.values())
        total_target = self.QUESTIONS_PER_EXAM * len(exams_config)
        lines.append("## 전체 요약")
        lines.append("")
        lines.append("| 과목 | 문제 수 | 목표 | 달성률 |")
        lines.append("|------|--------|------|--------|")
        
        for exam_name in exams_config.keys():
            count = results.get(exam_name, 0)
            target = self.QUESTIONS_PER_EXAM
            rate = f"{count/target*100:.1f}%" if target > 0 else "N/A"
            lines.append(f"| {exam_name} | {count} | {target} | {rate} |")
        
        lines.append(f"| **합계** | **{total_questions}** | **{total_target}** | **{total_questions/total_target*100:.1f}%** |")
        lines.append("")
        
        # 과목별 상세 통계
        for exam_name, exam_info in exams_config.items():
            exam_file = os.path.join(exam_dir, f'{exam_name}_exam.json')
            if not os.path.exists(exam_file):
                continue
            
            try:
                with open(exam_file, 'r', encoding='utf-8') as f:
                    exam_data = json.load(f)
            except Exception as e:
                self.logger.warning(f"시험 파일 로드 실패 ({exam_name}): {e}")
                continue
            
            lines.append(f"## {exam_name}")
            lines.append("")
            lines.append(f"총 문제 수: {len(exam_data)}개")
            lines.append("")
            
            # Domain별 통계
            domain_stats = {}
            subdomain_stats = {}
            
            for item in exam_data:
                domain = item.get('domain', '알 수 없음')
                subdomain = item.get('subdomain', '알 수 없음')
                
                domain_stats[domain] = domain_stats.get(domain, 0) + 1
                key = f"{domain}/{subdomain}"
                subdomain_stats[key] = subdomain_stats.get(key, 0) + 1
            
            # exam_config에서 목표 개수 가져오기
            domain_details = exam_info.get('domain_details', {})
            
            lines.append("### Domain/Subdomain별 문제 분포")
            lines.append("")
            lines.append("| Domain | Subdomain | 실제 | 목표 | 상태 |")
            lines.append("|--------|-----------|------|------|------|")
            
            for domain_name, domain_info in domain_details.items():
                subdomains = domain_info.get('subdomains', {})
                for subdomain_name, subdomain_info in subdomains.items():
                    target_count = subdomain_info.get('count', 0)
                    key = f"{domain_name}/{subdomain_name}"
                    actual_count = subdomain_stats.get(key, 0)
                    
                    if actual_count >= target_count:
                        status = "✅"
                    elif actual_count > 0:
                        status = "⚠️ 부족"
                    else:
                        status = "❌ 없음"
                    
                    lines.append(f"| {domain_name} | {subdomain_name} | {actual_count} | {target_count} | {status} |")
            
            lines.append("")
            
            # Domain별 소계
            lines.append("### Domain별 소계")
            lines.append("")
            lines.append("| Domain | 문제 수 |")
            lines.append("|--------|--------|")
            
            for domain_name in sorted(domain_stats.keys()):
                lines.append(f"| {domain_name} | {domain_stats[domain_name]} |")
            
            lines.append("")
        
        # 마크다운 파일 저장
        output_file = os.path.join(exam_dir, 'STATS_exam.md')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        self.logger.info(f"시험 통계 파일 저장 완료: {output_file}")
