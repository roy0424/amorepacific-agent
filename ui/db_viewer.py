"""
Database Viewer UI (Streamlit)
데이터베이스 테이블 뷰어 + 아마존 랭킹 시각화
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import inspect, text, select, and_, func
from sqlalchemy.orm import Session

from src.core.database import engine
from src.models.amazon import AmazonRanking, AmazonProduct, AmazonCategory
from src.models.brands import Brand


# ============================================================================
# Database Viewer Functions (기존 기능)
# ============================================================================

def get_tables() -> List[str]:
    inspector = inspect(engine)
    return inspector.get_table_names()


def get_columns(table_name: str) -> List[Dict[str, Any]]:
    inspector = inspect(engine)
    return inspector.get_columns(table_name)


def build_query(
    table_name: str,
    columns: List[Dict[str, Any]],
    limit: int,
    offset: int,
    order_by: str,
    order_dir: str,
    filter_column: str,
    filter_operator: str,
    filter_value: str,
) -> tuple[str, Dict[str, Any]]:
    allowed_columns = {col["name"] for col in columns}
    if order_by not in allowed_columns:
        order_by = columns[0]["name"]

    sql = f'SELECT * FROM "{table_name}"'
    params: Dict[str, Any] = {}

    if filter_column in allowed_columns and filter_value:
        if filter_operator == "contains":
            sql += f' WHERE "{filter_column}" LIKE :filter_value'
            params["filter_value"] = f"%{filter_value}%"
        else:
            sql += f' WHERE "{filter_column}" {filter_operator} :filter_value'
            params["filter_value"] = filter_value

    sql += f' ORDER BY "{order_by}" {order_dir}'
    sql += " LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    return sql, params


# ============================================================================
# Amazon Rankings Viewer Functions (새로운 기능)
# ============================================================================

def get_brands() -> List[Dict[str, Any]]:
    """활성화된 브랜드 목록 조회"""
    with Session(engine) as session:
        brands = session.query(Brand).filter(Brand.is_active == True).all()
        return [{"id": b.id, "name": b.name, "type": b.brand_type} for b in brands]


def get_categories() -> List[Dict[str, Any]]:
    """카테고리 목록 조회"""
    with Session(engine) as session:
        categories = session.query(AmazonCategory).all()
        return [{"id": c.id, "name": c.category_name} for c in categories]


def get_products(brand_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """제품 목록 조회"""
    with Session(engine) as session:
        query = session.query(AmazonProduct).filter(AmazonProduct.is_active == True)
        if brand_id:
            query = query.filter(AmazonProduct.brand_id == brand_id)
        products = query.all()
        return [{"id": p.id, "name": p.product_name, "asin": p.asin, "brand_id": p.brand_id} for p in products]


def get_ranking_data(
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    product_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 10000
) -> pd.DataFrame:
    """랭킹 데이터 조회"""
    with Session(engine) as session:
        query = (
            session.query(
                AmazonRanking.collected_at,
                AmazonRanking.rank,
                AmazonRanking.price,
                AmazonRanking.rating,
                AmazonRanking.review_count,
                AmazonRanking.is_prime,
                AmazonRanking.stock_status,
                AmazonProduct.product_name,
                AmazonProduct.asin,
                Brand.name.label("brand_name"),
                AmazonCategory.category_name
            )
            .join(AmazonProduct, AmazonRanking.product_id == AmazonProduct.id)
            .join(AmazonCategory, AmazonRanking.category_id == AmazonCategory.id)
            .outerjoin(Brand, AmazonProduct.brand_id == Brand.id)
        )

        filters = []
        if category_id:
            filters.append(AmazonRanking.category_id == category_id)
        if brand_id:
            filters.append(AmazonProduct.brand_id == brand_id)
        if product_id:
            filters.append(AmazonRanking.product_id == product_id)
        if start_date:
            filters.append(AmazonRanking.collected_at >= start_date)
        if end_date:
            filters.append(AmazonRanking.collected_at <= end_date)

        if filters:
            query = query.filter(and_(*filters))

        query = query.order_by(AmazonRanking.collected_at.desc()).limit(limit)

        result = query.all()

        if not result:
            return pd.DataFrame()

        df = pd.DataFrame([
            {
                "collected_at": r.collected_at,
                "rank": r.rank,
                "price": float(r.price) if r.price else None,
                "rating": float(r.rating) if r.rating else None,
                "review_count": r.review_count,
                "is_prime": r.is_prime,
                "stock_status": r.stock_status,
                "product_name": r.product_name,
                "asin": r.asin,
                "brand_name": r.brand_name,
                "category_name": r.category_name
            }
            for r in result
        ])

        return df


def get_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """통계 정보 계산"""
    if df.empty:
        return {}

    return {
        "total_records": len(df),
        "unique_products": df["asin"].nunique(),
        "date_range": (df["collected_at"].min(), df["collected_at"].max()),
        "avg_rank": df["rank"].mean(),
        "best_rank": df["rank"].min(),
        "worst_rank": df["rank"].max(),
        "avg_price": df["price"].mean() if "price" in df.columns else None,
        "avg_rating": df["rating"].mean() if "rating" in df.columns else None,
        "total_reviews": df["review_count"].sum() if "review_count" in df.columns else None
    }


def plot_ranking_timeline(df: pd.DataFrame, title: str = "랭킹 변화 추이"):
    """랭킹 타임라인 차트"""
    if df.empty:
        st.warning("표시할 데이터가 없습니다.")
        return

    # 여러 카테고리가 섞여있는지 확인
    df_plot = df.copy()
    has_multiple_categories = df_plot["category_name"].nunique() > 1

    if has_multiple_categories:
        # 전체 카테고리 선택 시: "제품명 (카테고리)" 형식으로 표시
        df_plot["display_name"] = df_plot["product_name"].str[:30] + "... (" + df_plot["category_name"] + ")"
        color_column = "display_name"
        color_label = "제품 (카테고리)"
    else:
        # 특정 카테고리 선택 시: 제품명만 표시
        color_column = "product_name"
        color_label = "제품명"

    fig = px.line(
        df_plot.sort_values("collected_at"),
        x="collected_at",
        y="rank",
        color=color_column,
        title=title,
        labels={
            "collected_at": "수집 시간",
            "rank": "랭킹",
            color_column: color_label
        },
        hover_data=["asin", "brand_name", "category_name", "price", "rating"]
    )

    # Y축 반전 (랭킹이 낮을수록 좋음)
    fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        hovermode="x unified",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_price_timeline(df: pd.DataFrame):
    """가격 변화 추이"""
    if df.empty or "price" not in df.columns or df["price"].isna().all():
        st.warning("가격 데이터가 없습니다.")
        return

    # 여러 카테고리가 섞여있는지 확인
    df_plot = df.copy()
    has_multiple_categories = df_plot["category_name"].nunique() > 1

    if has_multiple_categories:
        # 전체 카테고리 선택 시: "제품명 (카테고리)" 형식으로 표시
        df_plot["display_name"] = df_plot["product_name"].str[:30] + "... (" + df_plot["category_name"] + ")"
        color_column = "display_name"
        color_label = "제품 (카테고리)"
    else:
        # 특정 카테고리 선택 시: 제품명만 표시
        color_column = "product_name"
        color_label = "제품명"

    fig = px.line(
        df_plot.sort_values("collected_at"),
        x="collected_at",
        y="price",
        color=color_column,
        title="가격 변화 추이",
        labels={
            "collected_at": "수집 시간",
            "price": "가격 ($)",
            color_column: color_label
        },
        hover_data=["category_name"]
    )

    fig.update_layout(hovermode="x unified", height=400)
    st.plotly_chart(fig, use_container_width=True)


def plot_rank_distribution(df: pd.DataFrame):
    """랭킹 분포"""
    if df.empty:
        return

    # 여러 카테고리가 섞여있는지 확인
    df_plot = df.copy()
    has_multiple_categories = df_plot["category_name"].nunique() > 1

    if has_multiple_categories:
        # 전체 카테고리 선택 시: "제품명 (카테고리)" 형식으로 표시
        df_plot["display_name"] = df_plot["product_name"].str[:30] + "... (" + df_plot["category_name"] + ")"
        color_column = "display_name"
        color_label = "제품 (카테고리)"
    else:
        # 특정 카테고리 선택 시: 제품명만 표시
        color_column = "product_name"
        color_label = "제품명"

    fig = px.histogram(
        df_plot,
        x="rank",
        color=color_column,
        title="랭킹 분포",
        labels={"rank": "랭킹", color_column: color_label},
        nbins=50
    )

    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# Page Renderers
# ============================================================================

def render_db_viewer_page():
    """데이터베이스 뷰어 페이지"""
    st.title("🗂️ Database Viewer")
    st.markdown("**데이터베이스 테이블을 읽기 전용으로 확인합니다.**")

    tables = get_tables()
    if not tables:
        st.warning("⚠️ 테이블이 없습니다. DB 초기화를 먼저 진행하세요.")
        st.code("python scripts/init_db.py")
        return

    with st.sidebar:
        st.header("⚙️ 설정")
        selected_table = st.selectbox("테이블", options=tables)
        columns = get_columns(selected_table)
        column_names = [col["name"] for col in columns]

        limit = st.slider("조회 행 수", min_value=10, max_value=500, value=100, step=10)
        order_by = st.selectbox("정렬 컬럼", options=column_names, index=0)
        order_dir = st.radio("정렬 방향", options=["DESC", "ASC"], index=0)

        st.subheader("필터")
        filter_column = st.selectbox("컬럼", options=column_names, index=0)
        filter_operator = st.selectbox(
            "연산자",
            options=["=", "!=", ">", "<", ">=", "<=", "contains"],
            index=0,
        )
        filter_value = st.text_input("값", value="")

        refresh = st.button("🔄 새로고침", use_container_width=True)

    count_sql = f'SELECT COUNT(*) FROM "{selected_table}"'
    count_params: Dict[str, Any] = {}
    if filter_column in column_names and filter_value:
        if filter_operator == "contains":
            count_sql += f' WHERE "{filter_column}" LIKE :filter_value'
            count_params["filter_value"] = f"%{filter_value}%"
        else:
            count_sql += f' WHERE "{filter_column}" {filter_operator} :filter_value'
            count_params["filter_value"] = filter_value

    with engine.connect() as connection:
        total_rows = connection.execute(text(count_sql), count_params).scalar() or 0

    total_pages = max(1, (total_rows + limit - 1) // limit)
    page = st.number_input(
        "페이지",
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1,
    )
    offset = (page - 1) * limit

    sql, params = build_query(
        selected_table,
        columns,
        limit,
        offset,
        order_by,
        order_dir,
        filter_column,
        filter_operator,
        filter_value,
    )

    if refresh:
        st.session_state["db_viewer_refresh"] = True

    with st.expander("SQL 미리보기", expanded=False):
        st.code(sql)
        if params:
            st.json(params)

    with engine.connect() as connection:
        df = pd.read_sql_query(text(sql), connection, params=params)

    st.subheader(f"📊 {selected_table}")
    st.caption(f"{len(df)} rows (총 {total_rows}개, {page}/{total_pages} 페이지)")
    st.dataframe(df, use_container_width=True)

    st.download_button(
        "⬇️ CSV 다운로드",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected_table}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    with st.expander("스키마 정보", expanded=False):
        schema_df = pd.DataFrame(
            [{"name": c["name"], "type": str(c["type"])} for c in columns]
        )
        st.dataframe(schema_df, use_container_width=True)


def render_amazon_rankings_page():
    """아마존 랭킹 시각화 페이지"""
    st.title("📊 Laneige Rankings Viewer")
    st.markdown("**라네즈 제품의 아마존 랭킹 데이터를 시각화하여 확인합니다.**")

    # Laneige 브랜드 ID 가져오기
    with Session(engine) as session:
        laneige_brand = session.query(Brand).filter(
            Brand.name.ilike("%laneige%"),
            Brand.is_active == True
        ).first()
        laneige_brand_id = laneige_brand.id if laneige_brand else None

    if not laneige_brand_id:
        st.error("❌ Laneige 브랜드를 찾을 수 없습니다. 데이터베이스를 확인해주세요.")
        return

    # 사이드바 필터
    with st.sidebar:
        st.header("🔍 필터")

        # 날짜 범위
        st.subheader("날짜 범위")
        date_option = st.radio(
            "기간 선택",
            ["최근 24시간", "최근 7일", "최근 30일", "전체", "사용자 지정"],
            index=3  # 기본값: 전체
        )

        if date_option == "최근 24시간":
            start_date = datetime.now() - timedelta(hours=24)
            end_date = datetime.now()
        elif date_option == "최근 7일":
            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now()
        elif date_option == "최근 30일":
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()
        elif date_option == "사용자 지정":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("시작일", datetime.now() - timedelta(days=7))
                start_date = datetime.combine(start_date, datetime.min.time())
            with col2:
                end_date = st.date_input("종료일", datetime.now())
                end_date = datetime.combine(end_date, datetime.max.time())
        else:
            start_date = None
            end_date = None

        # 카테고리 필터
        st.subheader("카테고리")
        categories = get_categories()
        category_options = {"전체": None}
        category_options.update({c["name"]: c["id"] for c in categories})
        selected_category_name = st.selectbox("카테고리 선택", list(category_options.keys()))
        selected_category = category_options[selected_category_name]

        # 제품 필터 (Laneige 제품만)
        st.subheader("제품")
        products = get_products(brand_id=laneige_brand_id)
        product_options = {"전체": None}
        product_options.update({f"{p['name'][:50]}... ({p['asin']})": p["id"] for p in products})
        selected_product_name = st.selectbox("제품 선택", list(product_options.keys()))
        selected_product = product_options[selected_product_name]

    # 필터 변경 감지 - 필터가 바뀌면 자동으로 데이터 재조회
    # start_date와 end_date를 문자열로 변환하여 비교 (datetime 객체는 직접 비교 불가)
    current_filters = {
        'date_option': date_option,
        'start_date': str(start_date) if start_date else None,
        'end_date': str(end_date) if end_date else None,
        'category': selected_category,
        'product': selected_product
    }

    # 이전 필터와 비교
    if "prev_filters" not in st.session_state or st.session_state["prev_filters"] != current_filters:
        st.session_state["prev_filters"] = current_filters

        # 데이터 조회 (Laneige 브랜드로 고정)
        with st.spinner("데이터 조회 중..."):
            df = get_ranking_data(
                category_id=selected_category,
                brand_id=laneige_brand_id,
                product_id=selected_product,
                start_date=start_date,
                end_date=end_date
            )
            st.session_state["amazon_df"] = df
    else:
        df = st.session_state.get("amazon_df", pd.DataFrame())

    # 통계 정보
    if not df.empty:
        stats = get_stats(df)

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("전체 레코드", f"{stats['total_records']:,}")

        with col2:
            st.metric("제품 수", f"{stats['unique_products']:,}")

        with col3:
            st.metric("평균 랭킹", f"{stats['avg_rank']:.1f}" if stats['avg_rank'] else "N/A")

        with col4:
            st.metric("최고 랭킹", f"{stats['best_rank']:,}" if stats['best_rank'] else "N/A")

        with col5:
            st.metric("최저 랭킹", f"{stats['worst_rank']:,}" if stats['worst_rank'] else "N/A")

        # 차트 탭
        tab1, tab2, tab3, tab4 = st.tabs(["📈 랭킹 추이", "💰 가격 추이", "📊 랭킹 분포", "📋 데이터 테이블"])

        with tab1:
            plot_ranking_timeline(df)

        with tab2:
            plot_price_timeline(df)

        with tab3:
            plot_rank_distribution(df)

        with tab4:
            st.subheader("데이터 테이블")

            # 컬럼 순서 정렬
            display_columns = [
                "collected_at", "rank", "product_name", "brand_name",
                "category_name", "price", "rating", "review_count",
                "is_prime", "stock_status", "asin"
            ]

            display_df = df[display_columns].copy()
            display_df["collected_at"] = pd.to_datetime(display_df["collected_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")

            st.dataframe(
                display_df,
                use_container_width=True,
                height=500
            )

            # CSV 다운로드
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ CSV 다운로드",
                data=csv,
                file_name=f"amazon_rankings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.info("조회된 데이터가 없습니다. 필터를 조정하거나 데이터 수집을 확인해주세요.")

        # 데이터 수집 상태 확인
        with st.expander("💡 데이터 수집 상태 확인"):
            st.markdown("""
            데이터가 없는 경우 아래를 확인해주세요:

            1. **데이터베이스 초기화**
               ```bash
               python scripts/init_db.py
               ```

            2. **Prefect 워크플로우 실행**
               ```bash
               python scripts/deploy_flows.py
               prefect deployment run amazon-scraper/default
               ```

            3. **수동 스크래핑 실행**
               ```bash
               python src/flows/amazon_flow.py
               ```
            """)


# ============================================================================
# Main App
# ============================================================================

def main():
    st.set_page_config(
        page_title="Laneige Data Viewer",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 사이드바에서 페이지 선택
    with st.sidebar:
        st.title("📊 Laneige Data Viewer")
        page = st.radio(
            "페이지 선택",
            ["🗂️ Database Viewer", "📈 Laneige Rankings"],
            index=0
        )
        st.markdown("---")

    # 선택된 페이지 렌더링
    if page == "🗂️ Database Viewer":
        render_db_viewer_page()
    elif page == "📈 Laneige Rankings":
        render_amazon_rankings_page()


if __name__ == "__main__":
    main()
