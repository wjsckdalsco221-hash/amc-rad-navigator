import os
import io
import base64
import streamlit as st
import numpy as np
from PIL import Image, ImageDraw
import streamlit.components.v1 as components

# ---------------------------------------------------------
# 1. 기본 레이아웃 설정 (와이드 모드 활성화)
# ---------------------------------------------------------
st.set_page_config(
    page_title="서울아산병원 검사실 길 안내",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 세션 상태 초기화
if "page" not in st.session_state:
    st.session_state.page = "home"
if "selected_exam_idx" not in st.session_state:
    st.session_state.selected_exam_idx = 0
if "sel_bldg" not in st.session_state:
    st.session_state.sel_bldg = "동관"
if "sel_floor" not in st.session_state:
    st.session_state.sel_floor = "2층"
if "start_key" not in st.session_state:
    st.session_state.start_key = "2F_EAST_XRAY"
if "day_type" not in st.session_state:
    st.session_state.day_type = "평일(월~금)"
if "time_str" not in st.session_state:
    st.session_state.time_str = "14:20"

# ---------------------------------------------------------
# 2. 반응형 CSS (홈 화면: 480px 모바일 뷰 / 지도 화면: 1200px 와이드 뷰)
# ---------------------------------------------------------
if st.session_state.page == "home":
    container_max_width = "480px"
    padding_top = "2.6rem"
else:
    container_max_width = "1200px"  # 지도 화면 가로 확장
    padding_top = "2.0rem"

st.markdown(f"""
<style>
/* 상단 기본 헤더 투명화 */
header[data-testid="stHeader"] {{
    background: transparent !important;
    height: 1.5rem !important;
}}

/* 페이지 상태별 가로 폭 동적 조절 */
.block-container {{
    max-width: {container_max_width} !important;
    padding-top: {padding_top} !important;
    padding-bottom: 3rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    margin: 0 auto !important;
    transition: max-width 0.3s ease;
}}

/* 상단 서울아산병원 길안내 헤더 */
.app-header {{
    background: linear-gradient(135deg, #005C5C 0%, #003A3A 100%);
    color: white;
    padding: 18px 20px;
    border-radius: 14px;
    margin-top: 6px;
    margin-bottom: 18px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.12);
    box-sizing: border-box;
    width: 100%;
}}
.app-header h3 {{
    margin: 0;
    font-size: 1.22rem;
    font-weight: 800;
    color: #FFFFFF;
    line-height: 1.4;
}}
.app-header p {{
    margin: 6px 0 0 0;
    font-size: 0.85rem;
    color: #D2EBEB;
    line-height: 1.35;
}}

/* 검사 일정 카드 */
.exam-row-wrap {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 8px;
}}
.exam-pill {{
    background-color: #F0F5FF;
    color: #1D4ED8;
    font-weight: 700;
    font-size: 0.86rem;
    padding: 5px 14px;
    border-radius: 20px;
    white-space: nowrap;
    margin-top: 2px;
}}
.exam-info-col {{
    flex: 1;
}}
.exam-title-txt {{
    font-size: 1.05rem;
    font-weight: 800;
    color: #111111;
    margin-bottom: 4px;
    line-height: 1.35;
}}
.exam-sub-txt {{
    font-size: 0.87rem;
    color: #6B7280;
    line-height: 1.45;
}}

/* 녹색 사각 '길안내' 버튼 */
div.stButton > button {{
    background-color: #2E6930 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 4px !important;
    font-weight: 700 !important;
    font-size: 0.98rem !important;
    padding: 0.5rem 1.2rem !important;
    width: 100% !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08) !important;
}}
div.stButton > button:hover {{
    background-color: #235225 !important;
    color: #FFFFFF !important;
}}

/* 목적지 안내 배너 */
.dest-banner {{
    background-color: #EBF7EE;
    border: 2px solid #28A745;
    border-radius: 12px;
    padding: 14px 18px;
    margin: 10px 0 16px 0;
    color: #155724;
}}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. 관 · 층 · 검사실 좌표 데이터
# ---------------------------------------------------------
MAP_ROOMS = {
    # 서관 1층
    "1F_WEST_BLOOD": {
        "name": "서관 1층 채혈실", "short_name": "서관 채혈실",
        "floor": "1층", "floor_code": "1F", "building": "서관",
        "hours": "평일 06:10~18:30, 토 06:30~13:30",
        "boxes": [(0.241, 0.520, 0.317, 0.654)]
    },
    "1F_WEST_CTMR": {
        "name": "서관 1층 외래/응급 CT·MR실", "short_name": "외래/응급 CT·MR실",
        "floor": "1층", "floor_code": "1F", "building": "서관",
        "hours": "상시 운영 (외래·응급 예약)",
        "boxes": [(0.068, 0.514, 0.106, 0.654)]
    },
    # 서관 2층
    "2F_WEST_CT": {
        "name": "서관 2층 CT실", "short_name": "CT실 / 투시조영실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.223, 0.106, 0.307, 0.292), (0.223, 0.319, 0.259, 0.585), (0.267, 0.398, 0.307, 0.585)]
    },
    "2F_WEST_DIAG": {
        "name": "서관 2층 CT/MR 채혈실 (진단검사의학과)", "short_name": "진단검사의학과 (CT/MR 채혈실)",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "야간/휴일 전용 (18:30~익일 06:10)",
        "boxes": [(0.008, 0.228, 0.096, 0.692)]
    },
    "2F_WEST_PREADM": {
        "name": "서관 2층 입원전검사실", "short_name": "입원전검사실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:30~17:00 (토요일 미운영)",
        "boxes": [(0.160, 0.718, 0.193, 0.909), (0.193, 0.718, 0.215, 0.822)]
    },
    "2F_WEST_US": {
        "name": "서관 2층 초음파실", "short_name": "초음파실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:00~17:30",
        "boxes": [(0.240, 0.718, 0.313, 0.873), (0.222, 0.768, 0.240, 0.873)]
    },
    # 동관 1층
    "1F_EAST_XRAY": {
        "name": "동관 1층 영상의학과 외래촬영실", "short_name": "영상의학과 외래촬영실",
        "floor": "1층", "floor_code": "1F", "building": "동관",
        "hours": "평일 08:00~17:30",
        "boxes": [(0.516, 0.313, 0.554, 0.538), (0.505, 0.485, 0.534, 0.538)]
    },
    # 동관 2층
    "2F_EAST_XRAY": {
        "name": "동관 2층 일반촬영실", "short_name": "일반촬영실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.344, 0.275, 0.425, 0.355), (0.344, 0.355, 0.416, 0.556), (0.397, 0.556, 0.415, 0.638)]
    },
    "2F_EAST_MR": {
        "name": "동관 2층 MR실", "short_name": "MR실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 07:30~20:00",
        "boxes": [(0.344, 0.007, 0.443, 0.249)]
    },
    "2F_EAST_HEART": {
        "name": "동관 2층 심장검사실", "short_name": "심장검사실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.609, 0.735, 0.669, 0.990)]
    },
    # 신관 1층
    "1F_NEW_BLOOD": {
        "name": "신관 1층 채혈실", "short_name": "신관 채혈실",
        "floor": "1층", "floor_code": "1F", "building": "신관",
        "hours": "평일 06:10~17:30 (주말·공휴일 미운영)",
        "boxes": [(0.749, 0.550, 0.800, 0.635)]
    },
    "1F_NEW_PED_XRAY": {
        "name": "신관 1층 소아영상의학과", "short_name": "소아영상의학과",
        "floor": "1층", "floor_code": "1F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.907, 0.415, 0.998, 0.812)]
    },
    # 신관 2층
    "2F_NEW_MR": {
        "name": "신관 2층 MR실", "short_name": "MR실",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.696, 0.252, 0.829, 0.449)]
    },
    "2F_NEW_XRAY_US": {
        "name": "신관 2층 일반촬영실·초음파실", "short_name": "일반촬영실·초음파실",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:00~17:30",
        "boxes": [(0.696, 0.449, 0.829, 0.605), (0.707, 0.605, 0.820, 0.682)]
    }
}

ELEVATORS = {
    "서관": {"name": "서관 엘리베이터", "2F_box": (0.100, 0.355, 0.120, 0.550), "1F_box": (0.148, 0.608, 0.195, 0.652)},
    "동관": {"name": "동관 엘리베이터", "2F_box": (0.475, 0.640, 0.538, 0.692), "1F_box": (0.488, 0.588, 0.545, 0.638)},
    "신관": {"name": "신관 엘리베이터", "2F_box": (0.860, 0.618, 0.885, 0.672), "1F_box": (0.825, 0.573, 0.886, 0.622)}
}

PATIENT_EXAMS = [
    {
        "title": "[검사] 가정의학과 검체검사",
        "sub": "서관 1층 서관 채혈실(평;06:10~18:30, 토;06:30~13:30)",
        "default_key": "1F_WEST_BLOOD",
        "cat": "BLOOD"
    },
    {
        "title": "[검사] 일반촬영 (흉부 X-ray)",
        "sub": "동관 2층 일반촬영실(평;08:00~18:00)",
        "default_key": "2F_EAST_XRAY",
        "cat": "XRAY"
    },
    {
        "title": "[검사] 복부 조영 CT",
        "sub": "서관 2층 CT실(평;08:00~18:00)",
        "default_key": "2F_WEST_CT",
        "cat": "CT"
    },
    {
        "title": "[검사] 뇌 신경 MRI",
        "sub": "신관 2층 MR실(평;08:00~18:00)",
        "default_key": "2F_NEW_MR",
        "cat": "MR"
    }
]

# ---------------------------------------------------------
# 4. 시간·상황 규칙 엔진
# ---------------------------------------------------------
def resolve_dest_key(exam, start_key, day_type, time_str):
    cat = exam["cat"]
    t_val = int(time_str.replace(":", ""))
    start_bldg = MAP_ROOMS[start_key]["building"]

    if cat == "BLOOD":
        if day_type == "평일(월~금)":
            if 610 <= t_val <= 1730:
                return "1F_NEW_BLOOD" if start_bldg == "신관" else "1F_WEST_BLOOD"
            elif 1730 < t_val <= 1830:
                return "1F_WEST_BLOOD"
            else:
                return "2F_WEST_DIAG"
        elif day_type == "토요일":
            return "1F_WEST_BLOOD" if 630 <= t_val <= 1730 else "2F_WEST_DIAG"
        else:
            return "1F_WEST_BLOOD" if 630 <= t_val <= 1730 else "2F_WEST_DIAG"
    return exam["default_key"]

# ---------------------------------------------------------
# 5. 이미지 탐색 및 도면 가공
# ---------------------------------------------------------
def find_image(floor_code):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs = [
        r"C:\Users\user\Downloads\대리 진급",
        base_dir,
        os.getcwd()
    ]
    kor_floor = floor_code.replace("F", "층")
    target_names = [
        f"서동신_{floor_code}_지도.png",
        f"서동신_{kor_floor}_지도.png",
        f"서동신 {kor_floor} 지도.png",
        f"서동신_{floor_code}_지도_2.png",
        f"서동신_{kor_floor}_지도_2.png"
    ]
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for name in target_names:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
        try:
            for f in os.listdir(d):
                f_lower = f.lower()
                if f_lower.endswith((".png", ".jpg", ".jpeg")):
                    if (floor_code.lower() in f_lower) or (kor_floor in f):
                        return os.path.join(d, f)
        except Exception:
            pass
    return None

@st.cache_data
def clean_base_map(img_path, floor_code):
    img = Image.open(img_path).convert("RGB")
    arr = np.array(img)
    H, W, _ = arr.shape
    if floor_code == "2F":
        teals = [(0.340, 0.270, 0.430, 0.642), (0.692, 0.248, 0.833, 0.452), (0.220, 0.872, 0.316, 0.916)]
    else:
        teals = [(0.015, 0.215, 0.108, 0.505), (0.335, 0.555, 0.391, 0.660), (0.905, 0.412, 0.999, 0.816)]

    for (x1p, y1p, x2p, y2p) in teals:
        x1, y1, x2, y2 = int(x1p*W), int(y1p*H), int(x2p*W), int(y2p*H)
        sub = arr[y1:y2, x1:x2].astype(np.int16)
        r, g, b = sub[:,:,0], sub[:,:,1], sub[:,:,2]
        is_teal = (g > r + 20) & (b > r + 20) & (r < 95)
        is_white_txt = (r > 175) & (g > 190) & (b > 190)
        sub[is_white_txt] = [30, 30, 30]
        sub[is_teal] = [255, 255, 255]
        arr[y1:y2, x1:x2] = sub.astype(np.uint8)
    return arr

def draw_colored_map(base_arr, red_key=None, green_key=None, elev_box=None, mode="SAME"):
    arr = base_arr.copy()
    H, W, _ = arr.shape

    def fill_box(key, rgb):
        if not key or key not in MAP_ROOMS:
            return None
        boxes = MAP_ROOMS[key]["boxes"]
        centers = []
        for (x1p, y1p, x2p, y2p) in boxes:
            x1, y1, x2, y2 = int(x1p*W), int(y1p*H), int(x2p*W), int(y2p*H)
            centers.append(((x1+x2)//2, (y1+y2)//2))
            sub = arr[y1:y2, x1:x2]
            is_bg = (sub[:,:,0] > 242) & (sub[:,:,1] > 244) & (sub[:,:,2] > 244)
            sub[is_bg] = rgb
            arr[y1:y2, x1:x2] = sub
        return (int(np.mean([c[0] for c in centers])), int(np.mean([c[1] for c in centers]))), boxes

    red_res = fill_box(red_key, [255, 200, 200])     # 내 위치: 연한 빨간색
    green_res = fill_box(green_key, [188, 245, 200]) # 목적지: 연한 녹색

    pil_img = Image.fromarray(arr)
    draw = ImageDraw.Draw(pil_img)
    bw = max(3, int(W * 0.0025))

    if red_res:
        for b in red_res[1]:
            draw.rectangle([int(b[0]*W), int(b[1]*H), int(b[2]*W), int(b[3]*H)], outline=(217, 48, 37), width=bw)
    if green_res:
        for b in green_res[1]:
            draw.rectangle([int(b[0]*W), int(b[1]*H), int(b[2]*W), int(b[3]*H)], outline=(30, 142, 62), width=bw)

    elev_center = None
    if elev_box is not None:
        ex1, ey1, ex2, ey2 = int(elev_box[0]*W), int(elev_box[1]*H), int(elev_box[2]*W), int(elev_box[3]*H)
        elev_center = ((ex1+ex2)//2, (ey1+ey2)//2)
        pad = max(5, int(W * 0.004))
        draw.rectangle([ex1-pad, ey1-pad, ex2+pad, ey2+pad], outline=(255, 140, 0), width=bw+2)

    lw = max(4, int(W * 0.003))
    r_rad = max(9, int(W * 0.0075))
    corridor_y = int(H * 0.65)

    if mode == "SAME" and red_res and green_res and red_key != green_key:
        sx, sy = red_res[0]
        dx, dy = green_res[0]
        draw.line([(sx, sy), (sx, corridor_y), (dx, corridor_y), (dx, dy)], fill=(0, 102, 102), width=lw)
        draw.ellipse([sx-r_rad, sy-r_rad, sx+r_rad, sy+r_rad], fill=(217, 48, 37), outline=(255, 255, 255), width=2)
        draw.ellipse([dx-r_rad, dy-r_rad, dx+r_rad, dy+r_rad], fill=(30, 142, 62), outline=(255, 255, 255), width=2)
    elif mode == "TO_ELEV" and red_res and elev_center:
        sx, sy = red_res[0]
        ex, ey = elev_center
        draw.line([(sx, sy), (sx, ey), (ex, ey)], fill=(217, 48, 37), width=lw)
        draw.ellipse([sx-r_rad, sy-r_rad, sx+r_rad, sy+r_rad], fill=(217, 48, 37), outline=(255, 255, 255), width=2)
        draw.ellipse([ex-r_rad, ey-r_rad, ex+r_rad, ey+r_rad], fill=(255, 140, 0), outline=(255, 255, 255), width=2)
    elif mode == "FROM_ELEV" and elev_center and green_res:
        ex, ey = elev_center
        dx, dy = green_res[0]
        draw.line([(ex, ey), (dx, ey), (dx, dy)], fill=(30, 142, 62), width=lw)
        draw.ellipse([ex-r_rad, ey-r_rad, ex+r_rad, ey+r_rad], fill=(255, 140, 0), outline=(255, 255, 255), width=2)
        draw.ellipse([dx-r_rad, dy-r_rad, dx+r_rad, dy+r_rad], fill=(30, 142, 62), outline=(255, 255, 255), width=2)

    return pil_img

# ---------------------------------------------------------
# 6. [핵심] 양손가락 핀치 줌 & 드래그 인터랙티브 뷰어 컴포넌트
# ---------------------------------------------------------
def render_pinch_zoom_viewer(pil_img, step_title, viewer_height=490):
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    b64_img = base64.b64encode(buf.getvalue()).decode()
    elem_id = f"viewer_{abs(hash(step_title)) % 100000}"

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: -apple-system, BlinkMacSystemFont, "Malgun Gothic", sans-serif;
            overflow: hidden;
            touch-action: none;
        }}
        .badge-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}
        .step-badge {{
            background-color: #005C5C;
            color: white;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 0.88rem;
            font-weight: 700;
        }}
        .tip-badge {{
            font-size: 0.78rem;
            color: #555555;
            background: #EEEEEE;
            padding: 3px 8px;
            border-radius: 6px;
            font-weight: 600;
        }}
        .viewer-box {{
            position: relative;
            width: 100%;
            height: {viewer_height}px;
            background: #FFFFFF;
            border: 2px solid #005C5C;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 10px rgba(0,0,0,0.06);
            display: flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
        }}
        .map-layer {{
            position: absolute;
            transform-origin: 0 0;
            cursor: grab;
            user-select: none;
            will-change: transform;
        }}
        .map-layer:active {{
            cursor: grabbing;
        }}
        .map-layer img {{
            display: block;
            max-width: none;
            height: {viewer_height - 30}px;
            pointer-events: none;
        }}
        .floating-ctrls {{
            position: absolute;
            right: 14px;
            bottom: 14px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            z-index: 10;
        }}
        .btn-ctrl {{
            width: 40px;
            height: 40px;
            background: #005C5C;
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            font-size: 1.25rem;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.25);
            cursor: pointer;
            touch-action: manipulation;
        }}
        .btn-ctrl:active {{
            background: #003A3A;
            transform: scale(0.95);
        }}
    </style>
    </head>
    <body>
    <div class="badge-bar">
        <span class="step-badge">{step_title}</span>
        <span class="tip-badge">🖐️ 두 손가락 핀치 줌 / 드래그 이동</span>
    </div>
    <div class="viewer-box" id="{elem_id}_box">
        <div class="map-layer" id="{elem_id}_layer">
            <img id="{elem_id}_img" src="data:image/png;base64,{b64_img}" />
        </div>
        <div class="floating-ctrls">
            <button class="btn-ctrl" onclick="{elem_id}_zoomIn()">＋</button>
            <button class="btn-ctrl" onclick="{elem_id}_zoomOut()">－</button>
            <button class="btn-ctrl" onclick="{elem_id}_reset()" style="font-size:1.0rem;">⟲</button>
        </div>
    </div>

    <script>
        const cBox = document.getElementById('{elem_id}_box');
        const cLayer = document.getElementById('{elem_id}_layer');
        const cImg = document.getElementById('{elem_id}_img');

        let scale = 1;
        let posX = 0;
        let posY = 0;
        let isDrag = false;
        let startX = 0, startY = 0;
        let initDist = 0, initScale = 1;

        function updateStyle() {{
            cLayer.style.transform = `translate(${{posX}}px, ${{posY}}px) scale(${{scale}})`;
        }}

        function initFit() {{
            const cw = cBox.clientWidth;
            const ch = cBox.clientHeight;
            const iw = cImg.naturalWidth || cImg.width || 1200;
            const ih = cImg.naturalHeight || cImg.height || 550;
            scale = Math.min((cw - 16) / iw, (ch - 16) / ih);
            if (!scale || scale <= 0) scale = 0.55;
            posX = (cw - (iw * scale)) / 2;
            posY = (ch - (ih * scale)) / 2;
            updateStyle();
        }}

        cImg.onload = initFit;
        setTimeout(initFit, 120);

        // PC 마우스 드래그 & 휠 줌
        cBox.addEventListener('mousedown', (e) => {{
            if (e.target.tagName === 'BUTTON') return;
            isDrag = true;
            startX = e.clientX - posX;
            startY = e.clientY - posY;
        }});
        window.addEventListener('mousemove', (e) => {{
            if (!isDrag) return;
            posX = e.clientX - startX;
            posY = e.clientY - startY;
            updateStyle();
        }});
        window.addEventListener('mouseup', () => {{ isDrag = false; }});

        cBox.addEventListener('wheel', (e) => {{
            e.preventDefault();
            const factor = 1.15;
            const rect = cBox.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            let nextScale = e.deltaY < 0 ? scale * factor : scale / factor;
            nextScale = Math.min(Math.max(0.2, nextScale), 5.0);
            posX = mx - (mx - posX) * (nextScale / scale);
            posY = my - (my - posY) * (nextScale / scale);
            scale = nextScale;
            updateStyle();
        }}, {{ passive: false }});

        // 스마트폰 터치: 두 손가락 핀치 투 줌 & 한 손가락 패닝
        cBox.addEventListener('touchstart', (e) => {{
            if (e.target.tagName === 'BUTTON') return;
            if (e.touches.length === 1) {{
                isDrag = true;
                startX = e.touches[0].clientX - posX;
                startY = e.touches[0].clientY - posY;
            }} else if (e.touches.length === 2) {{
                isDrag = false;
                initDist = Math.hypot(
                    e.touches[0].clientX - e.touches[1].clientX,
                    e.touches[0].clientY - e.touches[1].clientY
                );
                initScale = scale;
            }}
        }}, {{ passive: false }});

        cBox.addEventListener('touchmove', (e) => {{
            if (e.target.tagName === 'BUTTON') return;
            e.preventDefault();
            if (e.touches.length === 1 && isDrag) {{
                posX = e.touches[0].clientX - startX;
                posY = e.touches[0].clientY - startY;
                updateStyle();
            }} else if (e.touches.length === 2 && initDist > 0) {{
                const curDist = Math.hypot(
                    e.touches[0].clientX - e.touches[1].clientX,
                    e.touches[0].clientY - e.touches[1].clientY
                );
                let nextScale = initScale * (curDist / initDist);
                nextScale = Math.min(Math.max(0.2, nextScale), 5.0);

                const rect = cBox.getBoundingClientRect();
                const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2 - rect.left;
                const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2 - rect.top;

                posX = midX - (midX - posX) * (nextScale / scale);
                posY = midY - (midY - posY) * (nextScale / scale);
                scale = nextScale;
                updateStyle();
            }}
        }}, {{ passive: false }});

        cBox.addEventListener('touchend', (e) => {{
            if (e.touches.length < 2) initDist = 0;
            if (e.touches.length === 0) isDrag = false;
        }});

        function {elem_id}_zoomIn() {{
            const nextScale = Math.min(scale * 1.3, 5.0);
            const cx = cBox.clientWidth / 2, cy = cBox.clientHeight / 2;
            posX = cx - (cx - posX) * (nextScale / scale);
            posY = cy - (cy - posY) * (nextScale / scale);
            scale = nextScale;
            updateStyle();
        }}
        function {elem_id}_zoomOut() {{
            const nextScale = Math.max(scale / 1.3, 0.2);
            const cx = cBox.clientWidth / 2, cy = cBox.clientHeight / 2;
            posX = cx - (cx - posX) * (nextScale / scale);
            posY = cy - (cy - posY) * (nextScale / scale);
            scale = nextScale;
            updateStyle();
        }}
        function {elem_id}_reset() {{
            initFit();
        }}
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=viewer_height + 40, scrolling=False)

# =========================================================
# PAGE 1: 나의 검사 일정 & 내 위치 선택 화면 (모바일 뷰)
# =========================================================
if st.session_state.page == "home":
    st.markdown("""
    <div class="app-header">
        <h3>🏥 서울아산병원 검사실 길 안내</h3>
        <p>받으실 검사의 [길안내] 버튼을 누르면 넓은 지도로 이동합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 📅 나의 검사 일정")
    st.caption("안내를 원하시는 검사 우측의 **[길안내]**를 눌러주세요.")

    # 검사 일정 카드 및 개별 '길안내' 버튼
    for idx, ex in enumerate(PATIENT_EXAMS):
        with st.container():
            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; padding:12px; margin-bottom:6px;">
                <div class="exam-row-wrap">
                    <div class="exam-pill">검사</div>
                    <div class="exam-info-col">
                        <div class="exam-title-txt">{ex['title']}</div>
                        <div class="exam-sub-txt">{ex['sub']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🧭 길안내", key=f"btn_go_map_{idx}", use_container_width=True):
                st.session_state.selected_exam_idx = idx
                st.session_state.page = "map"
                st.rerun()

    st.markdown("---")

    # 3칸 분할 현재 내 위치 선택란 (1. 관 선택 / 2. 층 선택 / 3. 위치 선택)
    st.markdown("#### 📍 현재 내 위치 선택")
    loc_col1, loc_col2, loc_col3 = st.columns([1.0, 0.9, 1.5])

    with loc_col1:
        bldg_list = ["서관", "동관", "신관"]
        if st.session_state.sel_bldg not in bldg_list:
            st.session_state.sel_bldg = "동관"
        st.session_state.sel_bldg = st.selectbox(
            "관 선택",
            options=bldg_list,
            index=bldg_list.index(st.session_state.sel_bldg)
        )

    with loc_col2:
        floor_list = ["1층", "2층"]
        if st.session_state.sel_floor not in floor_list:
            st.session_state.sel_floor = "2층"
        st.session_state.sel_floor = st.selectbox(
            "층 선택",
            options=floor_list,
            index=floor_list.index(st.session_state.sel_floor)
        )

    # 선택된 [관] + [층]의 검사실만 자동 필터링
    filtered_keys = [
        k for k, v in MAP_ROOMS.items()
        if v["building"] == st.session_state.sel_bldg and v["floor"] == st.session_state.sel_floor
    ]

    with loc_col3:
        default_idx = 0
        if st.session_state.start_key in filtered_keys:
            default_idx = filtered_keys.index(st.session_state.start_key)
        st.session_state.start_key = st.selectbox(
            "위치 선택",
            options=filtered_keys,
            format_func=lambda k: MAP_ROOMS[k]["short_name"],
            index=default_idx
        )

    # 시간 테스트 옵션
    with st.expander("⚙️ 현재 요일 및 시간 설정 (테스트용)"):
        t_c1, t_c2 = st.columns(2)
        st.session_state.day_type = t_c1.selectbox("요일", ["평일(월~금)", "토요일", "일요일/공휴일"], index=0)
        st.session_state.time_str = t_c2.select_slider("시각", ["09:00", "14:20", "17:45", "19:10"], value=st.session_state.time_str)

# =========================================================
# PAGE 2: 지도 전용 화면 (핀치 줌 & 드래그 와이드 뷰)
# =========================================================
elif st.session_state.page == "map":
    # 1. 최상단 뒤로가기 버튼
    b_col1, b_col2 = st.columns([1.2, 2.8])
    with b_col1:
        if st.button("⬅️ 검사 목록 및 위치 변경으로 돌아가기", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

    target_exam = PATIENT_EXAMS[st.session_state.selected_exam_idx]
    start_key = st.session_state.start_key
    dest_key = resolve_dest_key(target_exam, start_key, st.session_state.day_type, st.session_state.time_str)

    s_meta = MAP_ROOMS[start_key]
    d_meta = MAP_ROOMS[dest_key]
    is_diff_floor = (s_meta["floor_code"] != d_meta["floor_code"])
    elev_info = ELEVATORS[s_meta["building"]]

    # 2. 목적지 요약 배너
    st.markdown(f"""
    <div class="dest-banner">
        <div style="font-size:0.86rem; font-weight:700;">🟢 실시간 맞춤 길안내 목적지</div>
        <div style="font-size:1.3rem; font-weight:800; margin:3px 0;">{d_meta['name']} ({d_meta['building']} {d_meta['floor']})</div>
        <div style="font-size:0.9rem; color:#333; margin-top:4px;">
            • <b>내 출발 위치</b>: [{s_meta['building']} {s_meta['floor']}] {s_meta['name']}<br>
            • <b>운영시간</b>: {d_meta['hours']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    leg_c1, leg_c2, leg_c3 = st.columns(3)
    leg_c1.markdown("🔴 **연한 빨간색**: 내 출발 위치")
    leg_c2.markdown("🟢 **연한 녹색**: 가야 할 목적지")
    leg_c3.markdown("🟠 **주황색 사각 박스**: 탑승/하차 엘리베이터")

    # 3. 도면 렌더링 (핀치 줌 인터랙티브 뷰어 적용)
    path_2f = find_image("2F")
    path_1f = find_image("1F")

    if not path_2f or not path_1f:
        st.warning("⚠️ `서동신_1층_지도.png` 및 `서동신_2층_지도.png` 파일이 지정된 폴더에 있는지 확인해 주세요.")
    else:
        arr_2f = clean_base_map(path_2f, "2F")
        arr_1f = clean_base_map(path_1f, "1F")

        if is_diff_floor:
            # [1단계 지도] 출발 층 -> 엘리베이터 (핀치 줌 적용)
            base_start = arr_2f if s_meta["floor_code"] == "2F" else arr_1f
            elev_start_box = elev_info[f"{s_meta['floor_code']}_box"]
            img_s1 = draw_colored_map(base_start, red_key=start_key, elev_box=elev_start_box, mode="TO_ELEV")
            render_pinch_zoom_viewer(img_s1, f"1단계 : {s_meta['floor']} [{elev_info['name']}]로 이동")

            # [2단계 지도] 도착 층 엘리베이터 -> 목적지 검사실 (핀치 줌 적용)
            base_dest = arr_2f if d_meta["floor_code"] == "2F" else arr_1f
            elev_dest_box = elev_info[f"{d_meta['floor_code']}_box"]
            img_s2 = draw_colored_map(base_dest, green_key=dest_key, elev_box=elev_dest_box, mode="FROM_ELEV")
            render_pinch_zoom_viewer(img_s2, f"2단계 : {d_meta['floor']} 하차 ➔ [{d_meta['short_name']}](연한 녹색) 도착")
        else:
            # 동일 층 지도 1장 (핀치 줌 적용)
            base_same = arr_2f if s_meta["floor_code"] == "2F" else arr_1f
            img_same = draw_colored_map(base_same, red_key=start_key, green_key=dest_key, mode="SAME")
            render_pinch_zoom_viewer(img_same, f"{s_meta['floor']} 동선 지도 : [{s_meta['short_name']}](빨강) ➔ [{d_meta['short_name']}](녹색)")

    # 하단 질문 챗봇
    st.markdown("---")
    with st.expander("💬 길 안내 AI에게 질문하기"):
        q = st.text_input("질문을 입력하세요:", placeholder="예: 지금 채혈실 어떻게 가나요?")
        if q:
            st.success(f"현재 위치({s_meta['name']})에서 {d_meta['name']}(으)로 이동하시면 됩니다. 지도에 표시된 동선을 따라가 주세요!")
