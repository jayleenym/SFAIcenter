#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시험 설정 파일 로더 및 헬퍼 클래스
- exam_config.json 파일을 로드하고 기존 코드와의 호환성을 제공
"""

import os
import json
from typing import Dict, Any, List, Optional


class ExamConfig:
    """시험 설정 파일을 로드하고 다양한 형태로 접근할 수 있게 해주는 헬퍼 클래스"""
    
    def __init__(self, config_path: str = None, onedrive_path: str = None):
        """
        Args:
            config_path: exam_config.json 파일 경로. None이면 기본 경로 사용
            onedrive_path: OneDrive 경로. config_path가 None일 때 우선적으로 사용
        """
        if config_path is None:
            # OneDrive 경로가 제공된 경우 우선 사용
            if onedrive_path:
                config_path = os.path.join(onedrive_path, 'evaluation', 'eval_data', 'exam_config.json')
            
            # 기본 경로 찾기
            if config_path is None or not os.path.exists(config_path):
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(current_dir))
                project_config_path = os.path.join(project_root, 'evaluation', 'eval_data', 'exam_config.json')
                
                if os.path.exists(project_config_path):
                    config_path = project_config_path
                else:
                    # OneDrive 경로도 시도
                    if onedrive_path is None:
                        import platform
                        system = platform.system()
                        home_dir = os.path.expanduser("~")
                        if system == "Windows":
                            onedrive_path = os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
                        else:
                            onedrive_path = os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")
                    config_path = os.path.join(onedrive_path, 'evaluation', 'eval_data', 'exam_config.json')
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"exam_config.json 파일을 찾을 수 없습니다: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    def get_exam_statistics(self) -> Dict[str, Any]:
        """
        기존 exam_statistics.json과 동일한 형태로 반환
        Returns:
            {
                "금융일반": {
                    "경제": {
                        "exam_questions": 125,
                        "exam_subdomain_distribution": {
                            "미시경제학": 32,
                            ...
                        }
                    },
                    ...
                },
                ...
            }
        """
        result = {}
        for exam_name, exam_data in self.config['exams'].items():
            result[exam_name] = {}
            for domain_name, domain_data in exam_data['domain_details'].items():
                result[exam_name][domain_name] = {
                    'exam_questions': domain_data['exam_questions'],
                    'exam_subdomain_distribution': {
                        subdomain_name: subdomain_data['count']
                        for subdomain_name, subdomain_data in domain_data['subdomains'].items()
                    }
                }
        return result
    
    def get_exam_hierarchy(self) -> Dict[str, List[str]]:
        """
        기존 exam_hierarchy.json과 동일한 형태로 반환
        Returns:
            {
                "금융일반": ["경제", "경영"],
                "금융심화": ["회계", "세무", "노무"],
                ...
            }
        """
        return {
            exam_name: exam_data['domains']
            for exam_name, exam_data in self.config['exams'].items()
        }
    
    def get_domain_subdomain(self) -> Dict[str, List[str]]:
        """
        기존 domain_subdomain.json과 동일한 형태로 반환
        Returns:
            {
                "경제": [
                    "미시경제학 (수요·공급, 소비자·생산자이론, 시장이론, 후생경제)",
                    ...
                ],
                ...
            }
        """
        return self.config['all_domains']
    
    def get_exam_domains(self, exam_name: str) -> List[str]:
        """특정 시험의 도메인 리스트 반환"""
        if exam_name not in self.config['exams']:
            raise ValueError(f"시험 이름을 찾을 수 없습니다: {exam_name}")
        return self.config['exams'][exam_name]['domains']
    
    def get_domain_info(self, exam_name: str, domain_name: str) -> Dict[str, Any]:
        """특정 시험의 특정 도메인 정보 반환"""
        if exam_name not in self.config['exams']:
            raise ValueError(f"시험 이름을 찾을 수 없습니다: {exam_name}")
        if domain_name not in self.config['exams'][exam_name]['domain_details']:
            raise ValueError(f"도메인을 찾을 수 없습니다: {exam_name} > {domain_name}")
        return self.config['exams'][exam_name]['domain_details'][domain_name]
    
    def get_subdomain_info(self, exam_name: str, domain_name: str, subdomain_name: str) -> Dict[str, Any]:
        """특정 서브도메인 정보 반환"""
        domain_info = self.get_domain_info(exam_name, domain_name)
        if subdomain_name not in domain_info['subdomains']:
            raise ValueError(f"서브도메인을 찾을 수 없습니다: {exam_name} > {domain_name} > {subdomain_name}")
        return domain_info['subdomains'][subdomain_name]
    
    def get_subdomain_count(self, exam_name: str, domain_name: str, subdomain_name: str) -> int:
        """특정 서브도메인의 문제 수 반환"""
        return self.get_subdomain_info(exam_name, domain_name, subdomain_name)['count']
    
    def get_subdomain_description(self, exam_name: str, domain_name: str, subdomain_name: str) -> str:
        """특정 서브도메인의 설명 반환"""
        return self.get_subdomain_info(exam_name, domain_name, subdomain_name)['description']
    
    def get_all_exams(self) -> List[str]:
        """모든 시험 이름 리스트 반환"""
        return list(self.config['exams'].keys())
    
    def get_all_domains(self) -> List[str]:
        """모든 도메인 이름 리스트 반환"""
        return list(self.config['all_domains'].keys())
    
    def get_full_config(self) -> Dict[str, Any]:
        """전체 설정 반환"""
        return self.config


def load_exam_config(config_path: str = None, onedrive_path: str = None) -> ExamConfig:
    """
    편의 함수: ExamConfig 인스턴스 생성
    Usage:
        config = load_exam_config()
        stats = config.get_exam_statistics()
    """
    return ExamConfig(config_path, onedrive_path)


# 기존 코드와의 호환성을 위한 함수들
def load_exam_statistics(config_path: str = None, onedrive_path: str = None) -> Dict[str, Any]:
    """기존 코드와의 호환성: exam_statistics.json 형태로 반환"""
    config = ExamConfig(config_path, onedrive_path)
    return config.get_exam_statistics()


def load_exam_hierarchy(config_path: str = None, onedrive_path: str = None) -> Dict[str, List[str]]:
    """기존 코드와의 호환성: exam_hierarchy.json 형태로 반환"""
    config = ExamConfig(config_path, onedrive_path)
    return config.get_exam_hierarchy()


def load_domain_subdomain(config_path: str = None, onedrive_path: str = None) -> Dict[str, List[str]]:
    """기존 코드와의 호환성: domain_subdomain.json 형태로 반환"""
    config = ExamConfig(config_path, onedrive_path)
    return config.get_domain_subdomain()

