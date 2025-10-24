import configparser
import os
from openai import OpenAI

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

def query_model_openrouter(system_prompt: str, user_prompt: str, model_name = 'openai/gpt-5'):
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

if __name__ == "__main__":
    print(query_model_openrouter("안녕하세요"))