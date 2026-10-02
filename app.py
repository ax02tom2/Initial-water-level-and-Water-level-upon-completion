import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import json
import uuid
import streamlit.components.v1 as components

st.set_page_config(page_title="鑽探上下工水位自動繪圖系統", layout="wide")

# ==========================================
# 網頁專屬背景圖 (刷淡 65%、毛邊模糊處理、防遮擋設計)
# ==========================================
page_bg_img = '''
<style>
/* 1. 將背景圖綁定在 Streamlit 最外層主容器 */
[data-testid="stAppViewContainer"] {
    background-image: url("https://images.unsplash.com/photo-1504307651254-35680f356dfd?q=80&w=2070&auto=format&fit=crop");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}
/* 2. 利用 ::before 疊加一層 65% 白色遮罩與毛邊模糊 */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(255, 255, 255, 0.5); /* 50% 刷白 */
    backdrop-filter: blur(12px);                 /* 毛玻璃效果 */
    pointer-events: none;                        /* 穿透點擊，避免按鈕失效 */
    z-index: 0;                                  /* 定位在底層 */
}
/* 3. 隱藏預設的頂部白條 */
[data-testid="stHeader"] {
    background-color: transparent !important;
}
/* 4. 將主要內容區塊拉上來，並加上一層微透明質感面板，確保資料易讀 */
.block-container {
    position: relative;
    z-index: 1;
    background-color: rgba(255, 255, 255, 0.65);
    border-radius: 15px;
    padding: 2rem;
    margin-top: 1rem;
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
}
</style>
'''
st.markdown(page_bg_img, unsafe_allow_html=True)

st.title("💧 鑽探上下工水位自動繪圖系統")

# ==========================================
# 版面參數（想微調位置，改這裡即可）
# ==========================================
RULER_X = -0.4      # 深度尺所在 x 位置
STRIP_X1 = 0.2      # 漏水層色帶右邊界（色帶寬 = STRIP_X1 - RULER_X）
X0 = 1.5            # 第 1 天資料欄的起點（越大，資料區離左側色帶越遠）
LABEL_W = 1.3       # 「工作天數／鑽探進尺」表頭格寬度
CHART_H = 1000      # 主圖高 (px)
COL_PX = 165        # 每一天欄位的寬度 (px)；圖寬依天數自動計算
MIN_W, MAX_W = 900, 1900   # 主圖寬下限 / 上限 (px)

LAYER_COLORS = {
    "完全漏水層": "#f0f0f0",
    "有水層": "#e3f2fd",
    "部分漏水層": "#e8f5e9",
    "漏水層": "#fff3e0",
}


def render_chart_with_download(fig, filename, btn_label, scale=2):
    div_id = "plt_" + uuid.uuid4().hex[:8]
    w = int(fig.layout.width)
    h = int(fig.layout.height)
    plot_html = fig.to_html(
        full_html=False, include_plotlyjs="cdn", div_id=div_id,
        config={'displayModeBar': False}
    )
    btn_style = ("padding:8px 18px; font-size:15px; cursor:pointer; border:1px solid #888; "
                 "border-radius:6px; background:#f7f7f7; margin:0 8px 8px 0;")
    html = f"""
    <div style="font-family: sans-serif;">
      <button id="png_{div_id}" style="{btn_style}">{btn_label}</button>
      <button id="svg_{div_id}" style="{btn_style}">📐 下載 SVG（向量，可再編輯）</button>
      {plot_html}
    </div>
    <script>
      function dl_{div_id}(fmt) {{
        Plotly.downloadImage(document.getElementById("{div_id}"), {{
          format: fmt, width: {w}, height: {h}, scale: {int(scale)},
          filename: {json.dumps(filename)}
        }});
      }}
      document.getElementById("png_{div_id}").addEventListener("click", function () {{ dl_{div_id}("png"); }});
      document.getElementById("svg_{div_id}").addEventListener("click", function () {{ dl_{div_id}("svg"); }});
    </script>
    """
    components.html(html, height=h + 70, scrolling=True)


# ==========================================
# 1. 資料輸入區
# ==========================================
st.write("您可以直接在下方表格輸入資料，或是上傳 Excel 檔案整批匯入，系統將自動進行漏水層判估並產出 CAD 風格圖表：")
st.write("💡 **提示**：往下新增資料時，請確實填入「工作天數」與「鑽探終點(m)」，圖表才會更新。")

uploaded_file = st.file_uploader("📂 匯入 Excel 檔案 (選填)", type=["xlsx", "xls"])

# ==========================================
# ⚙️ [可自訂參數區]：網頁初始化的預設表格內容
# ==========================================
# 調整說明：這裡將原本的預設數字替換為 np.nan (空數值) 與 "" (空字串)
# [np.nan] * 5 代表產生 5 個空列，您可以把 5 改成 10，網頁一開始就會給 10 行空格
default_data = pd.DataFrame({
    "工作天數": [np.nan] * 5,
    "日期": [""] * 5,
    "鑽探起點(m)": [np.nan] * 5,
    "鑽探終點(m)": [np.nan] * 5,
    "下工水位(m)": [np.nan] * 5,
    "上工水位(m)": [np.nan] * 5
})

if uploaded_file is not None:
    try:
        df_uploaded = pd.read_excel(uploaded_file)
        required_cols = ["工作天數", "日期", "鑽探起點(m)", "鑽探終點(m)", "下工水位(m)", "上工水位(m)"]
        missing_cols = [col for col in required_cols if col not in df_uploaded.columns]
        
        if missing_cols:
            st.error(f"❌ 上傳的 Excel 缺少以下必要表頭欄位：{', '.join(missing_cols)}。請修正後重新上傳。")
        else:
            default_data = df_uploaded[required_cols] 
            st.success("✅ Excel 檔案讀取成功！您可以在下方表格繼續微調資料。")
    except Exception as e:
        st.error(f"❌ 讀取 Excel 發生錯誤：{e}")

edited_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=False)

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
# 3. CAD 成果圖（主圖，不含圖例）
# ==========================================
st.write("---")
st.subheader("📊 最終鑽探上下工水位成果圖")

if not valid_df.empty:
    fig = go.Figure()

    max_depth = int(valid_df['鑽探終點(m)'].max())
    max_days = len(valid_df)

    x_min = -1.5
    x_max = X0 + max_days + 0.05
    y_top = -6.0
    y_bot = max_depth + 2

    chart_w = int(max(MIN_W, min(MAX_W, COL_PX * (x_max - x_min))))
    px_per_x = (chart_w - 40) / (x_max - x_min)
    px_per_y = (CHART_H - 40) / (y_bot - y_top)
    strip_px = (STRIP_X1 - RULER_X) * px_per_x
    strip_cx = (RULER_X + STRIP_X1) / 2

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
    # (C) 主體繪製：迴圈跑每一天的資料
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

        # --- 左側漏水層色帶 ---
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
        fig.add_shape(type="line", x0=x_start, y0=-2.0, x1=x_start, y1=prev_depth,
                      line=dict(color="black", width=1.5, dash="dot"))
        if idx_i == len(valid_df) - 1:
            fig.add_shape(type="line", x0=x_end, y0=-2.0, x1=x_end, y1=end_d,
                          line=dict(color="black", width=1.5, dash="dot"))

        # --- 轉折處標示深度 ---
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

    export_name = st.text_input("匯出檔名（不含副檔名）", value="鑽探與水位成果圖")
    export_scale = st.radio("輸出解析度（倍數越高越清晰，檔案也越大）", [1, 2, 3], index=1,
                            horizontal=True, format_func=lambda x: f"{x}x")
    render_chart_with_download(fig, export_name or "鑽探與水位成果圖", "📥 下載成果圖 PNG", export_scale)

    # ==========================================
    # 5. 獨立圖例
    # ==========================================
    st.subheader("🔖 圖例（獨立圖）")
    st.caption("圖例已與成果圖分開，按下方按鈕即可下載 PNG 或 SVG，再自行貼到成果圖空白處。")

    LW, LH = 230, 190
    leg = go.Figure()

    leg.add_shape(type="rect", x0=2, y0=2, x1=LW - 2, y1=LH - 2,
                  fillcolor="rgba(0,0,0,0)", line=dict(color="black", width=2))
    leg.add_annotation(x=14, y=22, text="<b>圖例（單位：m）</b>", showarrow=False,
                       xanchor="left", font=dict(size=18, color="black"))
    leg.add_shape(type="line", x0=8, y0=42, x1=LW - 8, y1=42, line=dict(color="black", width=1))

    rows = [76, 116, 156]
    sym_x, txt_x = 34, 68

    leg.add_trace(go.Scatter(
        x=[sym_x], y=[rows[0]], mode="markers",
        marker=dict(symbol="triangle-down-open", size=22, color="black", line=dict(width=2.5)),
        hoverinfo="skip"))
    leg.add_annotation(x=txt_x, y=rows[0], text="<b>當日下工水位</b>", showarrow=False,
                       xanchor="left", font=dict(size=18, color="black"))

    leg.add_trace(go.Scatter(
        x=[sym_x], y=[rows[1]], mode="markers",
        marker=dict(symbol="triangle-down", size=22, color="black"),
        hoverinfo="skip"))
    leg.add_annotation(x=txt_x, y=rows[1], text="<b>翌日上工水位</b>", showarrow=False,
                       xanchor="left", font=dict(size=18, color="black"))

    leg.add_shape(type="line", x0=14, y0=rows[2], x1=54, y1=rows[2], line=dict(color="black", width=3))
    leg.add_annotation(x=txt_x, y=rows[2], text="<b>當日鑽探進尺</b>", showarrow=False,
                       xanchor="left", font=dict(size=18, color="black"))

    leg.update_layout(
        width=LW, height=LH,
        showlegend=False,
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False, range=[0, LW], fixedrange=True),
        yaxis=dict(visible=False, range=[LH, 0], fixedrange=True)
    )

    render_chart_with_download(leg, (export_name or "鑽探與水位成果圖") + "_圖例", "📥 下載圖例 PNG", export_scale)
else:
    st.info("請在上方表格輸入工作天數及鑽探終點深度，圖表將會自動生成。")
