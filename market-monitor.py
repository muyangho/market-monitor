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

# --- 단일 지표 호출 함수 (서버 환경 안정화) ---
def get_metric_data(ticker):
    if not ticker: return None
    try:
        # yf.download 대신 history를 사용하여 단일 종목 호출의 안정성 극대화
        hist = yf.Ticker(ticker).history(period="5d")
        if not hist.empty and len(hist) >= 2:
            current = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            change = ((current - prev) / prev) * 100
            return current, change
    except Exception as e:
        print(f"[{ticker}] 매크로 지표 호출 오류: {e}")
    return None

# --- 2. yfinance 병렬 세부 섹터 수집 ---
def fetch_yf_industry(ticker):
    try:
        info = yf.Ticker(ticker).info
        return ticker, info.get('industry', info.get('sector', ''))
    except:
        return ticker, ''

def get_detailed_sectors_dict(tickers):
    sectors_dict = {}
    # 서버 환경(특히 Streamlit Cloud)에서 yfinance IP 차단을 막기 위해 max_workers를 5로 하향
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
    # 클라우드 환경 차단 방지용 강력한 User-Agent
    req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        if index_name == "S&P 500":
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            req = urllib.request.Request(url, headers=req_headers)
            df = pd.read_html(urllib.request.urlopen(req).read())[0]
            df['Symbol'] = df['Symbol'].str.replace('.', '-', regex=False)
            df['Sector'] = df['GICS Sub-Industry'].apply(translate_sector)
            return df[['Symbol', 'Security', 'Sector']]
            
        elif index_name == "NASDAQ 100":
            url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
            req = urllib.request.Request(url, headers=req_headers)
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
            req = urllib.request.Request(url, headers=req_headers)
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
                ("ON", "ON Semiconductor", "반도체 설계/제조"), ("QCOM", "Qualcomm", "반도체 설계/제조"),
                ("RMBS", "Rambus", "반도체 설계/제조"), ("SWKS", "Skyworks Solutions", "반도체 설계/제조"),
                ("STM", "STMicroelectronics", "반도체 설계/제조"), ("TXN", "Texas Instruments", "반도체 설계/제조"),
                ("TER", "Teradyne", "반도체 장비/소재"), ("WDC", "Western Digital", "메모리 반도체"),
                ("WOLF", "Wolfspeed", "반도체 장비/소재")
            ]
            return pd.DataFrame(sox_data, columns=['Symbol', 'Security', 'Sector'])

        elif "KOSPI" in index_name or "KOSDAQ" in index_name:
            market = 'KOSPI' if "KOSPI" in index_name else 'KOSDAQ'
            suffix = '.KS' if market == 'KOSPI' else '.KQ'
            
            df_krx = fdr.StockListing(market)
            if 'Marcap' in df_krx.columns:
                top_n = df_krx.sort_values(by='Marcap', ascending=False).head(100)
            else:
                top_n = df_krx.head(100)
                
            top_n['Symbol'] = top_n['Code'] + suffix
            name_col = 'Name' if 'Name' in top_n.columns else 'Security'
            top_n = top_n.rename(columns={name_col: 'Security'})
            
            yf_sectors = get_detailed_sectors_dict(top_n['Symbol'].tolist())
            
            def map_krx_sector(row):
                yf_sec = yf_sectors.get(row['Symbol'], '')
                if yf_sec: return translate_sector(yf_sec)
                return translate_sector(row.get('Sector', '기타 일반 산업'))
                
            top_n['Sector'] = top_n.apply(map_krx_sector, axis=1)
            return top_n[['Symbol', 'Security', 'Sector']]
            
    except Exception as e:
        print(f"데이터 스크래핑 에러 발생: {e}")
    return pd.DataFrame()

# --- 5. 주가 데이터 다운로드 (에러 방어 로직 강화) ---
@st.cache_data(ttl=60)
def get_market_data(tickers):
    if not tickers: return None
    try:
        data = yf.download(tickers, period="5d", progress=False)['Close']
        if data.empty: return None
        
        # Series(단일 종목) 반환 방어
        if isinstance(data, pd.Series):
            data = data.to_frame()
            
        data = data.dropna(axis=1, how='all').ffill()
        if len(data) < 2: return None
        
        current = data.iloc[-1]
        prev = data.iloc[-2]
        pct_change = ((current - prev) / prev) * 100
        change_df = pct_change.reset_index()
        change_df.columns = ['Symbol', '등락률(%)']
        return change_df
    except Exception as e:
        print(f"주가 데이터 다운로드 에러: {e}")
        return None

def style_pct(val):
    if pd.isna(val): return ''
    if val > 0: return 'color: #ff4b4b; font-weight: bold;'
    elif val < 0: return 'color: #1f77b4; font-weight: bold;'
    return 'color: gray;'

# --- 6. 메인 UI 랜더링 ---
st.sidebar.title("🦅 Master Market Monitor")
menu = st.sidebar.radio("시장 분석 지수 선택", list(INDEX_MAP.keys()))

st.title(f"📊 {menu} 심층 분석")

# ==========================================
# [상단] 매크로 선행 지표
# ==========================================
idx_info = INDEX_MAP[menu]

st.subheader("📌 기준 지표 (Index vs Futures)")
with st.spinner(f"실시간 매크로 지표 호출 중..."):
    m_col1, m_col2 = st.columns(2)
    
    # 1. 본지수 렌더링
    idx_data = get_metric_data(idx_info["index_ticker"])
    if idx_data:
        m_col1.metric(label=f"📉 {idx_info['index_name']}", value=f"{idx_data[0]:,.2f}", delta=f"{idx_data[1]:.2f}%")
    else:
        m_col1.error(f"{idx_info['index_name']} 데이터를 불러오지 못했습니다.")

    # 2. 선물지수 렌더링
    if idx_info["future_ticker"]:
        fut_data = get_metric_data(idx_info["future_ticker"])
        if fut_data:
            m_col2.metric(label=f"📈 {idx_info['future_name']}", value=f"{fut_data[0]:,.2f}", delta=f"{fut_data[1]:.2f}%")
        else:
            m_col2.error(f"{idx_info['future_name']} 데이터를 불러오지 못했습니다.")
    else:
        m_col2.info("💡 API 정책상 해당 지수의 실시간 선물 데이터는 제공되지 않습니다.")

st.divider()

# ==========================================
# [하단] 종목 딥섹터 분석 및 차트 연동
# ==========================================
with st.spinner(f'종목 데이터 및 세부 산업군을 분석 중입니다...'):
    components_df = get_index_components(menu)
    
    if not components_df.empty:
        tickers = components_df['Symbol'].tolist()
        change_df = get_market_data(tickers)
        
        if change_df is not None:
            merged_df = pd.merge(components_df, change_df, on='Symbol')
            merged_df['등락률(%)'] = merged_df['등락률(%)'].round(2)
            merged_df = merged_df.sort_values(by='등락률(%)', ascending=False).dropna()
            
            merged_df['차트 링크'] = merged_df['Symbol'].apply(
                lambda x: f"https://finance.naver.com/item/main.naver?code={x.replace('.KS', '').replace('.KQ', '')}" if '.KS' in x or '.KQ' in x else f"https://finance.yahoo.com/quote/{x}"
            )
            
            display_df = merged_df[['Symbol', 'Security', 'Sector', '등락률(%)', '차트 링크']]
            display_df.columns = ['티커', '종목명', '섹터(테마)', '등락률(%)', '차트 링크']
            
            st.subheader("전체 시장 참여도 (Market Breadth)")
            pos = (display_df['등락률(%)'] > 0).sum()
            neg = (display_df['등락률(%)'] < 0).sum()
            flat = len(display_df) - pos - neg
            
            c1, c2, c3 = st.columns(3)
            c1.metric("상승 종목 📈", f"{pos}개")
            c2.metric("하락 종목 📉", f"{neg}개")
            c3.metric("보합", f"{flat}개")
            st.divider()
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("1. 🎯 테마별 자금 쏠림 (평균 등락률)")
                sector_avg = display_df.groupby('섹터(테마)')['등락률(%)'].mean().sort_values(ascending=False).round(2)
                st.dataframe(sector_avg.reset_index().style.map(style_pct, subset=['등락률(%)']), use_container_width=True)
            
            with col2:
                st.subheader("2. 🔥 멱살 주도주 (TOP 5)")
                st.dataframe(display_df[['티커', '종목명', '등락률(%)']].head(5).style.map(style_pct, subset=['등락률(%)']), use_container_width=True, hide_index=True)
                st.subheader("3. 🧊 하락 원흉 (BOTTOM 5)")
                st.dataframe(display_df[['티커', '종목명', '등락률(%)']].tail(5).sort_values(by='등락률(%)').style.map(style_pct, subset=['등락률(%)']), use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader(f"🔎 전체 구성 종목 ({len(display_df)}개)")
            st.dataframe(
                display_df.style.map(style_pct, subset=['등락률(%)']),
                column_config={
                    "차트 링크": st.column_config.LinkColumn("상세 차트", display_text="📈 차트 열기")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.error("데이터 통신 중 주가 기록을 불러오지 못했습니다. (yfinance API 응답 지연)")
    else:
        st.error("스크래핑 에러가 발생했습니다. 잠시 후 다시 시도해주세요.")
