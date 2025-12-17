#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools 모듈 초기화

이 모듈은 프로젝트 전체에서 사용되는 경로 설정을 제공합니다.
환경 변수로 오버라이드 가능:
- ONEDRIVE_PATH: OneDrive 데이터 경로
- PROJECT_ROOT_PATH: 프로젝트 루트 경로  
- SFAICENTER_PATH: SFAICenter 디렉토리 경로
"""

import os
import platform
from pathlib import Path
from typing import Optional


class PathResolver:
    """플랫폼별 경로 자동 탐지 클래스"""
    
    _instance: Optional['PathResolver'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'PathResolver':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if PathResolver._initialized:
            return
        
        self._system = platform.system()
        self._home = Path.home()
        self._tools_dir = Path(__file__).parent.resolve()
        self._project_root = self._tools_dir.parent
        
        # 캐시된 경로들
        self._onedrive_path: Optional[Path] = None
        self._sfaicenter_path: Optional[Path] = None
        
        PathResolver._initialized = True
    
    @property
    def tools_dir(self) -> Path:
        """tools 디렉토리 경로"""
        return self._tools_dir
    
    @property
    def project_root(self) -> Path:
        """프로젝트 루트 경로"""
        return self._project_root
    
    @property
    def onedrive_path(self) -> Path:
        """OneDrive 경로 (캐시됨)"""
        if self._onedrive_path is None:
            self._onedrive_path = self._find_onedrive_path()
        return self._onedrive_path
    
    @property
    def sfaicenter_path(self) -> Path:
        """SFAICenter 경로 (캐시됨)"""
        if self._sfaicenter_path is None:
            self._sfaicenter_path = self._find_sfaicenter_path()
        return self._sfaicenter_path
    
    def _find_onedrive_path(self) -> Path:
        """플랫폼별 OneDrive 경로 탐지"""
        # 플랫폼별 후보 경로 정의
        if self._system == "Windows":
            candidates = [
                self._home / "OneDrive" / "데이터L" / "selectstar",
                self._home / "OneDrive - 개인" / "데이터L" / "selectstar",
            ]
            # 환경 변수에서 추가 경로 확인
            for env_var in ["OneDrive", "OneDriveConsumer"]:
                env_path = os.environ.get(env_var)
                if env_path:
                    candidates.append(Path(env_path) / "데이터L" / "selectstar")
        elif self._system == "Darwin":  # macOS
            cloud_storage = self._home / "Library" / "CloudStorage"
            candidates = [
                cloud_storage / "OneDrive-개인" / "데이터L" / "selectstar",
                cloud_storage / "OneDrive" / "데이터L" / "selectstar",
            ]
        else:  # Linux 등
            candidates = [
                self._home / "OneDrive" / "데이터L" / "selectstar",
            ]
        
        # 존재하는 첫 번째 경로 반환
        for path in candidates:
            if path.exists():
                return path
        
        # 찾지 못한 경우 기본값 반환
        return candidates[0] if candidates else self._home / "OneDrive"
    
    def _find_sfaicenter_path(self) -> Path:
        """SFAICenter 디렉토리 탐지"""
        # 현재 프로젝트가 SFAICenter인지 확인
        current = self._project_root
        if current.name.lower() in ('sfaicenter', 'sfaicenter✨'):
            return current
        
        # 상위 디렉토리에서 검색
        search_dirs = [
            self._project_root,
            self._project_root.parent,
            self._home,
        ]
        
        for base in search_dirs:
            if not base.exists():
                continue
            
            # 직접 하위 디렉토리 확인 (최대 2단계)
            for depth in range(3):
                for path in base.glob('*' * (depth + 1) if depth > 0 else '*'):
                    if path.is_dir() and path.name.lower() in ('sfaicenter', 'sfaicenter✨'):
                        return path
        
        # 찾지 못한 경우 프로젝트 루트 반환
        return self._project_root


# 싱글톤 인스턴스
_resolver = PathResolver()

# tools 디렉토리 경로 (이 파일이 있는 디렉토리)
tools_dir = str(_resolver.tools_dir)

# 환경 변수 우선, 없으면 자동 탐지
ONEDRIVE_PATH = os.environ.get('ONEDRIVE_PATH') or str(_resolver.onedrive_path)
PROJECT_ROOT_PATH = os.environ.get('PROJECT_ROOT_PATH') or str(_resolver.project_root)
SFAICENTER_PATH = os.environ.get('SFAICENTER_PATH') or str(_resolver.sfaicenter_path)


def get_default_onedrive_path() -> str:
    """플랫폼별 기본 OneDrive 경로 반환 (외부 모듈에서 사용)"""
    return str(_resolver.onedrive_path)


def get_path_resolver() -> PathResolver:
    """PathResolver 인스턴스 반환 (고급 사용자용)"""
    return _resolver


__all__ = [
    # 경로 문자열 (하위 호환성)
    'tools_dir',
    'ONEDRIVE_PATH',
    'PROJECT_ROOT_PATH',
    'SFAICENTER_PATH',
    # 함수
    'get_default_onedrive_path',
    'get_path_resolver',
    # 클래스
    'PathResolver',
]
