#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
경로 설정 - 여기서만 수정하면 됩니다
"""

import os

# ONEDRIVE_PATH: OneDrive 데이터 경로 (기본값: 자동 감지)
ONEDRIVE_PATH = os.path.join(
    os.path.expanduser("~"),
    "Library/CloudStorage/OneDrive-개인/데이터L/selectstar"
)

# PROJECT_ROOT_PATH: 프로젝트 루트 경로 (기본값: 자동 감지)
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_PATH = os.path.dirname(os.path.dirname(current_dir))

# 환경 변수로 오버라이드 가능
if 'ONEDRIVE_PATH' in os.environ:
    ONEDRIVE_PATH = os.environ['ONEDRIVE_PATH']
if 'PROJECT_ROOT_PATH' in os.environ:
    PROJECT_ROOT_PATH = os.environ['PROJECT_ROOT_PATH']

