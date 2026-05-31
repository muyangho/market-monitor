import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.request
import warnings
import FinanceDataReader as fdr
import re
from concurrent.futures import ThreadPoolExecutor

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Master Market Monitor", layout="wide", initial_sidebar_state="expanded")

# --- 1. 지수별 본지수 & 선물지수 매핑 ---
INDEX_MAP = {
    "NASDAQ 100": {
        "index_ticker": "^NDX", "index_name": "나스닥 100 본지수 (^NDX)",
        "future_ticker": "NQ=F", "future_name": "나스닥 100 선물 (NQ=F)"
    },
    "S&P 500": {
        "index_ticker": "^GSPC", "index_name": "S&P 500 본지수 (^GSPC)",
        "future_ticker": "ES=F", "future_name": "S&P 500 선물 (ES=F)"
    },
    "DOW 30": {
        "index_ticker": "^DJI", "index_name": "다우존스 30 본지수 (^DJI)",
        "future_ticker": "YM=F", "future_name": "다우존스 선물 (YM=F)"
    },
    "PHLX Semiconductor (SOX)": {
        "index_ticker": "^SOX", "index_name": "필라델피아 반도체 지수 (^SOX)",
        "future_ticker": None, "future_name": None
    },
    "KOSPI 100 (대형주)": {
        "index_ticker": "^KS11", "index_name": "코스피 종합지수 (^KS11)",
        "future_ticker": None, "future_name": None
    },
    "KOSDAQ 100 (대형주)": {
        "index_ticker": "^KQ11", "index_name": "코스닥 종합지수 (^KQ11)",
        "future_ticker": None, "future_name": None
    }
}

# --- 단일 지표 호출 함수 ---
def get_metric_data(ticker):
    if not ticker: return None
    try:
        data = yf.download(ticker, period="5d", progress=False)['Close']
        if len(data) >= 2:
            current = float(data.iloc[-1])
            prev = float(data.iloc[-2])
            change = ((current - prev) / prev) * 100
            return current, change
    except:
        pass
    return None

# --- 2. yfinance 병렬(Multi-threading) 세부 섹터 수집 ---
def fetch_yf_industry(ticker):
    try:
        info = yf.Ticker(ticker).info
        return ticker, info.get('industry', info.get('sector', ''))
    except:
        return ticker, ''

def get_detailed_sectors_dict(tickers):
    sectors_dict = {}
    # 모바일 등에서의 API 차단/오류 방지를 위해 max_workers를 20에서 5로 하향
    with ThreadPoolExecutor(max_workers=5) as executor:
        for t, s in executor.map(fetch_yf_industry, tickers):
            if s: sectors_dict[t] = s
    return sectors_dict

# --- 3. 고도화된 한글 딥섹터 번역 로직 ---
def translate_sector(text):
    if pd.isna(text) or not str(text).strip(): return "일반 산업"
    text_str = str(text)

    if re.search('[가-힣]', text_str):
        if "반도체" in text_str: return "반도체 및 관련장비"
        if "소프트웨어" in text_str: return "소프트웨어 및 IT"
        if "제약" in text_str or "바이오" in text_str or "의약" in text_str: return "바이오/제약"
        if "자동차" in text_str: return "자동차 및 부품"
        if "은행" in text_str or "금융" in text_str: return "은행 및 금융"
        if "화학" in text_str: return "화학 및 소재"
        if "전자" in text_str: return "소비자 가전 및 부품"
        if "통신" in text_str: return "통신 서비스"
        return text_str

    eng_lower = text_str.lower()

    if "semiconductor equipment" in eng_lower: return "반도체 장비/소재"
    if "semiconductor" in eng_lower: return "반도체 설계/제조"
    if "software - infrastructure" in eng_lower or "systems software" in eng_lower: return "시스템 소프트웨어"
    if "software - application" in eng_lower or "application software" in eng_lower: return "응용 소프트웨어"
    if "information technology" in eng_lower or "it services" in eng_lower: return "IT 서비스/컨설팅"
    if "internet content" in eng_lower or "interactive media" in eng_lower: return "인터넷 미디어/콘텐츠"
    if "consumer electronics" in eng_lower: return "소비자 가전"
    if "computer hardware" in eng_lower or "electronic components" in eng_lower: return "컴퓨터/전자기기 부품"
    if "communication equipment" in eng_lower: return "통신 장비"
    if "auto manufacturer" in eng_lower or "automobile" in eng_lower: return "자동차 제조"
    if "auto parts" in eng_lower: return "자동차 부품"
    if "biotechnology" in eng_lower: return "바이오/생명공학"
    if "drug manufacturer" in eng_lower or "pharmaceutical" in eng_lower: return "제약"
    if "medical device" in eng_lower or "health care equipment" in eng_lower: return "의료 기기 및 장비"
    if "health care plans" in eng_lower or "medical care" in eng_lower: return "의료 서비스"
    if "bank" in eng_lower: return "은행"
    if "credit service" in eng_lower or "consumer finance" in eng_lower: return "소비자 금융/결제"
    if "capital market" in eng_lower or "asset management" in eng_lower: return "자산운용 및 투자"
    if "insurance" in eng_lower: return "보험"
    if "real estate" in eng_lower or "reit" in eng_lower: return "부동산/리츠"
    if "retail" in eng_lower: return "소매 유통"
    if "restaurant" in eng_lower: return "외식 및 식음료 서비스"
    if "packaged food" in eng_lower or "beverage" in eng_lower: return "식음료품"
    if "apparel" in eng_lower or "footwear" in eng_lower: return "의류 및 소비재"
    if "household" in eng_lower or "personal care" in eng_lower: return "가정/생활용품"
    if "aerospace" in eng_lower or "defense" in eng_lower: return "항공우주 및 국방"
    if "airline" in eng_lower or "travel" in eng_lower: return "항공 및 운송"
    if "entertainment" in eng_lower or "broadcasting" in eng_lower: return "미디어 및 엔터"
    if "telecom" in eng_lower: return "통신망/네트워크"
    if "oil" in eng_lower or "gas" in eng_lower or "energy" in eng_lower: return "에너지 및 석유"
    if "chemical" in eng_lower: return "화학/소재"
    if "utilities" in eng_lower: return "유틸리티(전력/가스)"
    if "machinery" in eng_lower or "industrial" in eng_lower: return "산업 기계 및 인프라"
    if "steel" in eng_lower or "metal" in eng_lower: return "철강 및 금속"

    return "기타 통합 산업"

# --- 4. 동적 구성 종목 추출 및 섹터 병합 ---
@st.cache_data(ttl=86400)
def get_index_components(index_name):
    try:
        if index_name == "S&P 500":
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            df = pd.read_html(urllib.request.urlopen(req).read())[0]
            df['Symbol'] = df['Symbol'].str.replace('.', '-', regex=False)
            df['Sector'] = df['GICS Sub-Industry'].apply(translate_sector)
            return df[['Symbol', 'Security', 'Sector']]

        elif index_name == "NASDAQ 100":
            url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            dfs = pd.read_html(urllib.request.urlopen(req).read())
            for df in dfs:
                if 'Ticker' in df.columns or 'Symbol' in df.columns:
                    sym_col = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
                    df = df.rename(columns={sym_col: 'Symbol', 'Company': 'Security'})
                    yf_sectors = get_detailed_sectors_dict(df['Symbol'].tolist())

                    def map_nasdaq_sector(row):
                        yf_sec = yf_sectors.get(row['Symbol'], '')
                        if yf_sec: return translate_sector(yf_sec)
                        wiki_sec = row.get('GICS Sub-Industry', row.get('GICS Sector', 'Technology'))
                        return translate_sector(wiki_sec)

                    df['Sector'] = df.apply(map_nasdaq_sector, axis=1)
                    return df[['Symbol', 'Security', 'Sector']]

        elif index_name == "DOW 30":
            url = 'https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            dfs = pd.read_html(urllib.request.urlopen(req).read())
            for df in dfs:
                if 'Symbol' in df.columns:
                    sec_col = 'Company' if 'Company' in df.columns else 'Security'
                    df = df.rename(columns={sec_col: 'Security'})
                    yf_sectors = get_detailed_sectors_dict(df['Symbol'].tolist())
                    df['Sector'] = df['Symbol'].apply(lambda x: translate_sector(yf_sectors.get(x, '다우 30 산업')))
                    return df[['Symbol', 'Security', 'Sector']]

        elif index_name == "PHLX Semiconductor (SOX)":
            sox_data = [
                ("AMD", "Advanced Micro Devices", "반도체 설계/제조"), ("ADI", "Analog Devices", "반도체 설계/제조"),
                ("AMAT", "Applied Materials", "반도체 장비/소재"), ("ASML", "ASML Holding", "반도체 장비/소재"),
                ("AVGO", "Broadcom", "반도체 설계/제조"), ("COHR", "Coherent", "반도체 장비/소재"),
                ("ENTG", "Entegris", "반도체 장비/소재"), ("GFS", "GlobalFoundries", "반도체 파운드리"),
                ("INTC", "Intel", "반도체 설계/제조"), ("KLAC", "KLA Corp", "반도체 장비/소재"),
                ("LRCX", "Lam Research", "반도체 장비/소재"), ("LSCC", "Lattice Semiconductor", "반도체 설계/제조"),
                ("MRVL", "Marvell Technology", "반도체 설계/제조"), ("MCHP", "Microchip Technology", "반도체 설계/제조"),
                ("MU", "Micron Technology", "메모리 반도체"), ("MPWR", "Monolithic Power Systems", "반도체 설계/제조"),
                ("NVDA", "Nvidia", "반도체 설계/제조"), ("NXPI", "NXP Semiconductors", "반도체 설계/제조"),
                ("ON", "ON Semiconductor",
