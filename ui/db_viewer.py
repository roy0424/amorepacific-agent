"""
Database Viewer UI (Streamlit)
Read-only viewer for inspecting tables and recent records.
"""
import sys
from pathlib import Path
from typing import Dict, Any, List

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import streamlit as st
from sqlalchemy import inspect, text

from src.core.database import engine


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


def main():
    st.set_page_config(
        page_title="Laneige DB Viewer",
        page_icon="🗂️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🗂️ Laneige Database Viewer")
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


if __name__ == "__main__":
    main()
