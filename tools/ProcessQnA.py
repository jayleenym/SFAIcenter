import re
import json
import os
import shutil
from typing import List, Dict, Any



def analyze_extracted_qna(qna_info: dict):
    # qna_info = qna_data['qna_data']
    # print(qna_info)
    try:
        if 'description' in qna_info and 'options' in qna_info['description']:
            options = qna_info['description']['options']
            answer = qna_info['description']['answer']
            if (len(answer) == 1) or (answer in ['O', 'X']):
                # 객관식
                return 'multiple-choice'
            else:
                # 주관식 - 답변의 문장 수로 단답형/서술형 구분
                sentence_count = answer.count('.') + answer.count('!') + answer.count('?')
                if sentence_count <= 1:
                    # 한 문장 또는 한 단어 (단답형)
                    return 'short-answer'
                else:
                    # 2문장 이상 (서술형)
                    return 'essay'
    except Exception as e:
        print("분석 오류:", e)


# 수정된 extract_qna_tags 함수 (정규식 패턴 수정)
def extract_qna_tags(json_data: Dict[str, Any], file_name: str) -> Dict[str, Any]:
    """
    page_contents에서 {q_0000_0000} 형태의 태그를 추출하고,
    add_info에서 해당 태그를 찾아서 별도 리스트로 분리하는 함수
    Q&A 내용 안의 tb, img, f 태그도 함께 추출하여 제거 (수정된 정규식)
    
    Args:
        json_data: JSON 데이터
        
    Returns:
        수정된 JSON 데이터와 추출된 Q&A 리스트
    """
    # 추출된 Q&A를 저장할 리스트
    extracted_qna = []

    # 각 페이지를 순회
    for page_data in json_data.get('contents', []):
        page_contents = page_data.get('page_contents', '')
        if page_contents != "":
            add_info = page_data.get('add_info', [])
            
            # page_contents에서 {q_0000_0000} 형태의 태그 추출
            qna_tags = re.findall(r'\{q_\d{4}_\d{4}\}', page_contents)
            
            # 제거할 인덱스들을 수집
            indices_to_remove = set()
            qna_items_to_extract = []
            
            # 각 태그에 대해 add_info에서 해당하는 항목 찾기
            for tag in qna_tags:
                # add_info에서 해당 태그를 가진 항목 찾기
                qna_item_index = None
                qna_item = None
                tag = tag.removeprefix('{').removesuffix('}')
                
                for i, info_item in enumerate(add_info):
                    if info_item.get('tag') == tag:
                        qna_item_index = i
                        qna_item = info_item
                        break
                
                if qna_item is not None:
                    # Q&A 내용에서 추가 태그들 추출
                    qna_content = ""
                    if 'description' in qna_item:
                        desc = qna_item['description']
                        # question, answer, explanation, options에서 태그 추출
                        for field in ['question', 'answer', 'explanation', 'options']:
                            if field in desc and desc[field]:
                                if field == 'options' and isinstance(desc[field], list):
                                    # options는 리스트이므로 각 항목을 합침
                                    for option in desc[field]:
                                        qna_content += str(option) + " "
                                else:
                                    qna_content += str(desc[field]) + " "
                    
                    # Q&A 내용에서 tb, img, f 태그 추출 (수정된 정규식)
                    tb_tags = re.findall(r'\{tb_\d{4}_\d{4}\}', qna_content)
                    img_tags = re.findall(r'\{img_\d{4}_\d{4}\}', qna_content)
                    f_tags = re.findall(r'\{f_\d{4}_\d{4}\}', qna_content)
                    additional_tags = tb_tags + img_tags + f_tags
                    
                    # 디버깅: 추가 태그 발견 시 출력
                    # if additional_tags:
                    #     print(f"  추가 태그 발견 - Q&A: {tag}")
                    #     print(f"    TB: {tb_tags}, IMG: {img_tags}, F: {f_tags}")
                    
                    # 추가 태그들의 실제 데이터 수집
                    additional_tag_data = []
                    
                    # 추가 태그들도 add_info에서 찾아서 인덱스 수집 및 데이터 저장
                    for additional_tag in additional_tags:
                        tag_without_braces = additional_tag[1:-1]  # {tag} -> tag
                        for j, additional_info_item in enumerate(add_info):
                            if additional_info_item.get('tag') == tag_without_braces:
                                indices_to_remove.add(j)
                                # 추가 태그의 실제 데이터도 저장
                                additional_tag_data.append({
                                    'tag': additional_tag,
                                    # 'tag_type': additional_tag.split('_')[0][1:],  # {tb_0000_0000} -> tb
                                    'data': additional_info_item
                                })
                                # print(f"    -> 추가 태그 데이터 수집: {additional_tag}")
                                break
                    
                    # Q&A 항목도 제거 대상에 추가
                    indices_to_remove.add(qna_item_index)

                    # 질문 타입
                    qna_type = analyze_extracted_qna(qna_item)

                    # Domain 찾기
                    with_domain_dir = "/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/data/FIN_workbook/1C/with_domain"
                    qna_domain = find_domain_for_qna(qna_item, file_name, with_domain_dir)

                    # 추출할 Q&A 정보 저장
                    qna_items_to_extract.append({
                        'file_id': json_data.get("file_id"),
                        'title': json_data.get('title'),
                        'chapter': page_data.get('chapter'),
                        'page': page_data.get('page'),
                        "qna_type": qna_type,
                        "qna_domain": qna_domain,
                        'qna_data': qna_item,
                        'additional_tags_found': additional_tags,
                        'additional_tag_data': additional_tag_data
                    })


            
            # 인덱스를 역순으로 정렬하여 제거 (뒤에서부터 제거)
            sorted_indices = sorted(indices_to_remove, reverse=True)
            for idx in sorted_indices:
                if 0 <= idx < len(add_info):
                    add_info.pop(idx)
            
            # 추출된 Q&A들을 리스트에 추가
            extracted_qna.extend(qna_items_to_extract)

            # 수정된 add_info로 업데이트
            page_data['add_info'] = add_info
            page_data['page_contents'] = re.sub(r'\{q_\d{4}_\d{4}\}', "", page_contents)
            page_data['page_contents'] = page_data['page_contents'].replace('\n\n', '\n')
    
    # 정제 끝나고 빈 페이지 삭제
    pages_to_remove = []
    for i, page_data in enumerate(json_data.get('contents', [])):
        page_contents = page_data.get('page_contents', '')
        if page_contents.strip() == "":
            pages_to_remove.append(i)
    
    # 역순으로 제거
    for i in reversed(pages_to_remove):
        json_data['contents'].pop(i)
    
    return {
        'modified_json': json_data,
        'extracted_qna': extracted_qna
    }

def find_domain_for_qna(qna_item: Dict[str, Any], file_id: str, with_domain_dir: str) -> str:
    """
    with_domain 폴더에서 동일한 문제를 찾아서 domain을 반환하는 함수
    
    Args:
        qna_item: 찾을 Q&A 아이템
        file_id: 파일 ID
        with_domain_dir: with_domain 폴더 경로
        
    Returns:
        찾은 domain 또는 빈 문자열
    """
    try:
        # with_domain 파일 경로 생성
        with_domain_file = os.path.join(with_domain_dir, f"{file_id}_extracted_qna_with_domain.json")
        
        if not os.path.exists(with_domain_file):
            print(f"with_domain 파일이 존재하지 않습니다: {with_domain_file}")
            return ""
        
        # with_domain 파일 읽기
        with open(with_domain_file, 'r', encoding='utf-8') as f:
            with_domain_data = json.load(f)
        
        # 현재 Q&A의 질문과 정답으로 매칭
        current_question = qna_item.get('description', {}).get('question', '')
        current_answer = qna_item.get('description', {}).get('answer', '')
        
        for domain_item in with_domain_data:
            domain_qna = domain_item.get('qna_data', {})
            domain_question = domain_qna.get('description', {}).get('question', '')
            domain_answer = domain_qna.get('description', {}).get('answer', '')
            
            # 질문과 정답이 일치하면 domain 반환
            if (current_question == domain_question and 
                current_answer == domain_answer):
                return domain_item.get('qna_domain', '')
        
        return ""
        
    except Exception as e:
        print(f"Domain 매칭 오류: {e}")
        return ""

def get_qna_datas(file_path: str, output_path: str = None) -> Dict[str, Any]:
    """
    JSON 파일을 처리하여 Q&A 태그를 추출하고 분리하는 함수
    
    Args:
        file_path: 입력 JSON 파일 경로
        output_path: 출력 JSON 파일 경로 (None이면 원본 파일 덮어쓰기)
        
    Returns:
        처리 결과
    """
    # JSON 파일 읽기
    with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # Q&A 태그 추출 및 분리
    result = extract_qna_tags(json_data, os.path.splitext(os.path.basename(file_path))[0])
    
    # 수정된 JSON 저장
    output_file = output_path if output_path else file_path
    
    # 파일이 존재하면 백업 생성
    if os.path.exists(output_file):
        # extract_backup 폴더 생성 (존재하지 않는 경우)
        backup_dir = os.path.join(os.path.dirname(output_file), 'extract_backup')
        os.makedirs(backup_dir, exist_ok=True)
        
        # 백업 파일명 생성 (.bak 확장자 추가)
        backup_filename = os.path.basename(output_file) + '.bak'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # 기존 파일을 백업 폴더로 복사
        shutil.copy2(output_file, backup_path)
        print(f"기존 파일을 백업했습니다: {backup_path}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result['modified_json'], f, ensure_ascii=False, indent=4)
    

    # 추출된 Q&A를 별도 파일로 저장
    if len(result['extracted_qna']) != 0:
        qna_output_path = output_path.replace('.json', '_extracted_qna.json')
        with open(qna_output_path, 'w', encoding='utf-8') as f:
            json.dump(result['extracted_qna'], f, ensure_ascii=False, indent=4)

        # analyze_extracted_qna(qna_output_path)
        return result
    else:
        qna_output_path = ""
    
    print(f"처리 완료:")
    print(f"- 수정된 JSON: {output_file}")
    print(f"- 추출된 Q&A: {qna_output_path}")
    if len(result['extracted_qna']) > 0:
        print(f"- 추출된 Q&A 개수: {len(result['extracted_qna'])}")
    
    return result


def merge_extracted_qna_files(input_dir: str, output_file: str = None) -> Dict[str, Any]:
    """
    지정된 경로의 모든 extracted_qna 파일을 하나로 합치는 함수
    
    Args:
        input_dir: extracted_qna 파일들이 있는 디렉토리 경로
        output_file: 출력 파일 경로 (None이면 input_dir/merged_extracted_qna.json)
        
    Returns:
        합쳐진 Q&A 데이터와 통계 정보
    """
    try:
        # 모든 extracted_qna 파일 찾기
        extracted_files = []
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.endswith('_extracted_qna.json') and file != 'merged_extracted_qna.json':
                    extracted_files.append(os.path.join(root, file))
        
        if not extracted_files:
            print(f"extracted_qna 파일을 찾을 수 없습니다: {input_dir}")
            return {'merged_data': [], 'statistics': {}}
        
        print(f"발견된 extracted_qna 파일 개수: {len(extracted_files)}")
        
        # 모든 Q&A 데이터를 합칠 리스트
        merged_qna_data = []
        file_stats = {}
        
        # 각 파일을 읽어서 합치기
        for file_path in extracted_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    qna_data = json.load(f)
                
                # Q&A 데이터가 리스트인지 확인
                if isinstance(qna_data, list):
                    merged_qna_data.extend(qna_data)
                    file_stats[os.path.basename(file_path)] = len(qna_data)
                    print(f"  - {os.path.basename(file_path)}: {len(qna_data)}개 Q&A 추가")
                else:
                    print(f"  - {os.path.basename(file_path)}: 잘못된 형식 (리스트가 아님)")
                    
            except Exception as e:
                print(f"  - {os.path.basename(file_path)}: 읽기 오류 - {e}")
        
        # 출력 파일 경로 설정
        if output_file is None:
            output_file = os.path.join(input_dir, 'merged_extracted_qna.json')
        
        # 합쳐진 데이터 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_qna_data, f, ensure_ascii=False, indent=4)
        
        # 통계 정보 생성
        statistics = {
            'total_files_processed': len(extracted_files),
            'total_qna_count': len(merged_qna_data),
            'files_stats': file_stats,
            'output_file': output_file
        }
        
        # Domain별 통계
        domain_stats = {}
        for qna_item in merged_qna_data:
            domain = qna_item.get('qna_domain', 'Unknown')
            domain_stats[domain] = domain_stats.get(domain, 0) + 1
        
        statistics['domain_stats'] = domain_stats
        
        print(f"\n합치기 완료:")
        print(f"- 총 Q&A 개수: {len(merged_qna_data)}")
        print(f"- 출력 파일: {output_file}")
        print(f"- Domain별 통계:")
        for domain, count in sorted(domain_stats.items()):
            print(f"  {domain}: {count}개")
        
        return {
            'merged_data': merged_qna_data,
            'statistics': statistics
        }
        
    except Exception as e:
        print(f"파일 합치기 오류: {e}")
        return {'merged_data': [], 'statistics': {}}


def merge_qna_by_domain(input_dir: str, output_dir: str = None) -> Dict[str, Any]:
    """
    Domain별로 extracted_qna 파일들을 분류하여 합치는 함수
    
    Args:
        input_dir: extracted_qna 파일들이 있는 디렉토리 경로
        output_dir: 출력 디렉토리 (None이면 input_dir/domain_merged)
        
    Returns:
        Domain별로 합쳐진 결과
    """
    try:
        # 모든 extracted_qna 파일 찾기
        extracted_files = []
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.endswith('_extracted_qna.json'):
                    extracted_files.append(os.path.join(root, file))
        
        if not extracted_files:
            print(f"extracted_qna 파일을 찾을 수 없습니다: {input_dir}")
            return {}
        
        # Domain별로 데이터 분류
        domain_data = {}
        
        for file_path in extracted_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    qna_data = json.load(f)
                
                if isinstance(qna_data, list):
                    for qna_item in qna_data:
                        domain = qna_item.get('qna_domain', 'Unknown')
                        if domain not in domain_data:
                            domain_data[domain] = []
                        domain_data[domain].append(qna_item)
                        
            except Exception as e:
                print(f"파일 읽기 오류 {os.path.basename(file_path)}: {e}")
        
        # 출력 디렉토리 설정
        if output_dir is None:
            output_dir = os.path.join(input_dir, 'domain_merged')
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Domain별로 파일 저장
        domain_results = {}
        for domain, qna_list in domain_data.items():
            output_file = os.path.join(output_dir, f"{domain}_merged_qna.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(qna_list, f, ensure_ascii=False, indent=4)
            
            domain_results[domain] = {
                'file_path': output_file,
                'count': len(qna_list)
            }
            print(f"{domain}: {len(qna_list)}개 Q&A -> {output_file}")
        
        return domain_results
        
    except Exception as e:
        print(f"Domain별 합치기 오류: {e}")
        return {} 