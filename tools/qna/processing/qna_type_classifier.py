#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q&A 타입 분류 클래스

문제를 multiple-choice, short-answer, essay, etc으로 분류합니다.
"""

import re
from typing import Dict


class QnATypeClassifier:
    """Q&A 타입 분류 클래스"""
    
    @staticmethod
    def classify_qna_type(qna_info: dict) -> str:
        """Q&A 타입 분류 (multiple-choice/short-answer/essay/etc)"""
        try:
            if 'description' in qna_info and 'options' in qna_info['description']:
                options = qna_info['description']['options']
                answer = qna_info['description']['answer']
                
                if len(options) >= 2:
                    if len(answer) == 1 and (answer in ['O', 'X'] or answer in ['①', '②', '③', '④', '⑤']):
                        return 'multiple-choice'
                    else:
                        return 'etc'
                else:
                    sentence_count = answer.count('.') + answer.count('!') + answer.count('?') + answer.count('\n')
                    pattern_only_answer = re.match(r'^\{[ft]b?_\d{4}_\d{4}\}$', answer.strip())
                    
                    if len(answer) == 0:
                        return "etc"
                    elif (sentence_count <= 1) or pattern_only_answer:
                        return 'short-answer'
                    else:
                        return 'essay'
        except Exception as e:
            print(f"분석 오류: {e}")
            return "etc"
        
        return "etc"
