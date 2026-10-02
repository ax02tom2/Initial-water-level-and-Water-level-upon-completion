import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 網頁基本設定
st.set_page_config(page_title="地下水位與漏水層自動評估系統", layout="wide")
st.title("💧 地下水位與漏水層自動評估系統")

# ==========================================
# 第一部分：資料輸入區 (單一窄版表格)
# ==========================================
st.write("請在下方表格輸入深度與水位資料（圖表會自動套用文獻規則並即時更新）:")

# 預設資料
default_data = pd.DataFrame({
    "工作天數": [1, 2, 3, 4, 5],
    "鑽探起點深度(m)": [0.0, 3.0, 10.0, 15.0, 24.0],
    "鑽探終點深度(m)": [3.0, 10.0, 15.0, 24.0, 30.0],
    "當日下工水位(m)": [np.nan, 8.9, 11.5, 22.3, 27.6],
    "翌日上工水位(m)": [np.nan, 9.2, 13.8, 23.2, np.nan]
})

# 取消過度拉寬，保留適當的欄寬
edited_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=False)

# ==========================================
# 第二部分：漏水層自動判斷邏輯
# ==========================================
def evaluate_water_layer(row):
    down_wl = row['當日下工水位(m)']
    up_wl = row['翌日上工水位(m)']
    total_depth = row['鑽探終點深度(m)']
    
    # 規則 H：均無水 -> 完全漏水層
    if pd.isna(down_wl) and pd.isna(up_wl):
        return "完全漏水層"
    # 規則 F/G：翌日無水 -> 漏水層
    if pd.isna(up_wl) and pd.notna(down_wl):
        return "漏水層"
        
    drop_m = up_wl - down_wl
    
    # 規則 A~D：無明顯變化(容許0.3m內波動)或上升 -> 有水層
    if drop_m <= 0.3:
        return "有水層"
    else:
        # 下降幅度比例
        ratio = drop_m / total_depth
        # 規則 E：小幅度下降 -> 部分漏水層
        if ratio < 0.5:
            return "部分漏水層"
        # 規則 F/G：大幅度下降 -> 漏水層
        else:
            return "漏水層"

# ==========================================
# 第三部分：完美還原 CAD 成果圖
# ==========================================
st.write("---")
st.write("📊 **水位與鑽探剖面成果圖**")

fig = go.Figure()

prev_depth = 0
max_depth = edited_df['鑽探終點深度(m)'].max() if not edited_df.empty else 30

for idx, row in edited_df.iterrows():
    day_i = int(row['工作天數'])
    x_start = day_i - 1  # 該天的左邊界
    x_end = day_i        # 該天的右邊界
    start_d = row['鑽探起點深度(m)']
    end_d = row['鑽探終點深度(m)']
    
    # --------------------------------------------------
    # 1. 繪製左側小小的漏水層判定區塊 (X座標介於 -1 到 0 之間)
    # --------------------------------------------------
    layer_type = evaluate_water_layer(row)
    colors = {
        "完全漏水層": "#e6e6e6",  # 灰色
        "有水層": "#e3f2fd",      # 淺藍色
        "部分漏水層": "#e8f5e9",  # 淺綠色
        "漏水層": "#fff3e0"       # 淺橘色
    }
    bg_color = colors.get(layer_type, "#ffffff")
    
    # 畫背景色塊
    fig.add_shape(type="rect", x0=-1, y0=start_d, x1=0, y1=end_d,
                  fillcolor=bg_color, line=dict(color="black", width=1))
                  
    # 寫入垂直文字 (用 <br> 將每個字斷行)
    vertical_text = "<br>".join(list(layer_type))
    fig.add_annotation(x=-0.5, y=(start_d + end_d)/2, text=vertical_text,
                       showarrow=False, font=dict(size=12, color="black"))

    # --------------------------------------------------
    # 2. 繪製階梯狀的鑽探進尺 (實心黑線)
    # --------------------------------------------------
    # 垂直下切線
    fig.add_shape(type="line", x0=x_start, y0=prev_depth, x1=x_start, y1=end_d,
                  line=dict(color="black", width=2))
    # 水平底線
    fig.add_shape(type="line", x0=x_start, y0=end_d, x1=x_end, y1=end_d,
                  line=dict(color="black", width=2))
    
    # 每天的分界線 (垂直點線)
    fig.add_shape(type="line", x0=x_end, y0=0, x1=x_end, y1=max_depth,
                  line=dict(color="gray", width=1, dash="dot"))

    # --------------------------------------------------
    # 3. 繪製上下工水位符號與虛線 (CAD 箭頭風格)
    # --------------------------------------------------
    wl_down = row['當日下工水位(m)']
    wl_up = row['翌日上工水位(m)']
    
    # 當日下工 (▽ 空心倒三角)
    if pd.notna(wl_down):
        x_pos = x_start + 0.3
        # 往下延伸的虛線
        fig.add_shape(type="line", x0=x_pos, y0=wl_down, x1=x_pos, y1=end_d,
                      line=dict(color="black", width=1, dash="dash"))
        # ▽ 符號與文字
        fig.add_trace(go.Scatter(
            x=[x_pos], y=[wl_down], mode="markers+text",
            marker=dict(symbol="triangle-down-open", size=14, color="black", line=dict(width=1.5)),
            text=[str(wl_down)], textposition="top center", textfont=dict(size=12, color="black"),
            hoverinfo="skip"
        ))
        
    # 翌日上工 (▼ 實心倒三角)
    if pd.notna(wl_up):
        x_pos = x_start + 0.7
        # 往下延伸的虛線
        fig.add_shape(type="line", x0=x_pos, y0=wl_up, x1=x_pos, y1=end_d,
                      line=dict(color="black", width=1, dash="dash"))
        # ▼ 符號與文字
        fig.add_trace(go.Scatter(
            x=[x_pos], y=[wl_up], mode="markers+text",
            marker=dict(symbol="triangle-down", size=14, color="black"),
            text=[str(wl_up)], textposition="top center", textfont=dict(size=12, color="black"),
            hoverinfo="skip"
        ))

    prev_depth = end_d

# --------------------------------------------------
# 4. 圖表排版與坐標軸設定 (符合每公尺刻度要求)
# --------------------------------------------------
fig.update_layout(
    height=850, # 拉高圖表讓 1m 刻度不會太擠
    showlegend=False,
    plot_bgcolor='white',
    margin=dict(l=40, r=40, t=60, b=40),
    xaxis=dict(
        showgrid=False,
        zeroline=False,
        side='top',
        tickmode='array',
        tickvals=[0.5, 1.5, 2.5, 3.5, 4.5],
        ticktext=["第1天", "第2天", "第3天", "第4天", "第5天"],
        range=[-1, len(edited_df)]
    ),
    yaxis=dict(
        title="深度(m)",
        autorange="reversed",
        showgrid=True,          
        gridcolor="#f0f0f0",    
        zeroline=False,
        showline=True,
        linecolor="black",
        linewidth=1,
        dtick=1, # <--- 強制每一公尺顯示一個刻度
        tickfont=dict(size=11)
    )
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
