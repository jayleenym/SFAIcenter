#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 쿼리 클래스
"""

import os
import json
import re
import configparser
from openai import OpenAI
from transformers import AutoTokenizer
from typing import Optional


class LLMQuery:
    """LLM 쿼리 클래스 (OpenRouter, vLLM 지원)"""
    
    def __init__(self, config_path: str = None, api_key: str = None):
        """
        Args:
            config_path: 설정 파일 경로 (None이면 자동 검색)
            api_key: API 키 (None이면 config 파일에서 key 사용)
        """
        self.config_path = self._find_config_file(config_path)
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path, encoding='utf-8')
        
        # API 키 결정: api_key 파라미터가 있으면 사용, 없으면 config에서 key 사용
        if api_key is None:
            api_key = self.config.get("OPENROUTER", "key")
        
        # OpenRouter 클라이언트 초기화
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.config.get("OPENROUTER", "url")
        )
        
        # vLLM 관련 변수
        self.llm = None
        self.tokenizer = None
        self.sampling_params = None
    
    @staticmethod
    def _find_config_file(config_path: str = None) -> str:
        """설정 파일 찾기"""
        if config_path and os.path.exists(config_path):
            return config_path
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        search_dirs = [
            current_dir,
            os.path.dirname(current_dir),
            os.path.dirname(os.path.dirname(current_dir))
        ]
        
        for search_dir in search_dirs:
            config_path = os.path.join(search_dir, 'llm_config.ini')
            if os.path.exists(config_path):
                return config_path
        
        return './llm_config.ini'
    
    def query_openrouter(self, system_prompt: str, user_prompt: str, model_name: str = 'openai/gpt-5') -> str:
        """OpenRouter API를 통한 쿼리"""
        if model_name == 'openai/gpt-5-pro':
            response = self.client.responses.create(
                model = model_name,
                instructions = system_prompt,
                input = user_prompt,
            )
            return response.output_text
        
        response = self.client.chat.completions.create(
            model=model_name,
            temperature=float(self.config.get("PARAMS", "temperature")),
            frequency_penalty=float(self.config.get("PARAMS", "frequency_penalty")),
            presence_penalty=float(self.config.get("PARAMS", "presence_penalty")),
            top_p=float(self.config.get("PARAMS", "top_p")),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )
        return response.choices[0].message.content
    
    def load_vllm_model(self, model_path: str):
        """vLLM 모델 로드"""
        from vllm import LLM, SamplingParams
        os.environ["CUDA_VISIBLE_DEVICES"] = self.config.get("VLLM", "gpu")
        
        self.llm = LLM(
            model=model_path,
            tensor_parallel_size=len(self.config.get("VLLM", "gpu").split(",")),
            max_model_len=int(self.config.get("VLLM", "max_model_len")),
            distributed_executor_backend="mp",
            dtype='bfloat16',
        )
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        stop_token_ids = [self.tokenizer.eos_token_id] + [
            self.tokenizer.convert_tokens_to_ids(stop_token) 
            for stop_token in self.config.get("PARAMS", "stop_tokens").split(",")
        ]
        stop_token_ids = [token_id for token_id in stop_token_ids if token_id is not None]
        
        self.sampling_params = SamplingParams(
            temperature=float(self.config.get("PARAMS", "temperature")),
            top_p=float(self.config.get("PARAMS", "top_p")),
            top_k=int(self.config.get("PARAMS", "top_k")),
            max_tokens=int(self.config.get("PARAMS", "max_tokens")),
            frequency_penalty=float(self.config.get("PARAMS", "frequency_penalty")),
            presence_penalty=float(self.config.get("PARAMS", "presence_penalty")),
            stop_token_ids=stop_token_ids
        )
    
    def query_vllm(self, system_prompt: str, user_prompt: str) -> str:
        """vLLM 모델을 통한 쿼리"""
        if self.llm is None or self.tokenizer is None or self.sampling_params is None:
            raise ValueError("vLLM 모델이 로드되지 않았습니다. load_vllm_model()을 먼저 호출하세요.")
        
        prompt = self.tokenizer.apply_chat_template(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            tokenize=False,
            add_generation_prompt=True
        )
        
        outputs = self.llm.generate([prompt], self.sampling_params)
        generated_text = outputs[0].outputs[0].text.strip()
        generated_text = self.remove_think_block(generated_text)
        generated_text = self.remove_assistant_block(generated_text)
        return generated_text


    def remove_think_block(self, text):   ## for Qwen3
        if isinstance(text, str):
            return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)
        return text


    def remove_assistant_block(self, text): ## for gpt-oss-120b
        if isinstance(text, str):
            match = re.search(r"assistantfinal(.*)$", text, flags=re.DOTALL)
            return match.group(1).strip() if match else text
        return text
    
    def parse_api_response(self, response: str) -> Optional[list]:
        """API 응답 파싱 (JSON 배열 추출)"""
        try:
            # JSON 응답에서 배열 부분만 추출
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                return None
            
            json_str = response[start_idx:end_idx]
            parsed_data = json.loads(json_str)
            
            if not isinstance(parsed_data, list):
                return None
            
            return parsed_data
            
        except json.JSONDecodeError:
            return None
        except Exception:
            return None