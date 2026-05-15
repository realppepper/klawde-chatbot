import requests
import tomllib
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tavily import TavilyClient
import os
import time
import re

# ───────────────────────────────────────────
# 설정 (필요시 여기서 수정)
# ───────────────────────────────────────────
with open(".streamlit/api.toml", "rb") as f:
    _secrets = tomllib.load(f)
TAVILY_API_KEY = _secrets["TAVILY_API_KEY"]
tavily = TavilyClient(api_key=TAVILY_API_KEY)

LIST_URL = "https://www.kw.ac.kr/ko/life/notice.jsp?srCategoryId=&mode=list&searchKey=1&searchVal="
MAX_NOTICES = 5          # 가져올 공지사항 개수
OUTPUT_BASE = "./html_data"  # HTML 파일 저장 기본 폴더
DELAY = 1.5              # 요청 간 딜레이 (초) — 서버 과부하 방지

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/91.0.4472.124 Safari/537.36'
}

# ───────────────────────────────────────────
# 파일명에 사용 불가한 문자 제거
# ───────────────────────────────────────────
def safe_filename(title: str) -> str:
    title = re.sub(r'[\\/*?:"<>|]', '', title)
    title = title.strip().replace(' ', '_')
    return title[:50]  # 너무 길면 자르기

# ───────────────────────────────────────────
# 공지사항 목록 가져오기
# ───────────────────────────────────────────
def get_notice_list(max_count: int) -> list:
    print("공지사항 목록을 가져오는 중...")
    response = requests.get(LIST_URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')

    notices = []
    for a_tag in soup.find_all('a', href=True):
        if 'BoardMode=view' in a_tag['href']:
            title = a_tag.get_text(separator=' ', strip=True)
            if title:
                link = urljoin(LIST_URL, a_tag['href'])
                if not any(n['link'] == link for n in notices):
                    notices.append({'title': title, 'link': link})
                    if len(notices) >= max_count:
                        break

    print(f"총 {len(notices)}개 공지사항 발견\n")
    return notices

# ───────────────────────────────────────────
# 공지사항 상세 내용 가져오기
# ───────────────────────────────────────────
def get_notice_detail(notice: dict) -> dict:
    url = notice['link']

    # 본문 추출 (Tavily extract — BS4보다 깔끔한 텍스트 제공)
    content_text = "본문 내용을 불러올 수 없습니다."
    try:
        extract_result = tavily.extract(urls=[url])
        if extract_result.get("results"):
            content_text = extract_result["results"][0].get("raw_content", content_text).strip()
    except Exception as e:
        print(f"  Tavily 추출 실패 ({e}), BeautifulSoup으로 대체 시도...")
        try:
            fallback_resp = requests.get(url, headers=HEADERS)
            fallback_soup = BeautifulSoup(fallback_resp.text, 'html.parser')
            for sel in ['.board-text', '.board-view-wrap', '.view-con', '.board-content']:
                area = fallback_soup.select_one(sel)
                if area:
                    content_text = area.get_text(separator='\n\n', strip=True)
                    break
        except Exception:
            pass

    # 메타데이터 추출 (등록일 / 조회수 / 첨부파일 — BS4 직접 파싱)
    post_resp = requests.get(url, headers=HEADERS)
    post_soup = BeautifulSoup(post_resp.text, 'html.parser')

    # 등록일 / 조회수 추출
    date_text = "확인 불가"
    views_text = "확인 불가"
    for info in post_soup.find_all(['dd', 'li', 'td', 'span', 'th']):
        text = info.get_text(strip=True)
        if "등록일" in text or "작성일" in text:
            clean = text.replace("등록일", "").replace("작성일", "").replace(":", "").strip()
            if clean:
                date_text = clean
            else:
                nxt = info.find_next_sibling(['dd', 'li', 'td', 'span'])
                if nxt:
                    date_text = nxt.get_text(strip=True)
        elif "조회" in text or "조회수" in text:
            clean = text.replace("조회수", "").replace("조회", "").replace(":", "").strip()
            if clean:
                views_text = clean
            else:
                nxt = info.find_next_sibling(['dd', 'li', 'td', 'span'])
                if nxt:
                    views_text = nxt.get_text(strip=True)

    # 첨부파일 추출
    attachments = []
    attach_links = post_soup.select('a[href*="download"], a[href*="Down"]')
    if not attach_links:
        attach_links = post_soup.select('.board-attachment a, .file-list a, .file a')
    for a in attach_links:
        file_name = a.get_text(strip=True) or "첨부파일"
        file_link = urljoin(LIST_URL, a['href'])
        if "javascript" not in file_link.lower():
            attachments.append({'name': file_name, 'link': file_link})

    return {
        'title': notice['title'],
        'link': notice['link'],
        'date': date_text,
        'views': views_text,
        'content': content_text,
        'attachments': attachments
    }

# ───────────────────────────────────────────
# HTML 파일로 저장 (공지사항 1개 = 파일 1개)
# ───────────────────────────────────────────
def save_as_html(item: dict, idx: int, output_dir: str):
    attachments_html = ""
    if item['attachments']:
        links = "".join(f"<li><a href='{a['link']}' target='_blank'>{a['name']}</a></li>" for a in item['attachments'])
        attachments_html = f"<div class='attachments'><strong>📎 첨부파일</strong><ul>{links}</ul></div>"

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{item['title']}</title>
<style>
  body {{ font-family: 'Malgun Gothic', sans-serif; line-height: 1.7; padding: 24px; background: #f4f4f9; }}
  .notice {{ background: #fff; border: 1px solid #ddd; padding: 24px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.08); }}
  h1 {{ color: #003087; font-size: 1.3em; border-bottom: 2px solid #003087; padding-bottom: 8px; }}
  .info {{ background: #f9f9f9; padding: 10px 14px; border-radius: 5px; font-size: 0.9em; color: #555; margin-bottom: 16px; }}
  .content {{ white-space: pre-wrap; font-size: 1em; color: #333; }}
  .attachments {{ margin-top: 16px; padding: 12px; background: #eef2f5; border-radius: 5px; }}
  a {{ color: #0056b3; }}
</style>
</head>
<body>
<div class="notice">
  <h1>{item['title']}</h1>
  <div class="info">
    등록일: {item['date']} &nbsp;|&nbsp; 조회수: {item['views']}<br>
    원문: <a href="{item['link']}" target="_blank">{item['link']}</a>
  </div>
  <div class="content">{item['content']}</div>
  {attachments_html}
</div>
</body>
</html>"""

    filename = f"{idx:03d}_{safe_filename(item['title'])}.html"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filename

# ───────────────────────────────────────────
# 메인 실행
# ───────────────────────────────────────────
if __name__ == "__main__":
    OUTPUT_DIR = OUTPUT_BASE
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    notices = get_notice_list(MAX_NOTICES)

    for idx, notice in enumerate(notices, 1):
        print(f"[{idx}/{len(notices)}] 수집 중: {notice['title']}")
        try:
            detail = get_notice_detail(notice)
            filename = save_as_html(detail, idx, OUTPUT_DIR)
            print(f"  → 저장 완료: {filename}")
        except Exception as e:
            print(f"  → 수집 실패: {e}")

        if idx < len(notices):
            time.sleep(DELAY)

    print(f"\n완료! '{OUTPUT_DIR}' 폴더에 {len(notices)}개 파일이 저장됐습니다.")
