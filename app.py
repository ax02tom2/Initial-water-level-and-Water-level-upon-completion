import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 網頁基本設定
st.set_page_config(page_title="地下水位與漏水層自動評估系統", layout="wide")
st.title("💧 地下水位與漏水層自動評估系統")
st.markdown("將現場上下工水位資料化為自動判估與可視化圖表，取代傳統 CAD 繪圖與人工判定。")

# ==========================================
# 第一部分：資料輸入區[cite: 1]
# ==========================================
st.subheader("📝 1. 現場水位與鑽探資料輸入")
st.write("請直接在下方表格修改「當日下工水位」與「翌日上工水位」等數值，系統會即時重新運算。")

# 建立預設資料表 (對應您提供的 Excel 範例結構)
default_data = pd.DataFrame({
    "工作天數": [1, 2, 3, 4, 5],
    "鑽探起點深度(m)": [0.0, 3.0, 10.0, 15.0, 24.0],
    "鑽探終點深度(m)": [3.0, 10.0, 15.0, 24.0, 30.0],
    "當日下工水位(m)": [np.nan, 8.9, 11.5, 22.3, 27.6],
    "翌日上工水位(m)": [np.nan, 9.2, 13.8, 23.2, np.nan]
})

# 使用 st.data_editor 讓使用者能在網頁上像 Excel 一樣編輯資料[cite: 1]
edited_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=True)

# ==========================================
# 第二部分：漏水層自動判斷邏輯[cite: 2]
# ==========================================
def evaluate_water_layer(row):
    down_wl = row['當日下工水位(m)']
    up_wl = row['翌日上工水位(m)']
    total_depth = row['鑽探終點深度(m)']
    
    # 規則 H：當日下工及翌日上工均無地下水 -> 完全漏水層[cite: 2]
    if pd.isna(down_wl) and pd.isna(up_wl):
        return "完全漏水層"
        
    # 如果翌日無水，通常視為嚴重漏水層
    if pd.isna(up_wl) and pd.notna(down_wl):
        return "漏水層 (無水)"
        
    # 計算水位變化 (數值越大代表深度越深；所以 up_wl > down_wl 代表水位下降)
    drop_m = up_wl - down_wl
    
    # 規則 A/B/C/D：上升或無明顯變化 (這裡容許 0.3m 內的微小波動視為無明顯變化) -> 有水層[cite: 2]
    if drop_m <= 0.3:
        return "有水層"
    else:
        # 計算下降幅度比例：(翌日上工水位 - 當日下工水位) / 當日總累計鑽探進尺深度[cite: 2]
        ratio = drop_m / total_depth
        
        # 規則 E：翌日上工水位小幅度下降 (下降幅度 < 50%) -> 部分漏水層[cite: 2]
        if ratio < 0.5:
            return "部分漏水層"
        # 規則 F/G：翌日上工水位大幅度下降 (下降幅度 > 50%) -> 漏水層[cite: 2]
        else:
            return "漏水層"

# 執行判定並將結果加入 Dataframe
edited_df['漏水層判定'] = edited_df.apply(evaluate_water_layer, axis=1)

st.write("💡 **自動判估結果** (依照文獻規則判定)：")
st.dataframe(edited_df[['工作天數', '鑽探終點深度(m)', '當日下工水位(m)', '翌日上工水位(m)', '漏水層判定']], use_container_width=True)

# ==========================================
# 第三部分：自動生成 CAD 風格成果圖[cite: 3]
# ==========================================
st.subheader("📊 2. 自動產出水位與鑽探剖面成果圖")

fig = go.Figure()

# 1. 繪製階梯狀的鑽探進尺輪廓線[cite: 3]
x_steps = [0.5]
y_steps = [0.0]

for i, row in edited_df.iterrows():
    day = row['工作天數']
    start_d = row['鑽探起點深度(m)']
    end_d = row['鑽探終點深度(m)']
    
    # 建立階梯的 X, Y 座標點[cite: 3]
    x_steps.extend([day - 0.5, day + 0.5])
    y_steps.extend([start_d, start_d])
    x_steps.extend([day + 0.5, day + 0.5])
    y_steps.extend([start_d, end_d])

# 將輪廓線加入圖表中
fig.add_trace(go.Scatter(
    x=x_steps, y=y_steps, 
    mode='lines', 
    line=dict(color='black', width=2), 
    name='鑽探進尺',
    hoverinfo='skip'
))

# 定義不同漏水層的對應背景顏色[cite: 3]
layer_colors = {
    "完全漏水層": "#e0e0e0",   # 灰色
    "有水層": "#cce5ff",     # 淡藍色
    "部分漏水層": "#d4edda", # 淡綠色
    "漏水層": "#fff3cd",     # 橘黃色
    "漏水層 (無水)": "#fff3cd"
}

# 2. 繪製水位標示 (▼, ∇) 與左側背景色塊[cite: 3]
for i, row in edited_df.iterrows():
    day = row['工作天數']
    layer_type = row['漏水層判定']
    
    # 畫出對應深度的背景色塊以標示地層屬性[cite: 3]
    fig.add_hrect(
        y0=row['鑽探起點深度(m)'], y1=row['鑽探終點深度(m)'],
        fillcolor=layer_colors.get(layer_type, "white"), opacity=0.4,
        layer="below", line_width=0,
        annotation_text=f"<b>{layer_type}</b>", annotation_position="top left"
    )
    
    # 標示「當日下工水位」 (空心倒三角形)[cite: 3]
    if pd.notna(row['當日下工水位(m)']):
        fig.add_trace(go.Scatter(
            x=[day - 0.2], y=[row['當日下工水位(m)']],
            mode='markers+text',
            marker=dict(symbol='triangle-down-open', size=14, color='black', line=dict(width=2)),
            text=[f"{row['當日下工水位(m)']} ∇"], textposition="top center",
            name=f'第{day}天 下工',
            hovertemplate=f"當日下工: {row['當日下工水位(m)']}m<extra></extra>"
        ))
        # 連接水位與階梯的輔助虛線
        fig.add_shape(type="line", x0=day - 0.2, y0=row['當日下工水位(m)'], x1=day - 0.2, y1=row['鑽探起點深度(m)'], line=dict(dash="dot", color="gray"))

    # 標示「翌日上工水位」 (實心倒三角形)[cite: 3]
    if pd.notna(row['翌日上工水位(m)']):
        fig.add_trace(go.Scatter(
            x=[day + 0.2], y=[row['翌日上工水位(m)']],
            mode='markers+text',
            marker=dict(symbol='triangle-down', size=14, color='black'),
            text=[f"{row['翌日上工水位(m)']} ▼"], textposition="bottom center",
            name=f'第{day}天 上工',
            hovertemplate=f"翌日上工: {row['翌日上工水位(m)']}m<extra></extra>"
        ))
        # 連接水位與階梯的輔助虛線
        fig.add_shape(type="line", x0=day + 0.2, y0=row['翌日上工水位(m)'], x1=day + 0.2, y1=row['鑽探終點深度(m)'], line=dict(dash="dot", color="gray"))

# 3. 圖表版面配置調整 (反轉 Y 軸)[cite: 3]
fig.update_layout(
    yaxis=dict(autorange="reversed", title="深度 (m)", tickfont=dict(size=14)),
    xaxis=dict(title="工作天數", tickmode='array', tickvals=edited_df['工作天數'], side='top', tickfont=dict(size=14)),
    height=700,
    showlegend=False,
    plot_bgcolor='white',
    margin=dict(l=50, r=50, t=80, b=50)
)

# 加上格線與外框
fig.update_xaxes(showline=True, linewidth=1, linecolor='black', gridcolor='#EEEEEE')
fig.update_yaxes(showline=True, linewidth=1, linecolor='black', gridcolor='#EEEEEE')

# 渲染圖表
st.plotly_chart(fig, use_container_width=True)

st.success("✅ 評估完成！您可以隨時在上方表格修改資料，本圖表與判定結果將自動更新。如需部署至雲端，只需將此腳本上傳至 GitHub 並連接 Streamlit Community Cloud 即可。")