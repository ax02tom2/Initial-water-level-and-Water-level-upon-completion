import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="地下水位自動評估繪圖系統", layout="wide")
st.title("💧 地下水位自動評估繪圖系統")

# ==========================================
# 1. 資料輸入區 (整合成單一乾淨表格)
# ==========================================
st.write("請直接在下方表格輸入資料，系統將自動進行漏水層判估並產出 CAD 風格圖表：")

# 將上下工紀錄合併，去除重複的日期與深度欄位
default_data = pd.DataFrame({
    "工作天數": [1, 2, 3, 4, 5],
    "日期": ["3/11", "3/12", "3/13", "3/14", "3/15"],
    "鑽探起點(m)": [0.0, 3.0, 10.0, 15.0, 24.0],
    "鑽探終點(m)": [3.0, 10.0, 15.0, 24.0, 30.0],
    "下工水位(m)": [np.nan, 8.9, 11.5, 22.3, 27.6],
    "上工水位(m)": [np.nan, 9.2, 13.8, 23.2, np.nan]
})

# 顯示表格，取消自適應寬度讓欄位緊湊
edited_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=False)

# ==========================================
# 2. 漏水層判斷邏輯 (後台自動計算)
# ==========================================
def evaluate_water_layer(row):
    down_wl = row['下工水位(m)']
    up_wl = row['上工水位(m)']
    total_depth = row['鑽探終點(m)']
    
    if pd.isna(down_wl) and pd.isna(up_wl): return "完全漏水層"
    if pd.isna(up_wl) and pd.notna(down_wl): return "漏水層"
        
    drop_m = up_wl - down_wl
    
    if drop_m <= 0.3: # 容許些微波動視為無明顯變化
        return "有水層"
    else:
        ratio = drop_m / total_depth
        if ratio < 0.5: return "部分漏水層"
        else: return "漏水層"

# ==========================================
# 3. 完美還原 CAD 成果圖 (客製化 Plotly)
# ==========================================
st.write("---")
st.subheader("📊 最終鑽探與水位成果圖")

fig = go.Figure()

max_depth = int(edited_df['鑽探終點(m)'].max()) if not edited_df.empty else 30
max_days = len(edited_df)

# --------------------------------------------------
# (A) 手工繪製左側 Y 軸深度尺 (CAD 風格)[cite: 5]
# --------------------------------------------------
ruler_x = -0.4  # 深度尺的 X 基準線
# 畫深度主垂直線
fig.add_shape(type="line", x0=ruler_x, y0=0, x1=ruler_x, y1=max_depth, line=dict(color="black", width=1.5))
fig.add_annotation(x=-1.2, y=-0.5, text="<b>深度(m)</b>", showarrow=False, font=dict(size=18, color="black"), xanchor="left")

# 畫 1m 與 5m 刻度線[cite: 5]
for d in range(max_depth + 1):
    if d % 5 == 0:
        # 5m 大刻度 (向左突出較長至 -0.65)
        fig.add_shape(type="line", x0=ruler_x, y0=d, x1=-0.65, y1=d, line=dict(color="black", width=1.5))
        fig.add_annotation(x=-0.75, y=d, text=str(d), showarrow=False, font=dict(size=16, color="black"), xanchor="right")
    else:
        # 1m 小刻度 (向左突出較短至 -0.5)
        fig.add_shape(type="line", x0=ruler_x, y0=d, x1=-0.5, y1=d, line=dict(color="black", width=1))

# --------------------------------------------------
# (B) 繪製頂部表格標題列 (工作天數 & 鑽探進尺)[cite: 5]
# --------------------------------------------------
# 表格左側的標題 (在 X軸 -1.2 到 -0.1 之間)
fig.add_shape(type="rect", x0=-1.2, y0=-3, x1=-0.1, y1=-2, line=dict(color="black", width=2))
fig.add_annotation(x=-0.65, y=-2.5, text="<b>工作天數</b>", showarrow=False, font=dict(size=16))
fig.add_shape(type="rect", x0=-1.2, y0=-2, x1=-0.1, y1=-1, line=dict(color="black", width=2))
fig.add_annotation(x=-0.65, y=-1.5, text="<b>鑽探進尺</b>", showarrow=False, font=dict(size=16))

# --------------------------------------------------
# (C) 繪製圖例 (右上角)[cite: 5]
# --------------------------------------------------
leg_x0 = max_days - 1.2
leg_y0 = 1.0
fig.add_shape(type="rect", x0=leg_x0, y0=leg_y0, x1=max_days-0.1, y1=leg_y0+4.5, line=dict(color="gray", width=1))
fig.add_annotation(x=leg_x0+0.1, y=leg_y0+0.5, text="(單位：m)", showarrow=False, xanchor="left", font=dict(size=12))
fig.add_annotation(x=leg_x0+0.1, y=leg_y0+1.2, text="圖例", showarrow=False, xanchor="left", font=dict(size=14))

# 圖例：當日下工
fig.add_trace(go.Scatter(x=[leg_x0+0.2], y=[leg_y0+2.2], mode="markers", marker=dict(symbol="triangle-down-open", size=12, color="black", line=dict(width=1.5))))
fig.add_shape(type="line", x0=leg_x0+0.2, y0=leg_y0+2.2, x1=leg_x0+0.2, y1=leg_y0+3.8, line=dict(dash="dash", color="black", width=1))
fig.add_shape(type="line", x0=leg_x0+0.2, y0=leg_y0+2.2, x1=leg_x0+0.5, y1=leg_y0+2.2, line=dict(color="black", width=1))
fig.add_annotation(x=leg_x0+0.55, y=leg_y0+2.2, text="當日下工水位", showarrow=False, xanchor="left", font=dict(size=12))

# 圖例：翌日上工
fig.add_trace(go.Scatter(x=[leg_x0+0.35], y=[leg_y0+3.0], mode="markers", marker=dict(symbol="triangle-down", size=12, color="black")))
fig.add_shape(type="line", x0=leg_x0+0.35, y0=leg_y0+3.0, x1=leg_x0+0.35, y1=leg_y0+3.8, line=dict(dash="dash", color="black", width=1))
fig.add_shape(type="line", x0=leg_x0+0.35, y0=leg_y0+3.0, x1=leg_x0+0.5, y1=leg_y0+3.0, line=dict(color="black", width=1))
fig.add_annotation(x=leg_x0+0.55, y=leg_y0+3.0, text="翌日上工水位", showarrow=False, xanchor="left", font=dict(size=12))

# 圖例：鑽探進尺底線
fig.add_shape(type="line", x0=leg_x0+0.1, y0=leg_y0+3.8, x1=leg_x0+0.4, y1=leg_y0+3.8, line=dict(color="black", width=1.5))
fig.add_shape(type="line", x0=leg_x0+0.4, y0=leg_y0+3.8, x1=leg_x0+0.5, y1=leg_y0+3.8, line=dict(dash="dash", color="black", width=1))
fig.add_annotation(x=leg_x0+0.55, y=leg_y0+3.8, text="當日鑽探進尺", showarrow=False, xanchor="left", font=dict(size=12))

# --------------------------------------------------
# (D) 進入資料迴圈：繪製主體
# --------------------------------------------------
prev_depth = 0

for idx, row in edited_df.iterrows():
    day_i = int(row['工作天數'])
    x_start = day_i - 1  # 該天的左邊界 (例如 Day 1 是 x=0)
    x_end = day_i        # 該天的右邊界 (例如 Day 1 是 x=1)
    
    start_d = row['鑽探起點(m)']
    end_d = row['鑽探終點(m)']
    
    # --- 頂部表格內容寫入 ---[cite: 5]
    fig.add_shape(type="rect", x0=x_start, y0=-3, x1=x_end, y1=-2, line=dict(color="black", width=2))
    fig.add_annotation(x=(x_start+x_end)/2, y=-2.5, text=f"<b>{day_i}</b>", showarrow=False, font=dict(size=16))
    fig.add_shape(type="rect", x0=x_start, y0=-2, x1=x_end, y1=-1, line=dict(color="black", width=2))
    depth_str = f"{int(start_d)}~{int(end_d)}m" if start_d.is_integer() and end_d.is_integer() else f"{start_d}~{end_d}m"
    fig.add_annotation(x=(x_start+x_end)/2, y=-1.5, text=depth_str, showarrow=False, font=dict(size=16))

    # --- 左側窄窄的漏水層標示 ---[cite: 5]
    layer_type = evaluate_water_layer(row)
    bg_color = {"完全漏水層":"#f0f0f0", "有水層":"#e3f2fd", "部分漏水層":"#e8f5e9", "漏水層":"#fff3e0"}.get(layer_type, "white")
    
    # 色塊寬度縮到極小 (x 從 -0.4 到 -0.1)
    fig.add_shape(type="rect", x0=ruler_x, y0=start_d, x1=-0.1, y1=end_d, fillcolor=bg_color, line=dict(color="black", width=1))
    # 將文字切成直排
    vert_text = "<br>".join(list(layer_type))
    fig.add_annotation(x=-0.25, y=(start_d + end_d)/2, text=f"<b>{vert_text}</b>", showarrow=False, font=dict(size=14, color="black"))

    # --- 階梯鑽探輪廓 ---[cite: 5]
    fig.add_shape(type="line", x0=x_start, y0=prev_depth, x1=x_start, y1=end_d, line=dict(color="black", width=2)) # 垂直切線
    fig.add_shape(type="line", x0=x_start, y0=end_d, x1=x_end, y1=end_d, line=dict(color="black", width=2))        # 水平底線
    
    # 水平延伸至深度尺的虛線
    fig.add_shape(type="line", x0=-0.1, y0=end_d, x1=x_start, y1=end_d, line=dict(color="black", width=1, dash="dot"))
    # 天數之間的分隔虛線 (垂直向上)
    fig.add_shape(type="line", x0=x_start, y0=-1, x1=x_start, y1=prev_depth, line=dict(color="black", width=1, dash="dot"))
    # 最右側的收尾虛線
    if day_i == max_days:
        fig.add_shape(type="line", x0=x_end, y0=-1, x1=x_end, y1=end_d, line=dict(color="black", width=1, dash="dot"))

    # --- 上下工水位符號標示 (完全 CAD 化) ---[cite: 5]
    wl_down = row['下工水位(m)']
    wl_up = row['上工水位(m)']
    
    # 當日下工 (▽)
    if pd.notna(wl_down):
        x_pos = x_start + 0.3
        fig.add_shape(type="line", x0=x_pos, y0=wl_down, x1=x_pos, y1=end_d, line=dict(color="black", width=1.5, dash="dash"))
        fig.add_trace(go.Scatter(x=[x_pos], y=[wl_down], mode="markers+text",
            marker=dict(symbol="triangle-down-open", size=18, color="black", line=dict(width=2)),
            text=[str(wl_down)], textposition="top center", textfont=dict(size=16, color="black"), hoverinfo="skip"))
    else:
        # 若無水位，寫入「無水位」三字[cite: 5]
        fig.add_annotation(x=x_start+0.3, y=start_d + (end_d - start_d)/2, text="無<br>水<br>位", showarrow=False, font=dict(size=14, color="black"))
        
    # 翌日上工 (▼)
    if pd.notna(wl_up):
        x_pos = x_start + 0.7
        fig.add_shape(type="line", x0=x_pos, y0=wl_up, x1=x_pos, y1=end_d, line=dict(color="black", width=1.5, dash="dash"))
        fig.add_trace(go.Scatter(x=[x_pos], y=[wl_up], mode="markers+text",
            marker=dict(symbol="triangle-down", size=18, color="black"),
            text=[str(wl_up)], textposition="top center", textfont=dict(size=16, color="black"), hoverinfo="skip"))
    else:
        fig.add_annotation(x=x_start+0.7, y=start_d + (end_d - start_d)/2, text="無<br>水<br>位", showarrow=False, font=dict(size=14, color="black"))

    prev_depth = end_d

# --------------------------------------------------
# 4. 關閉 Plotly 預設坐標軸 (由上方手工繪圖完全取代)
# --------------------------------------------------
fig.update_layout(
    height=900,
    showlegend=False,
    plot_bgcolor='white',
    margin=dict(l=20, r=20, t=20, b=20),
    xaxis=dict(visible=False, range=[-1.5, max_days + 0.2]),
    yaxis=dict(visible=False, autorange="reversed", range=[max_depth + 2, -4])
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
