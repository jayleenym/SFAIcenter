import re
import json
import os
import shutil
from typing import List, Dict, Any

import tools.Openrouter as Openrouter
from tools.ProcessFiles import FINAL_DATA_PATH, CYCLE_PATH


def analyze_extracted_qna(qna_info: dict):
    try:
        if 'description' in qna_info and 'options' in qna_info['description']:
            options = qna_info['description']['options']
            answer = qna_info['description']['answer']
            # 객관식 판별: O/X 선택 또는 ①②③④⑤ 번호 선택만
            if (answer in ['O', 'X']) or \
               (answer in ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']):
                # 객관식
                return 'multiple-choice'
            else:
                # 주관식 - 답변의 문장 수로 단답형/서술형 구분
                sentence_count = answer.count('.') + answer.count('!') + answer.count('?') + answer.count('\n')
                
                # {f_0000_0000} 또는 {tb_0000_0000} 패턴만 있는 경우 short-answer로 분류
                import re
                pattern_only_answer = re.match(r'^\{[ft]b?_\d{4}_\d{4}\}$', answer.strip())
                
                if len(answer) == 0:
                    return ""
                elif (sentence_count <= 1) and (("{" not in answer) or pattern_only_answer):
                    # 한 문장 또는 한 단어 (단답형)
                    # 또는 {f_0000_0000}, {tb_0000_0000} 패턴만 있는 경우
                    return 'short-answer'
                else:
                    # 2문장 이상 (서술형)
                    return 'essay'
    except Exception as e:
        print("분석 오류:", e)


def add_qna_domain_onebyone(json_data: dict, page_data: dict, model: str = None) -> list:
    """
    페이지의 Q&A 데이터에 Domain을 추가하는 함수
    
    Args:
        json_data: 전체 JSON 데이터
        page_data: 페이지 데이터
        model: 사용할 모델
        
    Returns:
        Domain 분류 결과 리스트
"""
    system_prompt = """
당신은 금융 문제지를 분류하는 전문가입니다.  
당신의 임무는 주어진 정보(책 제목, 책 분류, 챕터 제목)를 바탕으로 질문을 아래 분류 체계 중 하나로 정확하게 분류하는 것입니다.  

## 분류 체계

1. 금융기초
- 경제 (미시경제, 거시경제, 국제경제, 계량경제 등)
- 경영 (인사/조직, 전략/마케팅, 재무기초 등)
- 회계 (회계사 관련 자격증 및 회계 관련 학문적 내용)
- 세무 (세무사 관련 자격증 및 세법 관련 학문적 내용)
- 노무 (노무사 관련 자격증 및 노동법, 사회보험법 관련 학문적 내용)
- 통계 (통계 관련 자격증 및 통계학 관련 학문적 내용)

2. 금융실무
- 내부통제 (컴플라이언스, 법률, 규제, 협회규정 등)
- 영업 (세일즈, 화법, 고객관리 등)
- 디지털 (마이데이터, 가상자산, 블록체인, 핀테크 등)
- 자산운용 (트레이딩, 채권, 부동산PF, 퇴직연금, 신탁 등)
- 리스크관리 (채권수심, 신용리스크, 대체심사, 헷징 등)
- 보험계약 (장기보험, 자동차보험, 해상보험, 지급, 보전 등)
- 보상처리 (손해사정, 보험금 심사, 자동차 보상 등)

---

## 분류 지침
1. 반드시 위 체계 중 하나를 선택합니다.  
2. 질문의 핵심 주제가 학문적 개념·이론이면 → 금융기초,  
   실제 업무·규제·법률·실무 절차라면 → 금융실무로 분류합니다.  
3. 모호한 경우 더 구체적인 문맥을 고려해 대분류와 세부 카테고리를 명확히 결정합니다.  
4. 출력은 분류 결과만 JSON 형식으로 작성합니다.
5. 출력에는 코드 블록 표시(```json, ```)를 절대 포함하지 않습니다.  

---

## 출력 형식
[{
  "대분류": "금융기초 또는 금융실무",
  "카테고리": "세부 카테고리명",
  "근거": "간단한 분류 이유"
},
{
  "대분류": "금융기초 또는 금융실무",
  "카테고리": "세부 카테고리명",
  "근거": "간단한 분류 이유"
}]
"""
    user_prompt = ''
    # page_contents에서 Q&A 태그가 있는 항목들만 찾아서 처리
    page_contents = page_data.get('page_contents', '')
    qna_tags = re.findall(r'\{q_\d{4}_\d{4}\}', page_contents)
    
    for tag in qna_tags:
        tag_without_braces = tag[1:-1]  # {q_0000_0000} -> q_0000_0000
        # add_info에서 해당 태그를 가진 항목 찾기
        for info_item in page_data.get('add_info', []):
            if info_item.get('tag') == tag_without_braces and info_item.get('type') == 'question':
                single_prompt = f"""
책 제목: {json_data['title']}
책 분류: {json_data.get('cat1_domain', '')}/{json_data.get('cat2_sub', '')}/{json_data.get('cat3_specific', '')}
챕터: {page_data.get('chapter', '')}
질문: {info_item['description']['question']}
답변: {info_item['description']['answer']}
해설: {info_item['description']['explanation']}
===================="""
                user_prompt += single_prompt
                break
    
    # Q&A가 없는 경우 빈 리스트 반환
    if not user_prompt.strip():
        print(f"  - 페이지에 Q&A가 없음")
        return []
    
    # API 호출 및 도메인 분류
    print(f"  - API 호출 중... (모델: {model})")
    domain_response = Openrouter.query_model_openrouter(system_prompt, user_prompt, model)
    return domain_response



# 수정된 extract_qna_tags 함수 (정규식 패턴 수정)
def extract_qna_tags(json_data: Dict[str, Any], file_name: str, llm_model: str = None, output_path: str = None) -> Dict[str, Any]:
    """
    page_contents에서 {q_0000_0000} 형태의 태그를 추출하고,
    add_info에서 해당 태그를 찾아서 별도 리스트로 분리하는 함수
    Q&A 내용 안의 tb, img, f, etc 태그도 함께 추출하여 제거 (수정된 정규식)
    페이지별로 중간저장도 수행
    
    Args:
        json_data: JSON 데이터
        file_name: 파일명
        llm_model: 사용할 LLM 모델
        output_path: 출력 경로 (페이지별 중간저장용)
        
    Returns:
        추출된 Q&A 리스트
    """
    # 추출된 Q&A를 저장할 리스트
    extracted_qna = []

    # 각 페이지를 순회
    for page_data in json_data.get('contents', []):
        # 페이지별 상태 초기화
        if hasattr(add_qna_domain_onebyone, '_page_processed'):
            delattr(add_qna_domain_onebyone, '_page_processed')
        if hasattr(add_qna_domain_onebyone, '_page_domains'):
            delattr(add_qna_domain_onebyone, '_page_domains')
        if hasattr(add_qna_domain_onebyone, '_domain_index'):
            delattr(add_qna_domain_onebyone, '_domain_index')
            
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
                    
                    # Q&A 내용에서 tb, img, f, etc 태그 추출 (수정된 정규식)
                    tb_tags = re.findall(r'\{tb_\d{4}_\d{4}\}', qna_content)
                    img_tags = re.findall(r'\{img_\d{4}_\d{4}\}', qna_content)
                    f_tags = re.findall(r'\{f_\d{4}_\d{4}\}', qna_content)
                    etc_tags = re.findall(r'\{etc_\d{4}_\d{4}\}', qna_content)
                    footnote_tags = re.findall(r'\{note_\d{4}_\d{4}\}', qna_content)
                    additional_tags = tb_tags + img_tags + f_tags + etc_tags + footnote_tags
                    
                    # 디버깅: 추가 태그 발견 시 출력
                    # if additional_tags:
                    #     print(f"  추가 태그 발견 - Q&A: {tag}")
                    #     print(f"    TB: {tb_tags}, IMG: {img_tags}, F: {f_tags}, ETC: {etc_tags}, NOTE: {footnote_tags}")
                    
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
                    # indices_to_remove.add(qna_item_index)

                    # 질문 타입
                    qna_type = analyze_extracted_qna(qna_item)

                    # Domain 찾기
                    # with_domain_dir = "/Users/jinym/Desktop/Desktop_AICenter✨/SFAIcenter/data/FIN_workbook/1C/with_domain"
                    # qna_domain = find_domain_for_qna(qna_item, file_name, with_domain_dir)

                    # Domain 추가 (페이지의 모든 Q&A에 대해 한 번만 호출)
                    if not hasattr(add_qna_domain_onebyone, '_page_processed'):
                        try:
                            page_domains = add_qna_domain_onebyone(json_data, page_data, llm_model)
                            # JSON 파싱하여 도메인 리스트 저장
                            try:
                                if isinstance(page_domains, str):
                                    page_domains = json.loads(page_domains)
                            except json.JSONDecodeError:
                                print(f"  - JSON 파싱 실패, 빈 도메인으로 설정")
                                page_domains = []
                        except Exception as e:
                            print(f"  - API 호출 실패: {e}")
                            page_domains = []
                        # 페이지별 domain 정보를 저장
                        add_qna_domain_onebyone._page_processed = True
                        add_qna_domain_onebyone._page_domains = page_domains
                        add_qna_domain_onebyone._domain_index = 0
                    
                    # 각 Q&A에 해당하는 domain 순차적으로 할당
                    if hasattr(add_qna_domain_onebyone, '_page_domains') and add_qna_domain_onebyone._domain_index < len(add_qna_domain_onebyone._page_domains):
                        domain_obj = add_qna_domain_onebyone._page_domains[add_qna_domain_onebyone._domain_index]
                        qna_domain = domain_obj.get('카테고리', '') if isinstance(domain_obj, dict) else str(domain_obj)
                        qna_reason = domain_obj.get('근거', '') if isinstance(domain_obj, dict) else ''
                        add_qna_domain_onebyone._domain_index += 1
                    else:
                        qna_domain = ""
                        qna_reason = ""

                    # 추출할 Q&A 정보 저장
                    qna_items_to_extract.append({
                        # 'file_id': json_data.get("file_id"),
                        'file_id': file_name,
                        'title': json_data['title'],
                        'cat1_domain': json_data.get('cat1_domain'),
                        'cat2_sub': json_data.get('cat2_sub'),
                        'cat3_specific': json_data.get('cat3_specific'),
                        'chapter': page_data.get('chapter'),
                        'page': page_data.get('page'),
                        "qna_type": qna_type,
                        "qna_domain": qna_domain,
                        "qna_reason": qna_reason,
                        'qna_data': qna_item,
                        'additional_tags_found': additional_tags,
                        'additional_tag_data': additional_tag_data
                    })
            
            # 추출된 Q&A들을 리스트에 추가
            extracted_qna.extend(qna_items_to_extract)
            
            # 페이지별 중간저장 (임시 파일로)
            if qna_items_to_extract:
                temp_output_path = output_path.replace('.json', f'_temp_page_{page_data.get("page", "unknown")}.json')
                temp_dir = os.path.dirname(temp_output_path)
                os.makedirs(temp_dir, exist_ok=True)
                
                try:
                    with open(temp_output_path, 'w', encoding='utf-8') as f:
                        json.dump(qna_items_to_extract, f, ensure_ascii=False, indent=4)
                    print(f"  - 페이지 {page_data.get('page', 'unknown')} 중간저장: {len(qna_items_to_extract)}개 Q&A")
                except Exception as e:
                    print(f"  - 페이지 {page_data.get('page', 'unknown')} 중간저장 실패: {e}")
    
    
    return {
        'extracted_qna': extracted_qna
    }


def get_qna_datas(file_path: str, output_path: str = None, llm_model: str = None) -> Dict[str, Any]:
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
    result = extract_qna_tags(json_data, os.path.splitext(os.path.basename(file_path))[0], llm_model, output_path)    

    # 추출된 Q&A를 별도 파일로 저장
    if len(result['extracted_qna']) != 0:
        # 출력 디렉토리 생성
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        qna_output_path = output_path.replace('.json', '_extracted_qna.json')
        with open(qna_output_path, 'w', encoding='utf-8') as f:
            json.dump(result['extracted_qna'], f, ensure_ascii=False, indent=4)

        # 임시 파일들 개수 확인 및 삭제
        temp_files = []
        temp_qna_count = 0
        try:
            for file in os.listdir(output_dir):
                if file.startswith(os.path.basename(output_path).replace('.json', '_temp_page_')) and file.endswith('.json'):
                    temp_file_path = os.path.join(output_dir, file)
                    temp_files.append(temp_file_path)
                    
                    # 임시 파일의 Q&A 개수 확인
                    try:
                        with open(temp_file_path, 'r', encoding='utf-8') as f:
                            temp_data = json.load(f)
                            if isinstance(temp_data, list):
                                temp_qna_count += len(temp_data)
                    except Exception as e:
                        print(f"  - 임시 파일 {file} 읽기 오류: {e}")
            
            # 개수 검증
            final_qna_count = len(result['extracted_qna'])
            print(f"  - 임시 파일 Q&A 개수: {temp_qna_count}")
            print(f"  - 최종 파일 Q&A 개수: {final_qna_count}")
            
            if temp_qna_count == final_qna_count and temp_qna_count > 0:
                # 개수가 일치하면 임시 파일들 삭제
                temp_files_deleted = 0
                for temp_file_path in temp_files:
                    try:
                        os.remove(temp_file_path)
                        temp_files_deleted += 1
                    except Exception as e:
                        print(f"  - 임시 파일 삭제 오류: {e}")
                print(f"  - 임시 파일 {temp_files_deleted}개 삭제 완료")
            else:
                print(f"  - Q&A 개수가 일치하지 않아 임시 파일을 보존합니다.")
                print(f"  - 임시 파일 {len(temp_files)}개 보존됨")
                
        except Exception as e:
            print(f"  - 임시 파일 처리 중 오류: {e}")

        print(f"처리 완료:")
        print(f"- 추출된 Q&A: {qna_output_path}")
        print(f"- 추출된 Q&A 개수: {len(result['extracted_qna'])}")
        
        return result
    else:
        print(f"처리 완료: 추출된 Q&A가 없습니다.")
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
    


def replace_tags_in_text(text: str, additional_tag_data: list) -> str:
    """
    텍스트에서 {f_0000_0000}이나 {tb_0000_0000} 같은 태그를 additional_tag_data에서 찾아서 대치합니다.
    
    Args:
        text: 대치할 텍스트
        additional_tag_data: 태그 데이터 리스트
    
    Returns:
        태그가 대치된 텍스트
    """
    if not text or not additional_tag_data:
        return text
    
    # 태그 패턴 매칭: {f_0000_0000}, {tb_0000_0000}, {img_0000_0000}, {etc_0000_0000}, {note_0000_0000}
    tag_pattern = r'\{(f_\d{4}_\d{4}|tb_\d{4}_\d{4}|note_\d{4}_\d{4})\}'
    
    def replace_tag(match):
        tag_with_braces = match.group(0)  # {f_0000_0000}
        tag_without_braces = match.group(1)  # f_0000_0000
        
        # additional_tag_data에서 해당 태그 찾기
        for tag_data in additional_tag_data:
            if tag_data.get('tag') == tag_with_braces:
                # data 필드가 있는 경우
                if 'data' in tag_data:
                    data = tag_data.get('data', {})
                    if isinstance(data, dict):
                        # data에서 적절한 필드 찾기 (우선순위: content, text, description, caption)
                        for field in ['content', 'text', 'description', 'caption']:
                            if field in data and data[field]:
                                return str(data[field])
                        
                        # file_path가 있으면 파일명 표시
                        if 'file_path' in data and data['file_path']:
                            return f"[{os.path.basename(data['file_path'])}]"
                    
                    # data가 문자열이면 그대로 사용
                    elif isinstance(data, str) and data:
                        return data
                    
                    # data가 리스트면 첫 번째 요소 사용
                    elif isinstance(data, list) and data:
                        return str(data[0])
                
                # data 필드가 없는 경우, 직접 필드에서 찾기
                else:
                    # 직접 필드에서 적절한 내용 찾기 (우선순위: content, text, description, caption)
                    for field in ['content', 'text', 'description', 'caption']:
                        if field in tag_data and tag_data[field]:
                            return str(tag_data[field])
                    
                    # file_path가 있으면 파일명 표시
                    if 'file_path' in tag_data and tag_data['file_path']:
                        return f"[{os.path.basename(tag_data['file_path'])}]"
        
        # 태그를 찾지 못한 경우 원본 태그 유지
        return tag_with_braces
    
    return re.sub(tag_pattern, replace_tag, text)

def replace_tags_in_qna_data(qna_data: dict, additional_tag_data: list) -> dict:
    """
    Q&A 데이터의 question과 options에서 태그를 대치합니다.
    
    Args:
        qna_data: Q&A 데이터 딕셔너리 (전체 qna 객체 또는 qna_data 부분)
        additional_tag_data: 추가 태그 데이터 리스트
    
    Returns:
        태그가 대치된 Q&A 데이터
    """
    if not qna_data:
        return qna_data
    
    if not additional_tag_data:
        return qna_data
    
    # qna_data가 전체 qna 객체인 경우 qna_data 부분을 추출
    if 'qna_data' in qna_data:
        qna_info = qna_data['qna_data']
    else:
        # 이미 qna_data 부분만 전달된 경우
        qna_info = qna_data
    if 'description' in qna_info:
        desc = qna_info['description']
        
        # question 필드 처리
        if 'question' in desc and desc['question']:
            desc['question'] = replace_tags_in_text(desc['question'], additional_tag_data)
        
        # options 필드 처리 (리스트)
        if 'options' in desc and desc['options']:
            if isinstance(desc['options'], list):
                desc['options'] = [replace_tags_in_text(option, additional_tag_data) for option in desc['options']]
            else:
                desc['options'] = replace_tags_in_text(desc['options'], additional_tag_data)
        
        # answer 필드 처리
        if 'answer' in desc and desc['answer']:
            desc['answer'] = replace_tags_in_text(desc['answer'], additional_tag_data)
        
        # explanation 필드 처리
        if 'explanation' in desc and desc['explanation']:
            desc['explanation'] = replace_tags_in_text(desc['explanation'], additional_tag_data)
    
    return qna_data

def process_json_file_with_tag_replacement(file_path: str) -> bool:
    """
    JSON 파일을 로드하고 태그 대치를 수행한 후 저장합니다.
    
    Args:
        file_path: 처리할 JSON 파일 경로
    
    Returns:
        성공 여부
    """
    try:
        # JSON 파일 로드
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # extracted_qna 데이터가 있는 경우 처리
        if 'extracted_qna' in data and isinstance(data['extracted_qna'], list):
            print(f"Processing {os.path.basename(file_path)}: {len(data['extracted_qna'])} Q&A items")
            
            # 각 Q&A 항목에 대해 태그 대치 수행
            for i, qna_item in enumerate(data['extracted_qna']):
                data['extracted_qna'][i] = replace_tags_in_qna_data(qna_item)
            
            # 백업 파일 생성
            backup_path = file_path + '.backup'
            shutil.copy2(file_path, backup_path)
            print(f"Backup created: {backup_path}")
            
            # 수정된 데이터 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"Tag replacement completed for {os.path.basename(file_path)}")
            return True
        
        else:
            print(f"No extracted_qna data found in {os.path.basename(file_path)}")
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def process_all_json_files_with_tag_replacement(cycle: int, data_path: str = None) -> None:
    """
    지정된 사이클의 모든 JSON 파일에 대해 태그 대치를 수행합니다.
    
    Args:
        cycle: 사이클 번호 (1, 2, 3)
        data_path: 데이터 경로 (기본값: FINAL_DATA_PATH)
    """
    if data_path is None:
        data_path = FINAL_DATA_PATH
    
    final_path = os.path.join(data_path, CYCLE_PATH[cycle])
    
    if not os.path.exists(final_path):
        print(f"경로가 존재하지 않습니다: {final_path}")
        return
    
    print(f"Processing cycle {cycle} files in: {final_path}")
    print("=" * 60)
    
    # 모든 JSON 파일 찾기
    json_files = []
    for root, _, files in os.walk(final_path):
        for f in files:
            if f.endswith(".json") and ('_' not in f):
                json_files.append(os.path.join(root, f))
    
    if not json_files:
        print("처리할 JSON 파일이 없습니다.")
        return
    
    print(f"발견된 JSON 파일: {len(json_files)}개")
    
    # 각 파일 처리
    success_count = 0
    error_count = 0
    error_files = []
    
    for i, file_path in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] 처리 중: {os.path.basename(file_path)}")
        print("-" * 40)
        
        try:
            success = process_json_file_with_tag_replacement(file_path)
            if success:
                success_count += 1
                print(f"✅ {os.path.basename(file_path)} 처리 완료")
            else:
                error_count += 1
                error_files.append(os.path.basename(file_path))
                print(f"❌ {os.path.basename(file_path)} 처리 실패")
        except Exception as e:
            error_count += 1
            error_files.append(os.path.basename(file_path))
            print(f"❌ {os.path.basename(file_path)} 처리 실패: {e}")
    
    # 최종 결과 출력
    print("\n" + "=" * 60)
    print("전체 처리 완료!")
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {error_count}개")
    
    if error_files:
        print(f"실패한 파일: {', '.join(error_files)}")


# 사용 예시
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python ProcessFiles.py <cycle> [data_path]")
        print("")
        print("예시:")
        print("  python ProcessFiles.py 1  # 1차 사이클 파일 처리")
        print("  python ProcessFiles.py 2 /custom/path  # 2차 사이클, 커스텀 경로")
        sys.exit(1)
    
    cycle = int(sys.argv[1])
    data_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if cycle not in [1, 2, 3]:
        print("사이클은 1, 2, 3 중 하나여야 합니다.")
        sys.exit(1)
    
    process_all_json_files_with_tag_replacement(cycle, data_path)