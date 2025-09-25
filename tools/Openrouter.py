import configparser
from openai import OpenAI


INI_PATH = './llm_config.ini'

def query_model_openrouter(system_prompt: str, user_prompt: str, model_name = 'openai/gpt-5'):
    config = configparser.ConfigParser()
    # config.read(args.config_path, encoding='utf-8')
    config.read(INI_PATH, encoding='utf-8')

    client = OpenAI(api_key=config["OPENROUTER"]["key"], base_url=config["OPENROUTER"]["url"])


    response = client.chat.completions.create(
                model=model_name,
                temperature=float(config["PARAMS"]["temperature"]),
                frequency_penalty=float(config["PARAMS"]["frequency_penalty"]), 
                presence_penalty=float(config["PARAMS"]["presence_penalty"]),
                top_p=float(config["PARAMS"]["top_p"]), 
                max_tokens=int(config["PARAMS"]["max_tokens"]), 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            )
    llm_result = response.choices[0].message.content
    return llm_result

if __name__ == "__main__":
    print(query_model_openrouter("안녕하세요"))