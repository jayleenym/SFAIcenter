import configparser
import os
from openai import OpenAI
import pandas as pd
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams
import argparse

# 프로젝트 루트에서 llm_config.ini 찾기
def find_config_file():
    """프로젝트 루트에서 llm_config.ini 파일을 찾습니다."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # tools 디렉토리에서 시작해서 프로젝트 루트까지 올라가면서 찾기
    search_dirs = [
        current_dir,  # tools/
        os.path.dirname(current_dir),  # project_root/
    ]
    
    for search_dir in search_dirs:
        config_path = os.path.join(search_dir, 'llm_config.ini')
        if os.path.exists(config_path):
            return config_path
    
    # 찾지 못한 경우 기본값 반환
    return './llm_config.ini'

INI_PATH = find_config_file()


def query_openrouter(config, system_prompt: str, user_prompt: str, model_name = 'openai/gpt-5'):
    config = configparser.ConfigParser()
    # config.read(args.config_path, encoding='utf-8')
    print(f"[DEBUG] Config file path: {INI_PATH}")
    config.read(INI_PATH, encoding='utf-8')

    client = OpenAI(api_key=config["OPENROUTER"]["key"], base_url=config["OPENROUTER"]["url"])


    response = client.chat.completions.create(
                model=model_name,
                temperature=float(config["PARAMS"]["temperature"]),
                frequency_penalty=float(config["PARAMS"]["frequency_penalty"]), 
                presence_penalty=float(config["PARAMS"]["presence_penalty"]),
                top_p=float(config["PARAMS"]["top_p"]), 
                # max_tokens=int(config["PARAMS"]["max_tokens"]), 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            )
    llm_result = response.choices[0].message.content
    return llm_result



def load_model(model_path, config):
    print(f"[DEBUG] Config file path: {INI_PATH}")
    config.read(INI_PATH, encoding='utf-8')
    os.environ["CUDA_VISIBLE_DEVICES"] = config["VLLM"]["gpu"]

    llm = LLM(model = model_path, \
        tensor_parallel_size = len(config["VLLM"]["gpu"].split(",")), \
        max_model_len = int(config["VLLM"]["max_model_len"]), \
        distributed_executor_backend = "mp", \
        dtype='bfloat16', \
        # disable_custom_all_reduce=True, \
        # trust_remote_code = True, \
    )

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    stop_token_ids = [tokenizer.eos_token_id] \
        + [tokenizer.convert_tokens_to_ids(stop_token) for stop_token in config["PARAMS"]["stop_tokens"].split(",")]
    stop_token_ids = [token_id for token_id in stop_token_ids if token_id is not None]

    sampling_params = SamplingParams(
        temperature = float(config["PARAMS"]["temperature"]), 
        top_p = float(config["PARAMS"]["top_p"]), 
        top_k = int(config["PARAMS"]["top_k"]), 
        max_tokens = int(config["PARAMS"]["max_tokens"]), 
        frequency_penalty = float(config["PARAMS"]["frequency_penalty"]), 
        presence_penalty = float(config["PARAMS"]["presence_penalty"]), 
        stop_token_ids = stop_token_ids
    )

    return llm, tokenizer, sampling_params



def query_vllm(llm, tokenizer, sampling_params, system_prompt: str, user_prompt: str, model_name: str):
    """
    vLLM 모델을 직접 호출하여 system_prompt와 user_prompt를 처리합니다.
    
    Args:
        llm: 로드된 vLLM 모델
        tokenizer: 토크나이저
        sampling_params: 샘플링 파라미터
        system_prompt: 시스템 프롬프트
        user_prompt: 사용자 프롬프트
        model_name: 모델 경로
    
    Returns:
        str: 모델 응답 텍스트
    """
    try:
        # 채팅 템플릿 적용
        prompt = tokenizer.apply_chat_template(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            tokenize=False, add_generation_prompt=True
        )
        
        # 모델 추론
        outputs = llm.generate([prompt], sampling_params=sampling_params)
        
        # 결과 추출
        generated_text = outputs[0].outputs[0].text.strip()
        
        return generated_text
    except Exception as e:
        print(f"Error query_model_vllm: {e}")
        raise

if __name__ == "__main__":
    # query_openrouter 테스트
    print(query_openrouter("안녕하세요"))

    # query_model_vllm 테스트
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str)
    parser.add_argument("--task_files", type=str)
    parser.add_argument("--config_path", type=str)
    parser.add_argument("--res_path", type=str)
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config_path, encoding='utf-8')

    system_prompt = "You are a helpful assistant."
    user_prompt = "안녕하세요?"

    model_name = args.model_name.split('/')[-1]
    task_files = args.task_files.split(',')
    
    for task_file in task_files:
        df_merge = query_vllm(config, system_prompt, user_prompt, model_name)

        task_name = task_file.split('/')[-1].split('.')[0]
        output_file = os.path.join(args.res_path, f"res_{model_name}_{task_name}.csv")
        df_merge.to_csv(output_file, index=False, encoding='utf-8-sig')