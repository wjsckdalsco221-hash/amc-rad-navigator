import os
import streamlit as st
import numpy as np
from PIL import Image, ImageDraw

# ---------------------------------------------------------
# 1. 모바일 앱 전용 레이아웃 및 폰트 최적화 CSS
#    (PC 웹에서도 스마트폰 화면 비율로 중앙 정렬)
# ---------------------------------------------------------
st.set_page_config(
    page_title="AMC 맞춤형 검사실 길 안내",
    page_icon="📱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
/* 스마트폰 화면 비율(최대 480px) 중앙 정렬 */
.block-container {
    max-width: 480px !important;
    padding-top: 1rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
    margin: 0 auto !important;
}

/* 상단 모바일 앱 헤더 */
.app-header {
    background: linear-gradient(135deg, #005C5C 0%, #003A3A 100%);
    color: white;
    padding: 14px 16px;
    border-radius: 12px;
    margin-bottom: 12px;
    box-shadow: 0 3px 8px rgba(0,0,0,0.12);
}
.app-header h3 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 700;
    color: #FFFFFF;
}
.app-header p {
    margin: 3px 0 0 0;
    font-size: 0.82rem;
    color: #D2EBEB;
}

/* 목적지 직관적 안내 배너 */
.dest-banner {
    background-color: #EBF7EE;
    border: 2px solid #28A745;
    border-radius: 10px;
    padding: 12px;
    margin: 10px 0;
    color: #155724;
}

/* 1단계 / 2단계 지도 타이틀 뱃지 */
.map-step-badge {
    background-color: #005C5C;
    color: white;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 700;
    margin-top: 12px;
    margin-bottom: 6px;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 1층 및 2층 검사실 좌표 사전 (실제 도면 비율 0.0 ~ 1.0)
# ---------------------------------------------------------
MAP_ROOMS = {
    # 2층 검사실
    "2F_EAST_XRAY": {
        "name": "동관 2층 일반촬영실", "floor": "2F", "building": "동관",
        "hours": "월~금 08:00~18:00 상시 운영",
        "boxes": [(0.344, 0.275, 0.425, 0.355), (0.344, 0.355, 0.416, 0.556), (0.397, 0.556, 0.415, 0.638)]
    },
    "2F_WEST_CT": {
        "name": "서관 2층 CT실", "floor": "2F", "building": "서관",
        "hours": "월~금 08:00~18:00",
        "boxes": [(0.223, 0.106, 0.307, 0.292), (0.223, 0.319, 0.259, 0.585), (0.267, 0.398, 0.307, 0.585)]
    },
    "2F_WEST_DIAG": {
        "name": "서관 2층 CT/MR 채혈실 (진단검사의학과)", "floor": "2F", "building": "서관",
        "hours": "야간/휴일 전용 (18:30~익일 06:10)",
        "boxes": [(0.008, 0.228, 0.096, 0.692)]
    },
    "2F_WEST_PREADM": {
        "name": "서관 2층 입원전검사실", "floor": "2F", "building": "서관",
        "hours": "월~금 08:30~17:00 (토요일 미운영)",
        "boxes": [(0.160, 0.718, 0.193, 0.909), (0.193, 0.718, 0.215, 0.822)]
    },
    "2F_WEST_US": {
        "name": "서관 2층 초음파실", "floor": "2F", "building": "서관",
        "hours": "월~금 08:00~17:30",
        "boxes": [(0.240, 0.718, 0.313, 0.873), (0.222, 0.768, 0.240, 0.873)]
    },
    "2F_NEW_MR": {
        "name": "신관 2층 MR실", "floor": "2F", "building": "신관",
        "hours": "월~금 08:00~18:00",
        "boxes": [(0.696, 0.252, 0.829, 0.449)]
    },

    # 1층 검사실
    "1F_WEST_BLOOD": {
        "name": "서관 1층 채혈실", "floor": "1F", "building": "서관",
        "hours": "월~금 06:10~18:30 / 토 06:30~13:30",
        "boxes": [(0.241, 0.520, 0.317, 0.654)]
    },
    "1F_NEW_BLOOD": {
        "name": "신관 1층 채혈실", "floor": "1F", "building": "신관",
        "hours": "월~금 06:10~17:30 (휴일 미운영)",
        "boxes": [(0.749, 0.550, 0.800, 0.635)]
    },
    "1F_EAST_XRAY": {
        "name": "동관 1층 외래촬영실", "floor": "1F", "building": "동관",
        "hours": "월~금 08:00~17:30",
        "boxes": [(0.516, 0.313, 0.554, 0.538), (0.505, 0.485, 0.534, 0.538)]
    }
}

ELEVATORS = {
    "서관": {"name": "서관 엘리베이터", "2F_box": (0.100, 0.355, 0.120, 0.550), "1F_box": (0.148, 0.608, 0.195, 0.652)},
    "동관": {"name": "동관 엘리베이터", "2F_box": (0.475, 0.640, 0.538, 0.692), "1F_box": (0.488, 0.588, 0.545, 0.638)},
    "신관": {"name": "신관 엘리베이터", "2F_box": (0.860, 0.618, 0.885, 0.672), "1F_box": (0.825, 0.573, 0.886, 0.622)}
}

PATIENT_EXAMS = [
    {"name": "일반촬영 (흉부 X-ray)", "status": "완료", "default_key": "2F_EAST_XRAY", "cat": "XRAY"},
    {"name": "[검사] 외래 채혈실 (검체검사)", "status": "대기", "default_key": "1F_WEST_BLOOD", "cat": "BLOOD"},
    {"name": "복부 조영 CT", "status": "대기", "default_key": "2F_WEST_CT", "cat": "CT"},
    {"name": "뇌 신경 MRI", "status": "대기", "default_key": "2F_NEW_MR", "cat": "MR"}
]

# ---------------------------------------------------------
# 3. 시간·상황 매칭 규칙 엔진
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
# 4. 이미지 탐색 및 이미지 전처리 함수 (NameError 해결 핵심)
# ---------------------------------------------------------
def find_image(floor_str):
    """지정된 폴더 및 실행 경로에서 1층 / 2층 지도 파일을 안전하게 탐색"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs = [
        r"C:\Users\user\Downloads\대리 진급",
        base_dir,
        os.getcwd()
    ]
    kor_floor = floor_str.replace("F", "층")
    target_names = [
        f"서동신_{floor_str}_지도.png",
        f"서동신_{kor_floor}_지도.png",
        f"서동신 {kor_floor} 지도.png",
        f"서동신_{floor_str}_지도_2.png",
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
                    if (floor_str.lower() in f_lower) or (kor_floor in f):
                        return os.path.join(d, f)
        except Exception:
            pass
            
    return None

@st.cache_data
def clean_base_map(img_path, floor_str):
    """도면 이미지의 청록색 강조 영역을 일반 흰색 배경으로 초기화"""
    img = Image.open(img_path).convert("RGB")
    arr = np.array(img)
    H, W, _ = arr.shape
    if floor_str == "2F":
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
    """도면 위에 내 위치(연빨강), 목적지(연녹색), 엘리베이터(주황)를 매핑"""
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

    red_res = fill_box(red_key, [255, 200, 200])    # 내 위치: 연한 빨간색
    green_res = fill_box(green_key, [188, 245, 200]) # 가야할 곳: 연한 녹색

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
# 5. 세션 상태 관리
# ---------------------------------------------------------
if "start_key" not in st.session_state:
    st.session_state.start_key = "2F_EAST_XRAY"  # 기본 위치: 동관 2층 일반촬영실
if "selected_exam_idx" not in st.session_state:
    st.session_state.selected_exam_idx = 1       # 기본 목적지: 채혈실
if "day_type" not in st.session_state:
    st.session_state.day_type = "평일(월~금)"
if "time_str" not in st.session_state:
    st.session_state.time_str = "14:20"

# ---------------------------------------------------------
# 6. 스마트폰 전용 화면 렌더링
# ---------------------------------------------------------
st.markdown("""
<div class="app-header">
    <h3>🏥 서울아산병원 검사실 길 안내</h3>
    <p>내 위치(빨간색) ➔ 다음 검사실(녹색) 실시간 지도 안내</p>
</div>
""", unsafe_allow_html=True)

btn_col1, btn_col2 = st.columns([1, 1.2])
with btn_col1:
    st.button("🧭 위치 안내", type="primary", use_container_width=True)
with btn_col2:
    st.caption("👈 선택 후 버튼을 누르면 지도가 갱신됩니다.")

st.markdown("---")

# 1) 나의 검사 일정 목록
st.markdown("#### 📅 나의 검사 일정")

exam_options = []
for i, ex in enumerate(PATIENT_EXAMS):
    st_text = "✅ 완료" if ex["status"] == "완료" else "⏳ 대기"
    r_info = MAP_ROOMS[ex["default_key"]]
    exam_options.append(f"{ex['name']} [{r_info['building']} {r_info['floor']}] ({st_text})")

st.session_state.selected_exam_idx = st.radio(
    "안내받을 검사를 터치하세요:",
    options=range(len(PATIENT_EXAMS)),
    format_func=lambda i: exam_options[i],
    index=st.session_state.selected_exam_idx,
    label_visibility="collapsed"
)

# 2) 현재 내 위치 선택란
st.markdown("#### 📍 현재 내 위치 선택")
st.session_state.start_key = st.selectbox(
    "현재 계신 검사실/구역을 선택하세요:",
    options=list(MAP_ROOMS.keys()),
    format_func=lambda k: f"🔴 [{MAP_ROOMS[k]['building']} {MAP_ROOMS[k]['floor']}] {MAP_ROOMS[k]['name']}",
    index=list(MAP_ROOMS.keys()).index(st.session_state.start_key),
    label_visibility="collapsed"
)

# 간이 시간 설정
with st.expander("⚙️ 현재 요일 및 시간 변경 (테스트용)"):
    t_c1, t_c2 = st.columns(2)
    st.session_state.day_type = t_c1.selectbox("요일", ["평일(월~금)", "토요일", "일요일/공휴일"], index=0)
    st.session_state.time_str = t_c2.select_slider("시각", ["09:00", "14:20", "17:45", "19:10"], value=st.session_state.time_str)

st.markdown("---")

# ---------------------------------------------------------
# 7. 맞춤형 도면 안내 출력
# ---------------------------------------------------------
target_exam = PATIENT_EXAMS[st.session_state.selected_exam_idx]
start_key = st.session_state.start_key
dest_key = resolve_dest_key(target_exam, start_key, st.session_state.day_type, st.session_state.time_str)

s_meta = MAP_ROOMS[start_key]
d_meta = MAP_ROOMS[dest_key]
is_diff_floor = (s_meta["floor"] != d_meta["floor"])
elev_info = ELEVATORS[s_meta["building"]]

# 상단 직관적 목적지 안내 배너
st.markdown(f"""
<div class="dest-banner">
    <div style="font-size:0.8rem; font-weight:700;">🟢 지금 가실 곳 (도착 목표)</div>
    <div style="font-size:1.15rem; font-weight:800; margin:2px 0;">{d_meta['name']} ({d_meta['building']} {d_meta['floor']})</div>
    <div style="font-size:0.82rem; color:#444;">• 운영시간: {d_meta['hours']}</div>
</div>
""", unsafe_allow_html=True)

leg_c1, leg_c2 = st.columns(2)
leg_c1.markdown("<span style='color:#D93025; font-weight:700;'>■ 연한 빨간색</span>: 내 위치", unsafe_allow_html=True)
leg_c2.markdown("<span style='color:#1E8E3E; font-weight:700;'>■ 연한 녹색</span>: 목적지", unsafe_allow_html=True)

# 도면 파일 탐색 및 렌더링
path_2f = find_image("2F")
path_1f = find_image("1F")

if not path_2f or not path_1f:
    st.warning("⚠️ `서동신_1층_지도.png` 및 `서동신_2층_지도.png` 파일이 지정된 폴더에 있는지 확인해 주세요.")
else:
    arr_2f = clean_base_map(path_2f, "2F")
    arr_1f = clean_base_map(path_1f, "1F")

    if is_diff_floor:
        # [1단계 지도] 출발 층 -> 엘리베이터
        st.markdown(f"<div class='map-step-badge'>1단계 : {s_meta['floor']} [{elev_info['name']}]로 이동</div>", unsafe_allow_html=True)
        base_start = arr_2f if s_meta["floor"] == "2F" else arr_1f
        elev_start_box = elev_info[f"{s_meta['floor']}_box"]
        img_s1 = draw_colored_map(base_start, red_key=start_key, elev_box=elev_start_box, mode="TO_ELEV")
        st.image(img_s1, use_container_width=True)

        # [2단계 지도] 도착 층 엘리베이터 -> 목적지 검사실
        st.markdown(f"<div class='map-step-badge'>2단계 : {d_meta['floor']} 하차 ➔ [{d_meta['name']}] 도착</div>", unsafe_allow_html=True)
        base_dest = arr_2f if d_meta["floor"] == "2F" else arr_1f
        elev_dest_box = elev_info[f"{d_meta['floor']}_box"]
        img_s2 = draw_colored_map(base_dest, green_key=dest_key, elev_box=elev_dest_box, mode="FROM_ELEV")
        st.image(img_s2, use_container_width=True)
    else:
        # 동일 층 지도 1장
        st.markdown(f"<div class='map-step-badge'>{s_meta['floor']} 동선 안내</div>", unsafe_allow_html=True)
        base_same = arr_2f if s_meta["floor"] == "2F" else arr_1f
        img_same = draw_colored_map(base_same, red_key=start_key, green_key=dest_key, mode="SAME")
        st.image(img_same, use_container_width=True)

# 하단 간단 AI 챗봇
with st.expander("💬 길 안내 AI 질문하기"):
    q = st.text_input("질문을 입력하세요:", placeholder="예: 지금 채혈실 어떻게 가나요?")
    if q:
        st.success(f"현재 위치({s_meta['name']})에서 {d_meta['name']}(으)로 이동하시면 됩니다. 지도에 표시된 경로를 확인해 주세요!")
