import os
import re
import time
import requests
from bs4 import BeautifulSoup

def kw_recent_notice_crawler(max_pages=50):
    """
    광운대학교 공지사항 최신 데이터를 노이즈 없이 크롤링하여 저장하는 스크립트 (Linux 호환)
    - 조회수 필터링을 제거하여 오래된 공지 대신 '최신 공지사항' 위주로 대량 수집합니다.
    - 전체 HTML(res.text) 대신 본문 영역 엘리먼트만 타겟팅하여 내비게이션/푸터 등의 임베딩 노이즈를 방지합니다.
    - Linux 터미널 환경에서 가독성이 좋고, 쉘 스크립트 핸들링이 용이하도록 파일명과 경로를 최적화했습니다.
    """
    base_url = "https://www.kw.ac.kr/ko/life/notice.jsp"
    
    # Linux 환경을 고려한 표준 User-Agent 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 레포지토리의 embed.py 내 HTML_BASE 기본 설정에 맞춰 폴더 생성
    output_dir = 'html_data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[{output_dir}] 폴더를 생성했습니다.")

    all_notices = []
    
    print(f"--- [1단계] 최신 {max_pages}페이지까지 공지사항 목록 수집 시작 ---")
    for page in range(1, max_pages + 1):
        params = {'MaxRows': 10, 'tpage': page}
        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"    Page {page} 접근 실패 (상태 코드: {response.status_code})")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('.board-list-box ul li')
            
            if not items:
                print(f"    Page {page}에 게시글이 없습니다. 수집을 종료합니다.")
                break
                
            for item in items:
                anchor = item.select_one('.board-text a')
                if not anchor: 
                    continue
                
                # 제목 내 노이즈 텍스트 제거 및 정제
                title = anchor.get_text(strip=True).replace('신규게시글', '').replace('Attachment', '').strip()
                link = "https://www.kw.ac.kr" + anchor['href']
                
                # 메타 정보 파싱 (조회수, 작성일)
                info_element = item.select_one('p.info')
                info_text = info_element.get_text() if info_element else ""
                
                # 조회수 정규식 추출
                view_match = re.search(r'조회수\s*(\d+)', info_text)
                views = int(view_match.group(1)) if view_match else 0
                
                # 작성일 정규식 추출 (YYYY-MM-DD)
                date_match = re.search(r'작성일\s*(\d{4}-\d{2}-\d{2})', info_text)
                post_date = date_match.group(1) if date_match else "0000-00-00"
                
                all_notices.append({
                    'title': title, 
                    'views': views, 
                    'date': post_date, 
                    'link': link
                })
            
            print(f"    Page {page}/{max_pages} 목록 확보 완료 (누적 {len(all_notices)}개)")
            time.sleep(0.4)  # 목록 수집 간 리스펙트 타임
            
        except Exception as e:
            print(f"    Page {page} 목록 수집 중 오류 발생: {e}")

    print(f"\n--- [2단계] 총 {len(all_notices)}개 공지사항 본문 정밀 추출 및 클린 HTML 생성 시작 ---")
    
    # Linux 파일 시스템 규칙 및 CLI 셸 자동완성(Tab)을 고려한 안전한 파일명 변환기
    def safe_linux_filename(text):
        # 리눅스에서 금지되는 기호(/) 및 제어문자 제거, 윈도우 호환성용 문자도 함께 예방 정제
        text = re.sub(r'[\x00/\\*?:"<>|]', '', text)
        # 셸 주소 입력 시 이스케이프(\ ) 불편을 방지하기 위해 띄어쓰기를 언더바(_)로 치환
        text = text.strip().replace(' ', '_')
        return text[:45]

    for i, notice in enumerate(all_notices, 1):
        try:
            res = requests.get(notice['link'], headers=headers, timeout=10)
            if res.status_code != 200:
                print(f"    [{i}/{len(all_notices)}] 상세페이지 접근 실패 (코드: {res.status_code}) - {notice['title']}")
                continue
                
            detail_soup = BeautifulSoup(res.text, 'html.parser')
            
            # [핵심] 상/하단 공통 메뉴, 내비게이션바, 푸터를 제외한 '순수 공지 본문 틀'만 타겟팅
            content_area = None
            for selector in ['.board-view-wrap', '.board-view', '.view-con', '.board-content', '.board-text']:
                content_area = detail_soup.select_one(selector)
                if content_area:
                    break
            
            # 클래스가 매칭되지 않는 비표준 페이지일 경우 body 전체를 대체재로 설정
            if not content_area:
                content_area = detail_soup.find('body')
            
            # RAG 임베딩(Chunking)에 불필요한 스크립트나 스타일 태그가 본문 내부에 있다면 제거하여 완전 정제
            if content_area:
                for trash in content_area.select('script, style, iframe'):
                    trash.extract()
            
            # 오직 지식 데이터만 압축 보관하는 최소화된 규격의 클린 HTML 구조 선언
            clean_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{notice['title']}</title>
</head>
<body>
<div class="notice-container">
    <h1>{notice['title']}</h1>
    <div class="notice-meta">
        <p>작성일: {notice['date']} | 조회수: {notice['views']}</p>
        <p>원문 출처: <a href="{notice['link']}">{notice['link']}</a></p>
    </div>
    <hr>
    <div class="notice-body">
        {content_area.prettify() if content_area else "본문 내용을 불러올 수 없습니다."}
    </div>
</div>
</body>
</html>"""
            
            # 파일네임 포맷팅 (정렬 편의를 위해 인덱스 및 날짜 배치)
            clean_title = safe_linux_filename(notice['title'])
            file_name = f"{i:04d}_{notice['date']}_{clean_title}.html"
            
            # Linux 표준 경로 조인 시스템 (os.path.join)을 통한 안전한 파일 생성
            file_path = os.path.join(output_dir, file_name)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(clean_html)
                
            print(f"    [{i}/{len(all_notices)}] 저장 완료 -> {file_name}")
            
            # 리눅스 백그라운드 데몬 가동 및 서버 방화벽 차단 예방을 위한 필수 지연(Sleep) 시간 설정
            time.sleep(1.0)
            
        except Exception as e:
            print(f"    [{i}/{len(all_notices)}] 본문 다운로드 중 예외 발생: {e}")

    print(f"\n 수집 작업이 최종 완료되었습니다!")
    print(f" 출력 폴더: {os.path.abspath(output_dir)}")
    print(f" 생성된 문서 수: {len(os.listdir(output_dir))}개")

if __name__ == "__main__":
    # max_pages=50 설정 시 최신 약 500개의 공지사항을 수집합니다.
    # 챗봇의 백과사전식 지식 가버리지를 확보하고 싶다면 100~150페이지까지 확장 구동하셔도 좋습니다.
    kw_recent_notice_crawler(max_pages=50)