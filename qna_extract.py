import json
import os
import pandas as pd
import warnings
import shutil

import tools.ProcessFiles as pf
import tools.ProcessQnA as pq

origin_data_dir = os.path.join(pf.FINAL_DATA_PATH, '2C')#.replace('jinym', 'yejin')
data_dir = pf.FINAL_DATA_PATH.replace('FINAL', 'FIN_workbook/2C')#.replace('jinym', 'yejin')
origin_data_dir, data_dir

json_files = pf.get_filelist(2, origin_data_dir)
json_files = [file for file in json_files if 'Lv5' in file]


# 모든 JSON 파일 일괄 처리
print(f"총 {len(json_files)}개의 JSON 파일을 찾았습니다.")

total_extracted = 0
processed_files = 0

for i, json_file in enumerate(json_files):
    try:
        print(f"\n[{i+1}/{len(json_files)}] 처리 중: {os.path.basename(json_file)}")
        
        # 파일 처리
        name = os.path.basename(json_file)
        result = pq.get_qna_datas(json_file, os.path.join(data_dir, 'extracted', name), 'x-ai/grok-4-fast')
        
        total_extracted += len(result['extracted_qna'])
        processed_files += 1
        
        print(f"- 추출된 Q&A: {len(result['extracted_qna'])}개")
        
    except Exception as e:
        print(f"  - 오류 발생: {e}")

print(f"\n=== 전체 처리 결과 ===")
print(f"- 처리된 파일: {processed_files}/{len(json_files)}")
print(f"- 총 추출된 Q&A: {total_extracted}개")