import json
import os
import sys
import warnings
import shutil
import re
import glob

# 상위 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ProcessFiles as pf
from question_answer import ProcessQnA as pq


def find_last_processed_page(extracted_dir, file_name):
    """
    특정 파일의 마지막으로 처리된 페이지 번호를 찾는 함수
    
    Args:
        extracted_dir: extracted 디렉토리 경로
        file_name: 파일명 (확장자 제외)
        
    Returns:
        마지막으로 처리된 페이지 번호 (없으면 0)
    """
    # tmp 파일 패턴: {file_name}_temp_page_{page_number}.json
    pattern = os.path.join(extracted_dir, f"{file_name}_temp_page_*.json")
    tmp_files = glob.glob(pattern)
    
    if not tmp_files:
        return 0
    
    # 페이지 번호 추출
    page_numbers = []
    for tmp_file in tmp_files:
        # 파일명에서 페이지 번호 추출
        match = re.search(r'_temp_page_(\d+)\.json$', tmp_file)
        if match:
            page_numbers.append(int(match.group(1)))
    
    if not page_numbers:
        return 0
    
    return max(page_numbers)


def get_remaining_pages(json_data, start_page):
    """
    시작 페이지부터 처리해야 할 페이지들을 반환하는 함수
    
    Args:
        json_data: JSON 데이터
        start_page: 시작 페이지 번호
        
    Returns:
        처리해야 할 페이지 데이터 리스트
    """
    remaining_pages = []
    for page_data in json_data.get('contents', []):
        page_num = page_data.get('page', 0)
        if int(page_num) >= start_page:
            remaining_pages.append(page_data)
    
    return remaining_pages


ONEDRIVE_PATH = os.path.join(os.path.expanduser("~"), "Library/CloudStorage/OneDrive-개인/데이터L/selectstar")

def main(cycle: int):
    """
    Q&A 추출 메인 함수

    Args:
        cycle: 사이클 번호 (1, 2, 3)
    """
    # 경로 처리 개선: replace() 대신 os.path.join() 사용
    origin_data_dir = os.path.join(ONEDRIVE_PATH, 'data/FINAL')
    data_dir = os.path.join(ONEDRIVE_PATH, f'evaluation/workbook_data/{cycle}C')
    
    print(f"원본 데이터 경로: {origin_data_dir}")
    print(f"작업 데이터 경로: {data_dir}")

    json_files = pf.get_filelist(cycle, data_path=origin_data_dir)
    json_files = [file for file in json_files if 'Lv5' in file]

    # extracted 디렉토리 경로
    extracted_dir = os.path.join(data_dir, 'Lv5')

    # 모든 JSON 파일 일괄 처리
    print(f"총 {len(json_files)}개의 JSON 파일을 찾았습니다.")

    total_extracted = 0
    processed_files = 0

    for i, json_file in enumerate(json_files):
        try:
            print(f"\n[{i+1}/{len(json_files)}] 처리 중: {os.path.basename(json_file)}")
            
            # 파일명 (확장자 제외)
            name = os.path.splitext(os.path.basename(json_file))[0]
            
            # 완전히 처리된 파일인지 확인
            final_file = os.path.join(extracted_dir, f"{name}_extracted_qna.json")
            if os.path.exists(final_file):
                print(f"- 이미 완전히 처리된 파일입니다: {os.path.basename(final_file)}")
                continue
            
            # 마지막으로 처리된 페이지 확인
            last_processed_page = find_last_processed_page(extracted_dir, name)
            
            if last_processed_page > 0:
                print(f"- 마지막 처리된 페이지: {last_processed_page}")
                print(f"- 페이지 {last_processed_page + 1}부터 재개합니다.")
                
                # JSON 파일 읽기
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"  - JSON 파싱 오류: {e}")
                    continue
                except FileNotFoundError as e:
                    print(f"  - 파일을 찾을 수 없음: {e}")
                    continue
                except Exception as e:
                    print(f"  - 파일 읽기 오류: {e}")
                    continue
                
                # 남은 페이지들만 처리
                remaining_pages = get_remaining_pages(json_data, last_processed_page + 1)
                
                if not remaining_pages:
                    print(f"- 이미 모든 페이지가 처리되었습니다.")
                    continue
                
                print(f"- 처리할 페이지: {len(remaining_pages)}개")
                
                # 남은 페이지들만으로 새로운 JSON 데이터 생성
                json_data['contents'] = remaining_pages
                
                # 임시 파일로 저장
                temp_file = os.path.join(data_dir, f"{name}_temp_resume.json")
                try:
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    print(f"  - 임시 파일 저장 오류: {e}")
                    continue
                
                # 임시 파일로 처리 (file_id를 올바르게 설정하기 위해 직접 호출)
                try:
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        temp_json_data = json.load(f)
                except Exception as e:
                    print(f"  - 임시 파일 읽기 오류: {e}")
                    continue
                
                # file_id를 올바르게 설정
                result = pq.extract_qna_tags(temp_json_data, name, os.path.join(extracted_dir, f"{name}.json"))
                
                # 최종 파일 저장
                if len(result['extracted_qna']) != 0:
                    qna_output_path = os.path.join(extracted_dir, f"{name}_extracted_qna.json")
                    with open(qna_output_path, 'w', encoding='utf-8') as f:
                        json.dump(result['extracted_qna'], f, ensure_ascii=False, indent=4)
                
                # 기존 임시 파일들과 통합
                existing_qna = []
                temp_files = glob.glob(os.path.join(extracted_dir, f"{name}_temp_page_*.json"))
                for temp_file_path in temp_files:
                    try:
                        with open(temp_file_path, 'r', encoding='utf-8') as f:
                            temp_data = json.load(f)
                            if isinstance(temp_data, list):
                                existing_qna.extend(temp_data)
                    except Exception as e:
                        print(f"  - 기존 임시 파일 읽기 오류: {e}")
                
                # 기존 Q&A와 새로 처리된 Q&A 통합
                all_qna = existing_qna + result['extracted_qna']
                
                # 통합된 결과를 최종 파일로 저장
                final_output_path = os.path.join(extracted_dir, f"{name}_extracted_qna.json")
                with open(final_output_path, 'w', encoding='utf-8') as f:
                    json.dump(all_qna, f, ensure_ascii=False, indent=4)
                
                # 개수 검증 후 임시 파일들 삭제
                temp_qna_count = len(existing_qna) + len(result['extracted_qna'])
                final_qna_count = len(all_qna)
                
                print(f"  - 기존 임시 파일 Q&A: {len(existing_qna)}개")
                print(f"  - 새로 처리된 Q&A: {len(result['extracted_qna'])}개")
                print(f"  - 총 Q&A: {final_qna_count}개")
                
                if temp_qna_count == final_qna_count and final_qna_count > 0:
                    # 모든 임시 파일들 삭제
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
                
                # 임시 파일 삭제
                os.remove(temp_file)
                
                # 결과 업데이트
                result['extracted_qna'] = all_qna
                
            else:
                print(f"- 처음부터 처리합니다.")
                # 처음부터 처리
                result = pq.get_qna_datas(json_file, os.path.join(extracted_dir, f"{name}.json"))
            
            total_extracted += len(result['extracted_qna'])
            processed_files += 1
            
            print(f"- 추출된 Q&A: {len(result['extracted_qna'])}개")
            
        except Exception as e:
            print(f"  - 오류 발생: {e}")

    print(f"\n=== 전체 처리 결과 ===")
    print(f"- 처리된 파일: {processed_files}/{len(json_files)}")
    print(f"- 총 추출된 Q&A: {total_extracted}개")


if __name__ == "__main__":
    # 명령행 인수 처리
    if len(sys.argv) != 3:
        print("사용법: python qna_extract.py <cycle>")
        print("예시: python qna_extract.py 1")
        sys.exit(1)
    

    try:
        cycle = int(sys.argv[2])
        if cycle not in [1, 2, 3]:
            print("cycle은 1, 2, 3 중 하나여야 합니다.")
            sys.exit(1)
    except ValueError:
        print("cycle은 정수여야 합니다.")
        sys.exit(1)
    
    # 메인 함수 실행
    main(cycle)