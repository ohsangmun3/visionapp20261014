import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. 페이지 설정 (반드시 최상단에 위치)
st.set_page_config(
    page_title="제조 품질 현황 대시보드",
    page_icon="🔍",
    layout="wide"
)

# 2. 기본 샘플 데이터 생성 함수 (업로드 파일이 없을 때 사용)
@st.cache_data
def get_sample_data():
    base_dates = [
        "2026-10-01", "2026-10-01", "2026-10-01", "2026-10-02", "2026-10-02",
        "2026-10-03", "2026-10-03", "2026-10-04", "2026-10-04", "2026-10-05",
        "2026-10-05", "2026-10-06", "2026-10-06", "2026-10-07", "2026-10-07"
    ]
    data = {
        "inspection_date": base_dates,
        "product_id": [f"P{i:03d}" for i in range(1, 16)],
        "result": ["OK", "NG", "OK", "OK", "NG", "OK", "NG", "OK", "OK", "NG", "OK", "OK", "NG", "OK", "OK"],
        "defect_type": [
            "None", "Scratch", "None", "None", "Crack",
            "None", "Dent", "None", "None", "Contamination",
            "None", "None", "Scratch", "None", "None"
        ],
        "confidence": [0.98, 0.91, 0.96, 0.95, 0.88, 0.97, 0.92, 0.99, 0.94, 0.85, 0.97, 0.96, 0.90, 0.98, 0.95]
    }
    df = pd.DataFrame(data)
    df["inspection_date"] = pd.to_datetime(df["inspection_date"]).dt.date
    return df

# 3. 사이드바 구성 (파일 업로드 및 필터)
st.sidebar.header("📁 데이터 설정 및 필터")

uploaded_file = st.sidebar.file_uploader("CSV 파일 업로드", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df["inspection_date"] = pd.to_datetime(df["inspection_date"]).dt.date
        st.sidebar.success("CSV 파일이 성공적으로 로드되었습니다.")
    except Exception as e:
        st.sidebar.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        df = get_sample_data()
else:
    df = get_sample_data()
    st.sidebar.info("기본 샘플 데이터로 동작 중입니다.")

# 사이드바 필터 항목
st.sidebar.markdown("---")
st.sidebar.subheader("상세 필터")

# 3-1. 날짜 범위 필터
min_date = df["inspection_date"].min()
max_date = df["inspection_date"].max()

selected_dates = st.sidebar.date_input(
    "검사 날짜 범위",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# 3-2. 제품 ID 필터
product_list = sorted(df["product_id"].unique())
selected_products = st.sidebar.multiselect("제품 선택 (미선택 시 전체)", product_list, default=product_list)

# 3-3. 판정 결과 필터
result_options = ["전체", "OK", "NG"]
selected_result = st.sidebar.selectbox("검사 결과", result_options)

# 데이터 필터링 적용
filtered_df = df.copy()

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
    filtered_df = filtered_df[(filtered_df["inspection_date"] >= start_date) & (filtered_df["inspection_date"] <= end_date)]

if selected_products:
    filtered_df = filtered_df[filtered_df["product_id"].isin(selected_products)]

if selected_result != "전체":
    filtered_df = filtered_df[filtered_df["result"] == selected_result]

# 4. 메인 화면 헤더
st.title("제조 품질 현황 대시보드")
st.caption("AI 비전검사 PoC 준비를 위한 품질 데이터 모니터링")
st.markdown("---")

# 5. 상단 KPI 카드
total_inspections = len(filtered_df)
ok_count = len(filtered_df[filtered_df["result"] == "OK"])
ng_count = len(filtered_df[filtered_df["result"] == "NG"])
defect_rate = (ng_count / total_inspections * 100) if total_inspections > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("전체 검사", f"{total_inspections:,} 건")
col2.metric("정상 (OK)", f"{ok_count:,} 건")
col3.metric("불량 (NG)", f"{ng_count:,} 건")
col4.metric("불량률", f"{defect_rate:.2f} %")

st.markdown("---")

# 6. 중단 시각화 그래프
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("📈 일자별 검사 및 불량 추이")
    if not filtered_df.empty:
        # 일자별/결과별 집계
        daily_stats = filtered_df.groupby(["inspection_date", "result"]).size().reset_index(name="count")
        daily_stats["inspection_date"] = daily_stats["inspection_date"].astype(str)
        
        fig_trend = px.line(
            daily_stats,
            x="inspection_date",
            y="count",
            color="result",
            markers=True,
            title="일자별 검사 수량",
            labels={"inspection_date": "검사일", "count": "수량", "result": "판정"},
            color_discrete_map={"OK": "#2ca02c", "NG": "#d62728"}
        )
        fig_trend.update_layout(xaxis_title="날짜", yaxis_title="건수", hovermode="x unified")
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("조건에 일치하는 데이터가 없습니다.")

with col_chart2:
    st.subheader("📊 불량 유형별 발생 현황")
    defect_df = filtered_df[(filtered_df["result"] == "NG") & (filtered_df["defect_type"] != "None")]
    
    if not defect_df.empty:
        defect_counts = defect_df["defect_type"].value_counts().reset_index()
        defect_counts.columns = ["defect_type", "count"]
        
        fig_bar = px.bar(
            defect_counts,
            x="defect_type",
            y="count",
            text="count",
            title="불량 유형별 발생 건수",
            labels={"defect_type": "불량 유형", "count": "발생 건수"},
            color="defect_type",
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(xaxis_title="불량 유형", yaxis_title="건수", showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("선택된 조건에 불량(NG) 데이터가 없습니다.")

st.markdown("---")

# 7. 하단 최근 검사 결과 테이블 (최근 10건)
st.subheader("📋 최근 검사 데이터 (최근 10건)")
if not filtered_df.empty:
    recent_df = filtered_df.sort_values(by="inspection_date", ascending=False).head(10)
    st.dataframe(
        recent_df.reset_index(drop=True),
        use_container_width=True
    )
else:
    st.write("표시할 검사 데이터가 없습니다.")
