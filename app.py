import pandas as pd
import streamlit as st
from dashscope import Generation
import os

# 设置页面标题和布局
st.set_page_config(page_title="护肤品成分对比", layout="wide")
st.title("🧴 护肤品迭代版本成分对比")

# ===== API Key 加载逻辑（增强版） =====
try:
    # 尝试从 Streamlit Cloud Secrets 读取
    api_key = st.secrets["DASHSCOPE_API_KEY"]
    if api_key:
        Generation.api_key = api_key
        st.success("✅ API Key 已从 Secrets 加载")
    else:
        st.error("❌ Secrets 中的 API Key 为空，请检查配置")
        st.stop()
except Exception as e:
    # 如果 st.secrets 不存在，尝试从系统环境变量读取（本地开发）
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if api_key:
        Generation.api_key = api_key
        st.success("✅ API Key 已从系统环境变量加载")
    else:
        st.error(f"❌ 未找到 API Key：{e}")
        st.info("请在 Streamlit Cloud 后台配置 DASHSCOPE_API_KEY，或在本地设置环境变量")
        st.stop()
# ===== API Key 加载结束 =====

# 读取 Excel 数据
@st.cache_data
def load_data():
    df = pd.read_excel("data.xlsx", sheet_name='实例')
    return df

df = load_data()

# 获取产品标准名列表
product_standards = df['product_standard'].unique().tolist() if 'product_standard' in df.columns else ["薇诺娜舒敏保湿特护霜"]

# 获取所有版本列表
versions = df['version_label'].unique().tolist() if 'version_label' in df.columns else []

# ====== 界面布局 ======
products = df['product_standard'].unique().tolist()

selected_product = st.selectbox("选择产品（以昵称展示）", products, key="product_selector")

formulas = df[df['product_standard'] == selected_product]['配方标识'].unique().tolist()
selected_formula = st.selectbox("选择配方单元", formulas) if len(formulas) > 1 else formulas[0]

product_versions = df[df['product_standard'] == selected_product]['version_label'].unique().tolist()

if len(product_versions) == 0:
    st.warning(f"⚠️ 产品「{selected_product}」没有版本数据，请检查 Excel")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    st.subheader("旧版本")
    v1 = st.selectbox(
        "选择旧版本",
        product_versions,
        key=f"v1_{selected_product}"
    )

with col2:
    st.subheader("新版本")
    v2 = st.selectbox(
        "选择新版本",
        product_versions,
        key=f"v2_{selected_product}"
    )

# 对比按钮
if st.button("🔍 开始对比", type="primary"):
    # 检查数据是否存在
    v1_exists = len(df[(df['product_standard'] == selected_product) & (df['version_label'] == v1) & (df['配方标识'] == selected_formula)]) > 0
    v2_exists = len(df[(df['product_standard'] == selected_product) & (df['version_label'] == v2) & (df['配方标识'] == selected_formula)]) > 0

    if not v1_exists:
        st.error(f"❌ 未找到「{selected_product}」的「{v1}」-「{selected_formula}」数据，请检查数据录入")
        st.stop()
    if not v2_exists:
        st.error(f"❌ 未找到「{selected_product}」的「{v2}」-「{selected_formula}」数据，请检查数据录入")
        st.stop()

    # 拆分两代数据
    df_v1 = df[(df['product_standard'] == selected_product) & (df['version_label'] == v1) & (df['配方标识'] == selected_formula)][['ingredient_name_raw', 'ingredient_order']].rename(columns={'ingredient_order': 'ingredient_order_一代'})
    df_v1['ingredient_order_一代'] = df_v1['ingredient_order_一代'].astype('Int64')

    df_v2 = df[(df['product_standard'] == selected_product) & (df['version_label'] == v2) & (df['配方标识'] == selected_formula)][['ingredient_name_raw', 'ingredient_order']].rename(columns={'ingredient_order': 'ingredient_order_二代'})
    df_v2['ingredient_order_二代'] = df_v2['ingredient_order_二代'].astype('Int64')

    # 合并对比
    merged = pd.merge(df_v1, df_v2, on='ingredient_name_raw', how='outer')
    merged = merged.reset_index(drop=True)

    def classify_change(row):
        if pd.isna(row['ingredient_order_一代']):
            return '新增'
        if pd.isna(row['ingredient_order_二代']):
            return '移除'
        if row['ingredient_order_一代'] != row['ingredient_order_二代']:
            return '排序变化'
        return '不变'

    merged['变化类型'] = merged.apply(classify_change, axis=1)

    # 按第一代排序，新增放最后
    merged['sort_key'] = merged['ingredient_order_一代'].fillna(999)
    merged = merged.sort_values('sort_key')
    merged = merged.drop(columns=['sort_key'])

    # 展示对比表格
    st.subheader(f"📊 成分对比明细（{selected_formula}）")

    def highlight_row(row):
        change_type = row['变化类型']
        if change_type == '新增':
            return ['background-color: #d4edda'] * len(row)
        elif change_type == '移除':
            return ['background-color: #f8d7da'] * len(row)
        elif change_type == '排序变化':
            return ['background-color: #fff3cd'] * len(row)
        else:
            return [''] * len(row)

    styled_df = merged.style.apply(highlight_row, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # 统计概览卡片
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("新增", len(merged[merged['变化类型'] == '新增']))
    with col_b:
        st.metric("移除", len(merged[merged['变化类型'] == '移除']))
    with col_c:
        st.metric("排序变化", len(merged[merged['变化类型'] == '排序变化']))
    with col_d:
        st.metric("不变", len(merged[merged['变化类型'] == '不变']))

    # AI摘要
    total_changes = len(merged[merged['变化类型'] == '新增']) + len(merged[merged['变化类型'] == '移除']) + len(merged[merged['变化类型'] == '排序变化'])

    if total_changes == 0:
        st.info("📝 两个版本完全相同，没有成分变化，因此无需生成AI摘要。")
    else:
        st.subheader("🤖 AI 智能摘要")

        def build_prompt(merged_df, trace_ingredients):
            added_all = merged_df[merged_df['变化类型'] == '新增']
            added_regular = added_all[~added_all['ingredient_name_raw'].isin(trace_ingredients)]
            added_trace = added_all[added_all['ingredient_name_raw'].isin(trace_ingredients)]
            removed = merged_df[merged_df['变化类型'] == '移除']
            moved = merged_df[merged_df['变化类型'] == '排序变化']

            prompt = f"以下是一份护肤品版本对比结果（产品：{selected_product}，配方：{selected_formula}，旧版：{v1}，新版：{v2}）：\n\n"
            if len(added_regular) > 0:
                prompt += f"新增常规成分（{len(added_regular)}种）：{', '.join(added_regular['ingredient_name_raw'].tolist())}\n"
            else:
                prompt += "新增常规成分：无\n"

            if len(added_trace) > 0:
                prompt += f"新增微量成分（{len(added_trace)}种）：{', '.join(added_trace['ingredient_name_raw'].tolist())}\n"
            else:
                prompt += "新增微量成分：无\n"

            if len(removed) > 0:
                prompt += f"移除成分：{', '.join(removed['ingredient_name_raw'].tolist())}\n"
            else:
                prompt += "移除成分：无\n"

            if len(moved) > 0:
                prompt += "排序变化：\n"
                for _, row in moved.iterrows():
                    old, new = row['ingredient_order_一代'], row['ingredient_order_二代']
                    arrow = '提前' if old > new else '推后'
                    prompt += f"  - {row['ingredient_name_raw']}: 第{old}位 → 第{new}位（{arrow}{abs(old-new)}位）\n"

            prompt += "\n请用简洁的中文总结主要变化（100字以内），分点呈现："
            prompt += "\n1. 主要变化：用数字明确说出新增了几种常规成分、几种微量成分，是否移除了成分。"
            prompt += "\n2. 功效成分变化：新增或排序显著变化的常规成分中，哪些可能是功效成分，排序变化可能带来什么影响。"
            prompt += "\n注意：微量成分单独列出，不要与常规成分混淆。只陈述客观事实，不做'好/坏'评价。"
            return prompt

        with st.spinner("AI正在分析成分变化..."):
            try:
                prompt = build_prompt(merged, df)
                response = Generation.call(
                    model='qwen-plus',
                    prompt=prompt,
                    max_tokens=500,
                    temperature=0.7
                )
                summary = response.output.text
                print("调试：AI返回内容：", summary)
                st.success("✅ 摘要生成完成")
                st.markdown(summary.replace('\n', '  \n'))
            except Exception as e:
                st.error(f"AI摘要生成失败：{e}")
                st.info("请检查 API Key 是否配置正确，以及网络是否正常。")
else:
    st.info("👆 选择新旧版本后，点击「开始对比」按钮查看结果")

# 页脚
st.markdown("---")
st.caption("数据来源：国家药监局备案信息 · 仅供学习参考")
