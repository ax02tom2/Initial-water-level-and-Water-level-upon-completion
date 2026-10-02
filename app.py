import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="地下水位自動評估繪圖系統", layout="wide")
st.title("💧 地下水位自動評估繪圖系統")

# ==========================================
# 1. 資料輸入區
# ==========================================
st.write("請直接在下方表格輸入資料，系統將自動進行漏水層判估並產出 CAD 風格圖表：")
st.write("💡 **提示**：往下新增資料時，請確實填入「工作天數」與「鑽探終點(m)」，圖表才會更新。")

default_data = pd.DataFrame({
    "工作天數": [1.0, 2.0, 3.0, 4.0, 5.0],
    "日期": ["3/11", "3/12", "3/13", "3/14", "3/15"],
    "鑽探起點(m)": [0.0, 3.0, 10.0, 15.0, 24.0],
    "鑽探終點(m)": [3.0, 10.0, 15.0, 24.0, 30.0],
    "下工水位(m)": [np.nan, 8.9, 11.5, 22.3, 27.6],
    "上工水位(m)": [np.nan, 9.2, 13.8, 23.2, np.nan]
})

edited_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=False)

# 防呆處理：過濾未輸入完成的空白列
valid_df = edited_df.dropna(subset=['工作天數', '鑽探終點(m)']).copy()

# ==========================================
# 2. 漏水層判斷邏輯
# ==========================================
def evaluate_water_layer(row):
    down_wl = row['下工水位(m)']
    up_wl = row['上工水位(m)']
    total_depth = row['鑽探終點(m)']
    
    if pd.isna(down_wl) and pd.isna(up_wl): return "完全漏水層"
    if pd.isna(up_wl) and pd.notna(down_wl): return "漏水層"
        
    drop_m = up_wl - down_wl
    if drop_m <= 0.3: 
        return "有水層"
    else:
        ratio = drop_m / total_depth
        if ratio < 0.5: return "部分漏水層"
        else: return "漏水層"

# ==========================================
# 3. 完美還原 CAD 成果圖
# ==========================================
st.write("---")
st.subheader("📊 最終鑽探與水位成果圖")

if not valid_df.empty:
    fig = go.Figure()

    max_depth = int(valid_df['鑽探終點(m)'].max())
    max_days = len(valid_df)
    ruler_x = -0.5  # 深度尺位置

    # --------------------------------------------------
    # (A) 左側 Y 軸深度尺
    # --------------------------------------------------
    fig.add_annotation(x=-1.5, y=-1.0, text="<b>深度(m)</b>", showarrow=False, font=dict(size=24, color="black"), xanchor="left")
    fig.add_shape(type="line", x0=ruler_x, y0=0, x1=ruler_x, y1=max_depth, line=dict(color="black", width=2))

    for d in range(max_depth + 1):
        if d % 5 == 0:
            fig.add_shape(type="line", x0=ruler_x, y0=d, x1=-0.8, y1=d, line=dict(color="black", width=2.5))
            fig.add_annotation(x=-0.9, y=d, text=f"<b>{d}</b>", showarrow=False, font=dict(size=24, color="black"), xanchor="right")
        else:
            fig.add_shape(type="line", x0=ruler_x, y0=d, x1=-0.65, y1=d, line=dict(color="black", width=1.5))

    # --------------------------------------------------
    # (B) 頂部表格標題 (要求3: 往左移拉開距離)
    # --------------------------------------------------
    # 標題框線範圍往左推，設定在 -2.8 到 -1.0 之間
    fig.add_shape(type="rect", x0=-2.8, y0=-5.0, x1=-1.0, y1=-3.5, line=dict(color="black", width=2))
    fig.add_annotation(x=-1.9, y=-4.25, text="<b>工作天數</b>", showarrow=False, font=dict(size=24))
    fig.add_shape(type="rect", x0=-2.8, y0=-3.5, x1=-1.0, y1=-2.0, line=dict(color="black", width=2))
    fig.add_annotation(x=-1.9, y=-2.75, text="<b>鑽探進尺</b>", showarrow=False, font=dict(size=24))

    # --------------------------------------------------
    # (C) 強化版清晰圖例 (要求4: 修復三角形被白底遮蓋)
    # --------------------------------------------------
    leg_x0 = max_days - 1.9
    leg_y0 = 0.5
    # 將 fillcolor 背景框設為 layer="below" 確保不遮擋 Scatter 符號
    fig.add_shape(type="rect", x0=leg_x0, y0=leg_y0, x1=max_days-0.1, y1=leg_y0+5.5, fillcolor="white", line=dict(color="black", width=2), layer="below")
    fig.add_annotation(x=leg_x0+0.1, y=leg_y0+0.8, text="<b>(單位：m)</b>", showarrow=False, xanchor="left", font=dict(size=18))
    fig.add_annotation(x=leg_x0+0.1, y=leg_y0+1.6, text="<b>圖例</b>", showarrow=False, xanchor="left", font=dict(size=22))

    # 下工圖例 (▽)
    fig.add_trace(go.Scatter(x=[leg_x0+0.25], y=[leg_y0+2.8], mode="markers", marker=dict(symbol="triangle-down-open", size=22, color="black", line=dict(width=2.5)), hoverinfo="skip"))
    fig.add_shape(type="line", x0=leg_x0+0.25, y0=leg_y0+2.8, x1=leg_x0+0.25, y1=leg_y0+4.6, line=dict(dash="dash", color="black", width=1.5), layer="below")
    fig.add_shape(type="line", x0=leg_x0+0.25, y0=leg_y0+2.8, x1=leg_x0+0.6, y1=leg_y0+2.8, line=dict(color="black", width=1.5), layer="below")
    fig.add_annotation(x=leg_x0+0.7, y=leg_y0+2.8, text="<b>當日下工水位</b>", showarrow=False, xanchor="left", font=dict(size=20))

    # 上工圖例 (▼)
    fig.add_trace(go.Scatter(x=[leg_x0+0.45], y=[leg_y0+3.8], mode="markers", marker=dict(symbol="triangle-down", size=22, color="black"), hoverinfo="skip"))
    fig.add_shape(type="line", x0=leg_x0+0.45, y0=leg_y0+3.8, x1=leg_x0+0.45, y1=leg_y0+4.6, line=dict(dash="dash", color="black", width=1.5), layer="below")
    fig.add_shape(type="line", x0=leg_x0+0.45, y0=leg_y0+3.8, x1=leg_x0+0.6, y1=leg_y0+3.8, line=dict(color="black", width=1.5), layer="below")
    fig.add_annotation(x=leg_x0+0.7, y=leg_y0+3.8, text="<b>翌日上工水位</b>", showarrow=False, xanchor="left", font=dict(size=20))

    # 進尺底線圖例
    fig.add_shape(type="line", x0=leg_x0+0.1, y0=leg_y0+4.6, x1=leg_x0+0.5, y1=leg_y0+4.6, line=dict(color="black", width=2), layer="below")
    fig.add_shape(type="line", x0=leg_x0+0.5, y0=leg_y0+4.6, x1=leg_x0+0.6, y1=leg_y0+4.6, line=dict(dash="dash", color="black", width=1.5), layer="below")
    fig.add_annotation(x=leg_x0+0.7, y=leg_y0+4.6, text="<b>當日鑽探進尺</b>", showarrow=False, xanchor="left", font=dict(size=20))

    # --------------------------------------------------
    # (D) 主體繪製：迴圈跑每一天的資料
    # --------------------------------------------------
    prev_depth = 0

    for idx_i, (idx, row) in enumerate(valid_df.iterrows()):
        day_i = int(row['工作天數'])
        x_start = idx_i  
        x_end = idx_i + 1
        
        start_d = row['鑽探起點(m)']
        end_d = row['鑽探終點(m)']
        
        # --- 頂部表格內容寫入 ---
        fig.add_shape(type="rect", x0=x_start, y0=-5.0, x1=x_end, y1=-3.5, line=dict(color="black", width=2))
        fig.add_annotation(x=(x_start+x_end)/2, y=-4.25, text=f"<b>{day_i}</b>", showarrow=False, font=dict(size=24))
        fig.add_shape(type="rect", x0=x_start, y0=-3.5, x1=x_end, y1=-2.0, line=dict(color="black", width=2))
        depth_str = f"<b>{int(start_d)}~{int(end_d)}m</b>" if float(start_d).is_integer() and float(end_d).is_integer() else f"<b>{start_d}~{end_d}m</b>"
        fig.add_annotation(x=(x_start+x_end)/2, y=-2.75, text=depth_str, showarrow=False, font=dict(size=24))

        # --- 左側窄窄的漏水層標示 (要求1: 動態排版避免超出線) ---
        layer_type = evaluate_water_layer(row)
        bg_color = {"完全漏水層":"#f0f0f0", "有水層":"#e3f2fd", "部分漏水層":"#e8f5e9", "漏水層":"#fff3e0"}.get(layer_type, "white")
        
        fig.add_shape(type="rect", x0=ruler_x, y0=start_d, x1=-0.1, y1=end_d, fillcolor=bg_color, line=dict(color="black", width=1))
        
        # 動態字體與排版處理 (5個字拆雙排，3個字單排)
        if len(layer_type) >= 5:
            vert_text = f"{layer_type[0]}&nbsp;&nbsp;{layer_type[2]}<br>{layer_type[1]}&nbsp;&nbsp;{layer_type[3]}<br>&nbsp;&nbsp;&nbsp;{layer_type[4]}"
            f_size = 14
        else:
            vert_text = "<br>".join(list(layer_type))
            f_size = 20

        fig.add_annotation(x=-0.3, y=(start_d + end_d)/2, text=f"<b>{vert_text}</b>", showarrow=False, font=dict(size=f_size, color="black"))

        # --- 階梯鑽探輪廓 ---
        fig.add_shape(type="line", x0=x_start, y0=prev_depth, x1=x_start, y1=end_d, line=dict(color="black", width=2.5))
        fig.add_shape(type="line", x0=x_start, y0=end_d, x1=x_end, y1=end_d, line=dict(color="black", width=2.5))
        
        fig.add_shape(type="line", x0=-0.1, y0=end_d, x1=x_start, y1=end_d, line=dict(color="black", width=1.5, dash="dot"))
        fig.add_shape(type="line", x0=x_start, y0=-2.0, x1=x_start, y1=prev_depth, line=dict(color="black", width=1.5, dash="dot"))
        
        if idx_i == len(valid_df) - 1:
            fig.add_shape(type="line", x0=x_end, y0=-2.0, x1=x_end, y1=end_d, line=dict(color="black", width=1.5, dash="dot"))

        # --- 轉折處標示深度 (要求2: 修正至直角左側內彎處) ---
        corner_text = f"{int(end_d)}m" if float(end_d).is_integer() else f"{end_d}m"
        fig.add_annotation(
            x=x_start, y=end_d, # 定位在該階的左下轉角
            text=f"<b>{corner_text}</b>", 
            showarrow=False, 
            xanchor="left", yanchor="bottom", # 從直角的右上方長出去
            xshift=8, yshift=6,               
            font=dict(size=24, color="black")
        )

        # --- 上下工水位符號與「無水位」貼齊底線 ---
        wl_down = row['下工水位(m)']
        wl_up = row['上工水位(m)']
        
        # 當日下工 (▽)
        if pd.notna(wl_down):
            x_pos = x_start + 0.3
            fig.add_shape(type="line", x0=x_pos, y0=wl_down, x1=x_pos, y1=end_d, line=dict(color="black", width=1.5, dash="dash"))
            fig.add_trace(go.Scatter(x=[x_pos], y=[wl_down], mode="markers+text",
                marker=dict(symbol="triangle-down-open", size=26, color="black", line=dict(width=2.5)),
                text=[f"<b>{wl_down}</b>"], textposition="top center", textfont=dict(size=24, color="black"), hoverinfo="skip"))
        else:
            fig.add_annotation(
                x=x_start+0.3, y=end_d, 
                text="<b>無<br>水<br>位</b>", 
                showarrow=False, 
                yanchor="bottom", yshift=4, # 確保完美貼齊不亂飄
                font=dict(size=22, color="black")
            )
            
        # 翌日上工 (▼)
        if pd.notna(wl_up):
            x_pos = x_start + 0.7
            fig.add_shape(type="line", x0=x_pos, y0=wl_up, x1=x_pos, y1=end_d, line=dict(color="black", width=1.5, dash="dash"))
            fig.add_trace(go.Scatter(x=[x_pos], y=[wl_up], mode="markers+text",
                marker=dict(symbol="triangle-down", size=26, color="black"),
                text=[f"<b>{wl_up}</b>"], textposition="top center", textfont=dict(size=24, color="black"), hoverinfo="skip"))
        else:
            fig.add_annotation(
                x=x_start+0.7, y=end_d, 
                text="<b>無<br>水<br>位</b>", 
                showarrow=False, 
                yanchor="bottom", yshift=4,
                font=dict(size=22, color="black")
            )

        prev_depth = end_d

    # --------------------------------------------------
    # 4. 圖表顯示範圍設定
    # --------------------------------------------------
    fig.update_layout(
        height=950, 
        showlegend=False,
        plot_bgcolor='white',
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(visible=False, range=[-3.0, max_days + 0.2]), # X 軸留足空間給頂部表格
        yaxis=dict(visible=False, autorange="reversed", range=[max_depth + 2, -6.0])
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("請在上方表格輸入工作天數及鑽探終點深度，圖表將會自動生成。")
