import pandas as pd
import streamlit as st
from dashscope import Generation
import os

# 设置页面标题和布局
st.set_page_config(page_title="护肤品成分对比", layout="wide")
st.title("🧴 护肤品迭代版本成分对比")

# ===== API Key 加载 =====
try:
    api_key = st.secrets["DASHSCOPE_API_KEY"]
    if api_key:
        Generation.api_key = api_key
        st.success("✅ API Key 已加载")
        st.write("测试：正在加载数据...")
    else:
        st.error("❌ Secrets 中的 API Key 为空，请检查配置")
        st.stop()
except Exception as e:
    st.error(f"❌ 无法读取 Secrets 中的 API Key：{e}")
    st.info("请在 Streamlit Cloud 后台配置 DASHSCOPE_API_KEY")
    st.stop()
# ===== API Key 加载结束 =====

# ... 后续代码保持不变
