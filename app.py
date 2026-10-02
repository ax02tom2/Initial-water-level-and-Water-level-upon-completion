import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="地下水位自動評估繪圖系統", layout="wide")
st.title("💧 地下水位自動評估繪圖系統")

# ==========================================
# 版面參數（想微調位置，改這裡即可）
# ==========================================
RULER_X = -0.4      # 深度尺所在 x 位置
STRIP_X1 = 0.2      # 漏水層色帶右邊界（色帶寬 = STRIP_X1 - RULER_X）
X0 = 2.1            # 第 1 天資料欄的起點（越大，資料區離左側色帶越遠）
LABEL_W = 1.3       # 「工作天數／鑽探進尺」表頭格寬度
CHART_H = 1000      # 圖高 (px)
COL_PX = 165        # 每一天欄位的寬度 (px)；圖寬會依天數自動計算，不再留白
MIN_W, MAX_W = 900, 1900   # 圖寬下限 / 上限 (px)

LAYER_COLORS = {
    "完全漏水層": "#f0f0f0",
    "有水層": "#e3f2fd",
    "部分漏水層": "#e8f5e9",
    "漏水層": "#fff3e0",
}

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

# 防呆：自動過濾掉還沒輸入完成的空白列，避免報錯
valid_df = edited_df.dropna(subset=['工作天數', '鑽探終點(m)']).copy()


# ==========================================
# 2. 漏水層判斷邏輯
# ==========================================
def evaluate_water_layer(row):
    down_wl = row['下工水位(m)']
    up_wl = row['上工水位(m)']
    total_depth = row['鑽探終點(m)']

    if pd.isna(down_wl) and pd.isna(up_wl):
        return "完全漏水層"
    if pd.isna(up_wl) and pd.notna(down_wl):
        return "漏水層"

    drop_m = up_wl - down_wl
    if drop_m <= 0.3:
        return "有水層"
    else:
        ratio = drop_m / total_depth
        if ratio < 0.5:
            return "部分漏水層"
        else:
            return "漏水層"


def fit_layer_text(label, seg_h_px, strip_px):
    """
    依色帶實際可用的寬、高，自動決定漏水層文字排法與字級：
      1. 優先「直排單欄」(如：有／水／層)
      2. 放不下且字數 >= 4 時，改「分兩排」(如：完全 / 漏水層)
      3. 字級由大到小嘗試 (20 → 10)，確保不超出色帶
    回傳 (文字, 字級)
    """
    n = len(label)
    for f in range(20, 9, -1):
        line_h = f * 1.25
        if f * 1.1 <= strip_px * 0.9 and n * line_h <= seg_h_px * 0.92:
            return "<br>".join(label), f
        if n >= 4:
            k = n // 2
            rows = [label[:k], label[k:]]
            w = max(len(r) for r in rows) * f * 1.05
            if w <= strip_px * 0.92 and 2 * line_h <= seg_h_px * 0.92:
                return "<br>".join(rows), f
    if n >= 4:
        k = n // 2
        return label[:k] + "<br>" + label[k:], 10
    return "<br>".join(label), 10


# ==========================================
# 3. CAD 成果圖
# ==========================================
st.write("---")
st.subheader("📊 最終鑽探與水位成果圖")

if not valid_df.empty:
    fig = go.Figure()

    max_depth = int(valid_df['鑽探終點(m)'].max())
    max_days = len(valid_df)

    x_min = -1.5
    x_max = X0 + max_days + 0.05      # 右側幾乎不留白
    y_top = -6.0
    y_bot = max_depth + 2

    # 圖寬依天數自動決定（固定寬度，像素換算才精準）
    chart_w = int(max(MIN_W, min(MAX_W, COL_PX * (x_max - x_min))))
    px_per_x = (chart_w - 40) / (x_max - x_min)
    px_per_y = (CHART_H - 40) / (y_bot - y_top)
    strip_px = (STRIP_X1 - RULER_X) * px_per_x
    strip_cx = (RULER_X + STRIP_X1) / 2

    def dx(px):
        return px / px_per_x

    def dy(px):
        return px / px_per_y

    # --------------------------------------------------
    # 圖例幾何（以「像素」設計，再換算成座標；靠右上角、寬度精簡）
    # --------------------------------------------------
    LEG_W, LEG_H = 215, 335
    leg_x1 = x_max - dx(6)
    leg_x0 = leg_x1 - dx(LEG_W)
    leg_y0 = 0.3
    leg_y1 = leg_y0 + dy(LEG_H)

    def lx(px):
        return leg_x0 + dx(px)

    def ly(px):
        return leg_y0 + dy(px)

    def add_dotted_v(x, ya, yb):
        """畫垂直點線；經過圖例範圍時自動斷開，避免穿過圖例"""
        if yb <= ya:
            return
        segs = [(ya, yb)]
        if leg_x0 <= x <= leg_x1:
            new = []
            for a, b in segs:
                if b <= leg_y0 or a >= leg_y1:
                    new.append((a, b))
                else:
                    if a < leg_y0:
                        new.append((a, leg_y0))
                    if b > leg_y1:
                        new.append((leg_y1, b))
            segs = new
        for a, b in segs:
            fig.add_shape(type="line", x0=x, y0=a, x1=x, y1=b,
                          line=dict(color="black", width=1.5, dash="dot"))

    # --------------------------------------------------
    # (A) 左側 Y 軸深度尺
    # --------------------------------------------------
    fig.add_annotation(x=-1.4, y=-1.0, text="<b>深度(m)</b>", showarrow=False,
                       font=dict(size=26, color="black"), xanchor="left")
    fig.add_shape(type="line", x0=RULER_X, y0=0, x1=RULER_X, y1=max_depth, line=dict(color="black", width=2))

    for d in range(max_depth + 1):
        if d % 5 == 0:
            fig.add_shape(type="line", x0=RULER_X, y0=d, x1=-0.7, y1=d, line=dict(color="black", width=2.5))
            fig.add_annotation(x=-0.8, y=d, text=f"<b>{d}</b>", showarrow=False,
                               font=dict(size=26, color="black"), xanchor="right")
        else:
            fig.add_shape(type="line", x0=RULER_X, y0=d, x1=-0.5, y1=d, line=dict(color="black", width=1))

    # --------------------------------------------------
    # (B) 頂部表格標題
    # --------------------------------------------------
    lx0 = X0 - LABEL_W
    lx1 = X0
    lcx = (lx0 + lx1) / 2
    fig.add_shape(type="rect", x0=lx0, y0=-5.0, x1=lx1, y1=-3.5, line=dict(color="black", width=2))
    fig.add_annotation(x=lcx, y=-4.25, text="<b>工作天數</b>", showarrow=False, font=dict(size=24))
    fig.add_shape(type="rect", x0=lx0, y0=-3.5, x1=lx1, y1=-2.0, line=dict(color="black", width=2))
    fig.add_annotation(x=lcx, y=-2.75, text="<b>鑽探進尺</b>", showarrow=False, font=dict(size=24))

    # --------------------------------------------------
    # (C) 圖例：水位符號 + 漏水層色塊說明
    #   白底框 layer="below"，三角形(trace)才不會被蓋住
    # --------------------------------------------------
    fig.add_shape(type="rect", x0=leg_x0, y0=leg_y0, x1=leg_x1, y1=leg_y1,
                  fillcolor="white", line=dict(color="black", width=2), layer="below")

    # 標題
    fig.add_annotation(x=lx(14), y=ly(20), text="<b>圖例（單位：m）</b>", showarrow=False,
                       xanchor="left", font=dict(size=17, color="black"))
    fig.add_shape(type="line", x0=lx(8), y0=ly(38), x1=lx(LEG_W - 8), y1=ly(38),
                  line=dict(color="black", width=1))

    # 水位符號三列（間距 40px，符號在左、文字在右）
    r1, r2, r3 = 66, 106, 146
    sym_x, txt_x = 34, 68

    fig.add_trace(go.Scatter(
        x=[lx(sym_x)], y=[ly(r1)], mode="markers",
        marker=dict(symbol="triangle-down-open", size=20, color="black", line=dict(width=2.5)),
        hoverinfo="skip"))
    fig.add_annotation(x=lx(txt_x), y=ly(r1), text="<b>當日下工水位</b>", showarrow=False,
                       xanchor="left", font=dict(size=17, color="black"))

    fig.add_trace(go.Scatter(
        x=[lx(sym_x)], y=[ly(r2)], mode="markers",
        marker=dict(symbol="triangle-down", size=20, color="black"),
        hoverinfo="skip"))
    fig.add_annotation(x=lx(txt_x), y=ly(r2), text="<b>翌日上工水位</b>", showarrow=False,
                       xanchor="left", font=dict(size=17, color="black"))

    fig.add_shape(type="line", x0=lx(14), y0=ly(r3), x1=lx(54), y1=ly(r3),
                  line=dict(color="black", width=3), layer="above")
    fig.add_annotation(x=lx(txt_x), y=ly(r3), text="<b>當日鑽探進尺</b>", showarrow=False,
                       xanchor="left", font=dict(size=17, color="black"))

    # 漏水層色塊說明
    fig.add_shape(type="line", x0=lx(8), y0=ly(172), x1=lx(LEG_W - 8), y1=ly(172),
                  line=dict(color="black", width=1))
    fig.add_annotation(x=lx(14), y=ly(192), text="<b>漏水層分類</b>", showarrow=False,
                       xanchor="left", font=dict(size=16, color="black"))

    for i, name in enumerate(["完全漏水層", "有水層", "部分漏水層", "漏水層"]):
        ry = 224 + i * 32
        fig.add_shape(type="rect", x0=lx(14), y0=ly(ry - 11), x1=lx(50), y1=ly(ry + 11),
                      fillcolor=LAYER_COLORS[name], line=dict(color="black", width=1), layer="above")
        fig.add_annotation(x=lx(62), y=ly(ry), text=f"<b>{name}</b>", showarrow=False,
                           xanchor="left", font=dict(size=16, color="black"))

    # --------------------------------------------------
    # (D) 主體繪製：迴圈跑每一天的資料
    # --------------------------------------------------
    prev_depth = 0

    for idx_i, (idx, row) in enumerate(valid_df.iterrows()):
        day_i = int(row['工作天數'])
        x_start = X0 + idx_i
        x_end = X0 + idx_i + 1

        start_d = row['鑽探起點(m)']
        end_d = row['鑽探終點(m)']
        if pd.isna(start_d):
            start_d = prev_depth

        # --- 頂部表格內容 ---
        fig.add_shape(type="rect", x0=x_start, y0=-5.0, x1=x_end, y1=-3.5, line=dict(color="black", width=2))
        fig.add_annotation(x=(x_start + x_end) / 2, y=-4.25, text=f"<b>{day_i}</b>", showarrow=False, font=dict(size=26))
        fig.add_shape(type="rect", x0=x_start, y0=-3.5, x1=x_end, y1=-2.0, line=dict(color="black", width=2))
        depth_str = (f"<b>{int(start_d)}~{int(end_d)}m</b>"
                     if float(start_d).is_integer() and float(end_d).is_integer()
                     else f"<b>{start_d}~{end_d}m</b>")
        fig.add_annotation(x=(x_start + x_end) / 2, y=-2.75, text=depth_str, showarrow=False, font=dict(size=26))

        # --- 左側漏水層色帶（文字自動排版，不超出色帶）---
        layer_type = evaluate_water_layer(row)
        bg_color = LAYER_COLORS.get(layer_type, "white")

        fig.add_shape(type="rect", x0=RULER_X, y0=start_d, x1=STRIP_X1, y1=end_d,
                      fillcolor=bg_color, line=dict(color="black", width=1))

        seg_h_px = (end_d - start_d) * px_per_y
        layer_text, layer_font = fit_layer_text(layer_type, seg_h_px, strip_px)
        fig.add_annotation(x=strip_cx, y=(start_d + end_d) / 2, text=f"<b>{layer_text}</b>",
                           showarrow=False, font=dict(size=layer_font, color="black"))

        # --- 階梯鑽探輪廓 ---
        fig.add_shape(type="line", x0=x_start, y0=prev_depth, x1=x_start, y1=end_d, line=dict(color="black", width=2))
        fig.add_shape(type="line", x0=x_start, y0=end_d, x1=x_end, y1=end_d, line=dict(color="black", width=2))

        fig.add_shape(type="line", x0=STRIP_X1, y0=end_d, x1=x_start, y1=end_d,
                      line=dict(color="black", width=1.5, dash="dot"))
        add_dotted_v(x_start, -2.0, prev_depth)

        if idx_i == len(valid_df) - 1:
            add_dotted_v(x_end, -2.0, end_d)

        # --- 轉折處標示深度：直角(x_start, end_d)左上方 ---
        corner_text = f"{int(end_d)}m" if float(end_d).is_integer() else f"{end_d}m"
        fig.add_annotation(
            x=x_start, y=end_d,
            text=f"<b>{corner_text}</b>",
            showarrow=False,
            xanchor="right", yanchor="bottom",
            xshift=-8, yshift=6,
            font=dict(size=26, color="black")
        )

        # --- 上下工水位符號與「無水位」標示 ---
        wl_down = row['下工水位(m)']
        wl_up = row['上工水位(m)']

        if pd.notna(wl_down):
            x_pos = x_start + 0.3
            fig.add_shape(type="line", x0=x_pos, y0=wl_down, x1=x_pos, y1=end_d,
                          line=dict(color="black", width=1.5, dash="dash"))
            fig.add_trace(go.Scatter(
                x=[x_pos], y=[wl_down], mode="markers+text",
                marker=dict(symbol="triangle-down-open", size=26, color="black", line=dict(width=2.5)),
                text=[f"<b>{wl_down}</b>"], textposition="top center",
                textfont=dict(size=26, color="black"), hoverinfo="skip"))
        else:
            fig.add_annotation(
                x=x_start + 0.3, y=end_d,
                text="<b>無<br>水<br>位</b>",
                showarrow=False,
                yanchor="bottom", yshift=4,
                font=dict(size=24, color="black")
            )

        if pd.notna(wl_up):
            x_pos = x_start + 0.7
            fig.add_shape(type="line", x0=x_pos, y0=wl_up, x1=x_pos, y1=end_d,
                          line=dict(color="black", width=1.5, dash="dash"))
            fig.add_trace(go.Scatter(
                x=[x_pos], y=[wl_up], mode="markers+text",
                marker=dict(symbol="triangle-down", size=26, color="black"),
                text=[f"<b>{wl_up}</b>"], textposition="top center",
                textfont=dict(size=26, color="black"), hoverinfo="skip"))
        else:
            fig.add_annotation(
                x=x_start + 0.7, y=end_d,
                text="<b>無<br>水<br>位</b>",
                showarrow=False,
                yanchor="bottom", yshift=4,
                font=dict(size=24, color="black")
            )

        prev_depth = end_d

    # --------------------------------------------------
    # 4. 關閉 Plotly 預設坐標軸並設定範圍
    # --------------------------------------------------
    fig.update_layout(
        width=chart_w,
        height=CHART_H,
        showlegend=False,
        plot_bgcolor='white',
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(visible=False, range=[x_min, x_max]),
        yaxis=dict(visible=False, autorange="reversed", range=[y_bot, y_top])
    )

    st.plotly_chart(fig, use_container_width=False, config={'displayModeBar': False})
else:
    st.info("請在上方表格輸入工作天數及鑽探終點深度，圖表將會自動生成。")
