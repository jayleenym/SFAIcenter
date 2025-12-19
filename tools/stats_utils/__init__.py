#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
statistics 패키지 - 통계 저장 및 집계 관련 기능

이 패키지는 Q&A 및 시험 관련 통계를 저장하고 집계하는 기능을 제공합니다:
- StatisticsSaver: 통계 데이터 저장 및 집계
"""

from .statistics_saver import StatisticsSaver

__all__ = ['StatisticsSaver']

