import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from bs4 import BeautifulSoup

# 크롤링된 HTML 파일들이 저장된 디렉토리 경로
DATA_DIR = "html_data/공지 크롤링 모음_2025~2026년/" 

def analyze_character_distribution(data_dir):
    # 디렉토리 내의 모든 html 파일 찾기
    file_paths = glob.glob(os.path.join(data_dir, "*.html"))
    
    if not file_paths:
        print(f"경고: '{data_dir}' 폴더에 HTML 파일이 존재하지 않습니다. 경로를 확인해주세요.")
        return

    print(f"총 {len(file_paths)}개의 파일을 분석합니다. 잠시만 기다려주세요...\n")
    
    char_counts = []
    
    for path in file_paths:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
                
                # HTML 태그를 제거하고 순수 텍스트만 추출
                soup = BeautifulSoup(html_content, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                
                # 글자 수 저장
                char_counts.append(len(text))
        except Exception as e:
            print(f"파일 읽기 에러 ({path}): {e}")

    # pandas 데이터프레임으로 변환
    df = pd.DataFrame({"char_count": char_counts})
    
    # 1. 터미널에 통계 요약 출력
    print("=== 📊 수집된 페이지 글자 수 통계 요약 ===")
    print(df['char_count'].describe().to_string())
    print("==========================================\n")
    
    # 2. 분포 시각화 (히스토그램 & 밀도 그래프)
    plt.figure(figsize=(12, 7))
    sns.histplot(df["char_count"], bins=50, kde=True, color='#4C72B0')
    
    # 그래프 꾸미기
    plt.title("Distribution of Character Counts in Crawled Pages", fontsize=16, fontweight='bold')
    plt.xlabel("Character Count (Text only)", fontsize=14)
    plt.ylabel("Number of Pages (Frequency)", fontsize=14)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # 평균선 표시 (빨간 점선)
    mean_val = df["char_count"].mean()
    plt.axvline(mean_val, color='red', linestyle='dashed', linewidth=2, label=f'Mean: {mean_val:.0f}')
    plt.legend()
    
    # 이미지로 저장
    save_path = "char_length_distribution.png"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✅ 분포 그래프가 '{save_path}' 이미지 파일로 저장되었습니다!")

if __name__ == "__main__":
    analyze_character_distribution(DATA_DIR)