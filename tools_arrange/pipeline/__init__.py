# pipeline 패키지
from .config import ONEDRIVE_PATH, PROJECT_ROOT_PATH
from .base import PipelineBase
from .main import Pipeline

__all__ = [
    'ONEDRIVE_PATH',
    'PROJECT_ROOT_PATH',
    'PipelineBase',
    'Pipeline'
]

# 경로 설정을 쉽게 접근할 수 있도록
__version__ = '1.0.0'

