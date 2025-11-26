#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools 모듈 초기화
tools_dir 경로 및 전역 설정을 제공
"""

import os
import subprocess
import platform

# tools 디렉토리 경로 (이 파일이 있는 디렉토리)
tools_dir = os.path.dirname(os.path.abspath(__file__))


def _find_onedrive_path():
    """플랫폼별 OneDrive 경로를 자동으로 찾는 함수"""
    system = platform.system()
    home_dir = os.path.expanduser("~")
    
    # 가능한 OneDrive 경로들
    possible_paths = []
    
    if system == "Windows":
        # Windows OneDrive 경로들
        possible_paths = [
            os.path.join(home_dir, "OneDrive", "데이터L", "selectstar"),
            os.path.join(home_dir, "OneDrive - 개인", "데이터L", "selectstar"),
            os.path.join(home_dir, "OneDrive", "개인", "데이터L", "selectstar"),
            # 환경 변수에서 OneDrive 경로 찾기
            os.path.join(os.environ.get("OneDrive", ""), "데이터L", "selectstar") if "OneDrive" in os.environ else None,
            os.path.join(os.environ.get("OneDriveConsumer", ""), "데이터L", "selectstar") if "OneDriveConsumer" in os.environ else None,
        ]
    elif system == "Darwin":  # macOS
        # macOS OneDrive 경로
        possible_paths = [
            os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar"),
            os.path.join(home_dir, "Library", "CloudStorage", "OneDrive", "데이터L", "selectstar"),
        ]
    else:  # Linux or others
        possible_paths = [
            os.path.join(home_dir, "OneDrive", "데이터L", "selectstar"),
        ]
    
    # 가능한 경로들 중 존재하는 첫 번째 경로 반환
    for path in possible_paths:
        if path and os.path.exists(path):
            return path
    
    # 경로를 찾지 못한 경우, 플랫폼별 기본 경로 반환 (존재 여부와 관계없이)
    if system == "Windows":
        # Windows 기본 경로
        return os.path.join(home_dir, "OneDrive", "데이터L", "selectstar")
    else:
        # macOS 기본 경로
        return os.path.join(home_dir, "Library", "CloudStorage", "OneDrive-개인", "데이터L", "selectstar")


def get_default_onedrive_path():
    """플랫폼별 기본 OneDrive 경로 반환 (외부 모듈에서 사용)"""
    return _find_onedrive_path()


def _find_sfaicenter_path():
    """SFAICenter 디렉토리를 찾는 함수 (find 명령어 사용)"""
    # 현재 파일의 디렉토리에서 시작
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 프로젝트 루트 경로 계산
    project_root = os.path.dirname(current_dir)
    
    # 먼저 현재 경로에서 상위로 올라가면서 SFAICenter 찾기
    search_paths = [
        project_root,  # 프로젝트 루트
        os.path.dirname(project_root),  # 프로젝트 루트의 상위
        os.path.expanduser("~"),  # 홈 디렉토리
    ]
    
    for search_path in search_paths:
        if not os.path.exists(search_path):
            continue
        
        # find 명령어로 SFAICenter 디렉토리 찾기
        try:
            # macOS/Linux find 명령어 사용
            result = subprocess.run(
                ['find', search_path, '-maxdepth', '3', '-type', 'd', '-name', 'SFAICenter', '-o', '-name', 'SFAIcenter'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # 첫 번째 결과 사용
                found_path = result.stdout.strip().split('\n')[0]
                if os.path.isdir(found_path):
                    return found_path
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            # find 명령어 실패 시 수동으로 찾기
            pass
        
        # find 실패 시 수동으로 상위 디렉토리 탐색
        current = search_path
        for _ in range(3):  # 최대 3단계 상위로
            sfaicenter_path = os.path.join(current, 'SFAICenter')
            if os.path.isdir(sfaicenter_path):
                return sfaicenter_path
            
            sfaicenter_path = os.path.join(current, 'SFAIcenter')
            if os.path.isdir(sfaicenter_path):
                return sfaicenter_path
            
            parent = os.path.dirname(current)
            if parent == current:  # 루트에 도달
                break
            current = parent
    
    # 찾지 못한 경우 프로젝트 루트 반환 (fallback)
    return project_root


# ONEDRIVE_PATH: OneDrive 데이터 경로 (플랫폼별 자동 감지)
ONEDRIVE_PATH = _find_onedrive_path()

# PROJECT_ROOT_PATH: 프로젝트 루트 경로 (기본값: 자동 감지)
PROJECT_ROOT_PATH = os.path.dirname(tools_dir)

# SFAICENTER_PATH: SFAICenter 디렉토리 경로 (find로 자동 감지)
SFAICENTER_PATH = _find_sfaicenter_path()

# 환경 변수로 오버라이드 가능
if 'ONEDRIVE_PATH' in os.environ:
    ONEDRIVE_PATH = os.environ['ONEDRIVE_PATH']
if 'PROJECT_ROOT_PATH' in os.environ:
    PROJECT_ROOT_PATH = os.environ['PROJECT_ROOT_PATH']
if 'SFAICENTER_PATH' in os.environ:
    SFAICENTER_PATH = os.environ['SFAICENTER_PATH']

__all__ = [
    'tools_dir',
    'ONEDRIVE_PATH',
    'PROJECT_ROOT_PATH',
    'SFAICENTER_PATH',
    'get_default_onedrive_path'
]

