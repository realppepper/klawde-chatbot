import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

import json
import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

def analyze_attachment_distribution(json_path='html_data/attachments.json', output_dir='analytics_result'):
    """
    JSON 파일 내 첨부파일 텍스트의 다양한 통계적 확률 분포를 분석하는 함수
    """
    # 1. 리눅스 서버 환경을 고려하여 GUI 화면 없이 파일 저장 전용 모드(Agg) 설정
    plt.switch_backend('Agg')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"--- [1단계] 데이터 로드 및 통계 메트릭 계산 시작 ({json_path}) ---")
    if not os.path.exists(json_path):
        print(f"오류: 지정한 경로에 JSON 파일이 없습니다: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 파싱 데이터 추출 및 데이터프레임 생성
    metrics = []
    for item in data:
        text = item.get('text', '').strip()
        if not text:
            continue
            
        char_count = len(text)
        words = text.split()
        word_count = len(words)
        unique_word_count = len(set(words))
        
        # [수정 완료] 정규식 re.split을 사용하여 문자열을 안정적으로 문장 단위 분리
        sentences = [s for s in re.split(r'[.!?]\s', text) if len(s.strip()) > 0]
        sentence_count = max(len(sentences), 1)
        
        metrics.append({
            'filename': item.get('filename', 'Unknown'),
            'char_count': char_count,
            'word_count': word_count,
            'lexical_diversity': unique_word_count / word_count if word_count > 0 else 0,
            'avg_word_per_sentence': word_count / sentence_count
        })

    df = pd.DataFrame(metrics)
    if df.empty:
        print("분석할 유효한 텍스트 데이터가 데이터셋에 존재하지 않습니다.")
        return

    print(f"총 {len(df)}개의 첨부파일 텍스트 문서 분석을 시작합니다.")

    print("\n--- [2단계] 기술 통계 가독성 요약 (Descriptive Statistics) ---")
    desc_stats = df[['char_count', 'word_count', 'lexical_diversity']].describe()
    print(desc_stats)
    desc_stats.to_csv(os.path.join(output_dir, 'descriptive_statistics.csv'))

    print("\n--- [3단계] 고등 확률 분포 특징 추출 (Shape of Distribution) ---")
    for col in ['char_count', 'word_count']:
        skewness = stats.skew(df[col])
        kurtosis = stats.kurtosis(df[col])
        print(f"[{col}]")
        print(f"  - 왜도 (Skewness): {skewness:.4f}")
        print(f"  - 첨도 (Kurtosis): {kurtosis:.4f}")
        
        if 3 <= len(df) <= 5000:
            shapiro_stat, p_val = stats.shapiro(df[col])
            print(f"  - 정규성 검정 (Shapiro-Wilk P-value): {p_val:.4e}")

    print("\n--- [4단계] 시각화 및 확률 밀도 함수(KDE) 그래프 생성 시작 ---")
    sns.set_theme(style="whitegrid")
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.histplot(df['char_count'], kde=True, ax=axes[0], color='skyblue', stat="density")
    axes[0].set_title('Document Character Count Distribution (KDE)', fontsize=13)
    axes[0].set_xlabel('Character Count')
    axes[0].set_ylabel('Probability Density')

    sns.histplot(df['word_count'], kde=True, ax=axes[1], color='salmon', stat="density")
    axes[1].set_title('Document Word Count Distribution (KDE)', fontsize=13)
    axes[1].set_xlabel('Word Count')
    axes[1].set_ylabel('Probability Density')
    
    plt.tight_layout()
    chart1_path = os.path.join(output_dir, 'text_length_distributions.png')
    plt.savefig(chart1_path, dpi=200)
    plt.close()
    print(f"-> 분포 차트 저장 완료: {chart1_path}")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.boxplot(x=df['char_count'], ax=axes[0], color='lightgreen')
    axes[0].set_title('Character Count Outliers Detection (Boxplot)', fontsize=13)
    
    sns.boxplot(x=df['lexical_diversity'], ax=axes[1], color='orchid')
    axes[1].set_title('Lexical Diversity Distribution [Unique/Total]', fontsize=13)
    
    plt.tight_layout()
    chart2_path = os.path.join(output_dir, 'outliers_boxplots.png')
    plt.savefig(chart2_path, dpi=200)
    plt.close()
    print(f"-> 아웃라이어 이상치 분석 차트 저장 완료: {chart2_path}")

    print(f"\n 모든 통계 분석이 완료되었습니다. 결과물이 '{output_dir}' 폴더에 보관되었습니다.")

if __name__ == "__main__":
    # 필요한 경우 내 json 파일의 경로를 인자로 수정하여 실행 가능
    import re # 내부 정규식용 임포트 유연성 확보
    analyze_attachment_distribution(json_path='html_data/extracted_documents.json')