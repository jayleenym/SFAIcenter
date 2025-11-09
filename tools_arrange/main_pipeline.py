#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인 파이프라인 - 전체 프로세스 실행
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# 프로젝트 루트 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from core.utils import FileManager, TextProcessor, JSONHandler
from core.llm_query import LLMQuery
from data_processing.json_cleaner import JSONCleaner
from qna.qna_processor import QnAExtractor, TagProcessor, QnATypeClassifier


class Pipeline:
    """메인 파이프라인 클래스"""
    
    def __init__(self, base_path: str = None, config_path: str = None):
        """
        Args:
            base_path: 기본 데이터 경로
            config_path: LLM 설정 파일 경로
        """
        self.file_manager = FileManager(base_path)
        self.text_processor = TextProcessor()
        self.json_handler = JSONHandler()
        self.json_cleaner = JSONCleaner()
        self.llm_query = LLMQuery(config_path) if config_path else None
        
        # 로깅 설정
        self._setup_logging()
    
    def _setup_logging(self):
        """로깅 설정"""
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file, encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def step1_cleanup_empty_pages(self, cycle: int, data_path: str = None) -> Dict[str, Any]:
        """1단계: 빈 페이지 제거"""
        self.logger.info(f"=== 1단계: 빈 페이지 제거 (Cycle {cycle}) ===")
        
        if data_path is None:
            data_path = self.file_manager.final_data_path
        
        final_path = os.path.join(data_path, self.file_manager.cycle_path[cycle])
        
        if not os.path.exists(final_path):
            self.logger.error(f"경로가 존재하지 않습니다: {final_path}")
            return {'success': False, 'error': f'경로 없음: {final_path}'}
        
        result = self.json_cleaner.cleanup_directory(Path(final_path))
        
        self.logger.info(f"처리 완료: {result['processed_files']}개 파일, {result['total_removed']}개 페이지 제거")
        return {'success': True, 'result': result}
    
    def step2_extract_qna(self, cycle: int, data_path: str = None, output_path: str = None) -> Dict[str, Any]:
        """2단계: Q&A 추출"""
        self.logger.info(f"=== 2단계: Q&A 추출 (Cycle {cycle}) ===")
        
        if data_path is None:
            data_path = self.file_manager.final_data_path
        
        if output_path is None:
            output_path = os.path.join(
                self.file_manager.base_path,
                f'evaluation/workbook_data/{self.file_manager.cycle_path[cycle]}/Lv5'
            )
        
        json_files = self.file_manager.get_filelist(cycle, data_path)
        json_files = [f for f in json_files if 'Lv5' in f]
        
        self.logger.info(f"총 {len(json_files)}개의 JSON 파일을 찾았습니다.")
        
        extractor = QnAExtractor(self.file_manager)
        total_extracted = 0
        processed_files = 0
        
        for i, json_file in enumerate(json_files, 1):
            try:
                self.logger.info(f"[{i}/{len(json_files)}] 처리 중: {os.path.basename(json_file)}")
                
                file_name = os.path.splitext(os.path.basename(json_file))[0]
                file_output_path = os.path.join(output_path, f"{file_name}.json")
                
                result = extractor.extract_from_file(json_file, file_output_path)
                
                total_extracted += len(result['extracted_qna'])
                processed_files += 1
                
                self.logger.info(f"추출된 Q&A: {len(result['extracted_qna'])}개")
                
            except Exception as e:
                self.logger.error(f"파일 처리 오류 ({os.path.basename(json_file)}): {e}")
        
        self.logger.info(f"처리 완료: {processed_files}개 파일, {total_extracted}개 Q&A 추출")
        return {
            'success': True,
            'processed_files': processed_files,
            'total_extracted': total_extracted
        }
    
    def step3_process_tags(self, cycle: int) -> Dict[str, Any]:
        """3단계: 태그 처리"""
        self.logger.info(f"=== 3단계: 태그 처리 (Cycle {cycle}) ===")
        
        extracted_dir = os.path.join(
            self.file_manager.base_path,
            f'evaluation/workbook_data/{self.file_manager.cycle_path[cycle]}/Lv5'
        )
        source_dir = os.path.join(
            self.file_manager.final_data_path,
            f'{self.file_manager.cycle_path[cycle]}/Lv5'
        )
        
        if not os.path.exists(extracted_dir):
            self.logger.error(f"경로가 존재하지 않습니다: {extracted_dir}")
            return {'success': False, 'error': f'경로 없음: {extracted_dir}'}
        
        tag_processor = TagProcessor()
        
        # 모든 extracted_qna 파일 찾기
        extracted_files = []
        for file in os.listdir(extracted_dir):
            if file.endswith('_extracted_qna.json'):
                extracted_files.append(file)
        
        self.logger.info(f"총 {len(extracted_files)}개의 extracted_qna 파일을 찾았습니다.")
        
        success_count = 0
        error_count = 0
        
        for i, file in enumerate(extracted_files, 1):
            try:
                self.logger.info(f"[{i}/{len(extracted_files)}] 처리 중: {file}")
                
                file_id = file.replace('_extracted_qna.json', '')
                
                # 파일 로드
                extracted_qna_path = os.path.join(extracted_dir, file)
                source_path = os.path.join(source_dir, file_id, f"{file_id}.json")
                
                if not os.path.exists(source_path):
                    self.logger.warning(f"원본 파일을 찾을 수 없습니다: {source_path}")
                    error_count += 1
                    continue
                
                qna_data = self.json_handler.load(extracted_qna_path)
                source_data = self.json_handler.load(source_path)
                
                # 태그 처리
                tags_added_from_source, tags_added_empty, tags_found = tag_processor.fix_missing_tags(
                    qna_data, source_data
                )
                
                filled_count, total_empty = tag_processor.fill_additional_tag_data(
                    qna_data, source_data
                )
                
                # 결과 저장
                self.json_handler.save(qna_data, extracted_qna_path)
                
                self.logger.info(
                    f"처리 완료: 추가 태그 {tags_added_from_source}개, "
                    f"빈 데이터 채움 {filled_count}/{total_empty}개"
                )
                success_count += 1
                
            except Exception as e:
                self.logger.error(f"파일 처리 오류 ({file}): {e}")
                error_count += 1
        
        self.logger.info(f"처리 완료: 성공 {success_count}개, 실패 {error_count}개")
        return {
            'success': True,
            'success_count': success_count,
            'error_count': error_count
        }
    
    def step4_format_json(self, cycle: int, file_id: str, pages: List[Dict]) -> Dict:
        """4단계: JSON 포맷 변경"""
        self.logger.info(f"=== 4단계: JSON 포맷 변경 (Cycle {cycle}, File: {file_id}) ===")
        
        result = self.json_handler.format_change(file_id, cycle, pages, self.file_manager)
        
        # 텍스트 처리
        result = self.text_processor.fill_chapter(result)
        result = self.text_processor.merge_paragraphs(result)
        
        self.logger.info("JSON 포맷 변경 완료")
        return result
    
    def run_full_pipeline(self, cycle: int, steps: List[str] = None) -> Dict[str, Any]:
        """
        전체 파이프라인 실행
        
        Args:
            cycle: 사이클 번호 (1, 2, 3)
            steps: 실행할 단계 리스트 (None이면 전체 실행)
                가능한 값: 'cleanup', 'extract', 'tags', 'format'
        
        Returns:
            실행 결과
        """
        if steps is None:
            steps = ['cleanup', 'extract', 'tags']
        
        self.logger.info(f"=== 전체 파이프라인 시작 (Cycle {cycle}) ===")
        self.logger.info(f"실행 단계: {', '.join(steps)}")
        
        results = {}
        
        try:
            if 'cleanup' in steps:
                results['cleanup'] = self.step1_cleanup_empty_pages(cycle)
            
            if 'extract' in steps:
                results['extract'] = self.step2_extract_qna(cycle)
            
            if 'tags' in steps:
                results['tags'] = self.step3_process_tags(cycle)
            
            if 'format' in steps:
                self.logger.warning("format 단계는 개별 파일 처리용입니다.")
            
            self.logger.info("=== 전체 파이프라인 완료 ===")
            results['success'] = True
            
        except Exception as e:
            self.logger.error(f"파이프라인 실행 오류: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='전체 파이프라인 실행')
    parser.add_argument('--cycle', type=int, required=True, choices=[1, 2, 3], help='사이클 번호 (1, 2, 3)')
    parser.add_argument('--steps', nargs='+', choices=['cleanup', 'extract', 'tags', 'format'],
                       default=None, help='실행할 단계 (기본값: 전체 실행)')
    parser.add_argument('--base_path', type=str, default=None, help='기본 데이터 경로')
    parser.add_argument('--config_path', type=str, default=None, help='LLM 설정 파일 경로')
    
    args = parser.parse_args()
    
    # 파이프라인 실행
    pipeline = Pipeline(base_path=args.base_path, config_path=args.config_path)
    results = pipeline.run_full_pipeline(args.cycle, args.steps)
    
    # 결과 출력
    print("\n=== 실행 결과 ===")
    print(f"성공: {results.get('success', False)}")
    
    if 'cleanup' in results:
        print(f"\n1단계 (빈 페이지 제거): {results['cleanup'].get('success', False)}")
    
    if 'extract' in results:
        print(f"\n2단계 (Q&A 추출): {results['extract'].get('success', False)}")
        if results['extract'].get('success'):
            print(f"  - 처리된 파일: {results['extract'].get('processed_files', 0)}개")
            print(f"  - 추출된 Q&A: {results['extract'].get('total_extracted', 0)}개")
    
    if 'tags' in results:
        print(f"\n3단계 (태그 처리): {results['tags'].get('success', False)}")
        if results['tags'].get('success'):
            print(f"  - 성공: {results['tags'].get('success_count', 0)}개")
            print(f"  - 실패: {results['tags'].get('error_count', 0)}개")
    
    if not results.get('success'):
        print(f"\n오류: {results.get('error', '알 수 없는 오류')}")
        sys.exit(1)


if __name__ == "__main__":
    main()

