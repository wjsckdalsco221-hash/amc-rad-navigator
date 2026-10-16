import os
import streamlit as st
import numpy as np
from PIL import Image, ImageDraw

# ---------------------------------------------------------
# 1. 기본 레이아웃 설정
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
if "nav_mode" not in st.session_state:
    st.session_state.nav_mode = "exam"  # 'exam' 또는 'custom'
if "selected_exam_idx" not in st.session_state:
    st.session_state.selected_exam_idx = 0

# 출발 위치 세션
if "sel_bldg" not in st.session_state:
    st.session_state.sel_bldg = "동관"
if "sel_floor" not in st.session_state:
    st.session_state.sel_floor = "2층"
if "start_key" not in st.session_state:
    st.session_state.start_key = "2F_EAST_XRAY"

# 검사 외 찾아갈 장소 세션
if "sel_dest_bldg" not in st.session_state:
    st.session_state.sel_dest_bldg = "신관"
if "sel_dest_floor" not in st.session_state:
    st.session_state.sel_dest_floor = "2층"
if "custom_dest_key" not in st.session_state:
    st.session_state.custom_dest_key = "2F_NEW_EYE"

# 시간 설정 세션 (기본값: 평일 15:00)
if "day_type" not in st.session_state:
    st.session_state.day_type = "평일(월~금)"
if "time_str" not in st.session_state:
    st.session_state.time_str = "15:00"

# ---------------------------------------------------------
# 2. 반응형 CSS
# ---------------------------------------------------------
if st.session_state.page == "home":
    container_max_width = "480px"
    padding_top = "2.6rem"
else:
    container_max_width = "1200px"
    padding_top = "2.0rem"

st.markdown(f"""
<style>
header[data-testid="stHeader"] {{
    background: transparent !important;
    height: 1.5rem !important;
}}
.block-container {{
    max-width: {container_max_width} !important;
    padding-top: {padding_top} !important;
    padding-bottom: 3rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    margin: 0 auto !important;
    transition: max-width 0.3s ease;
}}
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
    font-size: 0.86rem;
    color: #555555;
    line-height: 1.45;
}}
div.stButton > button {{
    background-color: #2E6930 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    font-size: 0.98rem !important;
    padding: 0.52rem 1.2rem !important;
    width: 100% !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08) !important;
}}
div.stButton > button:hover {{
    background-color: #235225 !important;
    color: #FFFFFF !important;
}}
.dest-banner {{
    background-color: #EBF7EE;
    border: 2px solid #28A745;
    border-radius: 12px;
    padding: 14px 18px;
    margin: 10px 0 16px 0;
    color: #155724;
}}
.map-step-badge {{
    background-color: #005C5C;
    color: white;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 0.92rem;
    font-weight: 700;
    margin-top: 14px;
    margin-bottom: 8px;
    display: inline-block;
}}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. 도면 기반 실제 검사실·시설 좌표 사전
# ---------------------------------------------------------
MAP_ROOMS = {
    # ================= [서관 1층] =================
    "1F_WEST_BLOOD": {
        "name": "서관 1층 채혈실", "short_name": "서관 채혈실",
        "floor": "1층", "floor_code": "1F", "building": "서관",
        "hours": "평일 06:10~18:30, 토 06:30~13:30",
        "boxes": [(0.238, 0.520, 0.320, 0.654)]
    },
    "1F_WEST_CTMR": {
        "name": "서관 1층 외래/응급 CT·MR실", "short_name": "외래/응급 CT·MR실",
        "floor": "1층", "floor_code": "1F", "building": "서관",
        "hours": "상시 운영 (외래·응급)",
        "boxes": [(0.065, 0.508, 0.105, 0.654)]
    },
    "1F_WEST_PHARM": {
        "name": "서관 1층 외래약국", "short_name": "외래약국",
        "floor": "1층", "floor_code": "1F", "building": "서관",
        "hours": "평일 08:30~18:00",
        "boxes": [(0.180, 0.670, 0.215, 0.800)]
    },
    "1F_WEST_RECORD": {
        "name": "서관 1층 의무기록·영상발급 창구", "short_name": "의무기록/영상발급",
        "floor": "1층", "floor_code": "1F", "building": "서관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.105, 0.670, 0.145, 0.800)]
    },
    "1F_WEST_ADMIN": {
        "name": "서관 1층 원무상담실·서관통합창구", "short_name": "서관통합창구 (입·원무)",
        "floor": "1층", "floor_code": "1F", "building": "서관",
        "hours": "평일 08:00~17:30",
        "boxes": [(0.245, 0.670, 0.320, 0.790)]
    },
    "1F_WEST_LIVER": {
        "name": "서관 1층 간담도췌외과", "short_name": "간담도췌외과",
        "floor": "1층", "floor_code": "1F", "building": "서관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.018, 0.215, 0.105, 0.505)]
    },

    # ================= [동관 1층] =================
    "1F_EAST_XRAY": {
        "name": "동관 1층 영상의학과 외래촬영실", "short_name": "영상의학과 외래촬영실",
        "floor": "1층", "floor_code": "1F", "building": "동관",
        "hours": "평일 08:00~17:30 (주간 운영)",
        "boxes": [(0.508, 0.313, 0.550, 0.540)]
    },
    "1F_EAST_NEURO": {
        "name": "동관 1층 신경과·파킨슨병센터·신경외과", "short_name": "신경과·신경외과",
        "floor": "1층", "floor_code": "1F", "building": "동관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.562, 0.330, 0.665, 0.505)]
    },
    "1F_EAST_INJECT": {
        "name": "동관 1층 동관주사실", "short_name": "동관주사실",
        "floor": "1층", "floor_code": "1F", "building": "동관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.385, 0.555, 0.445, 0.660)]
    },
    "1F_EAST_ADMIT": {
        "name": "동관 1층 입원지원센터·대외협력실", "short_name": "입원지원센터",
        "floor": "1층", "floor_code": "1F", "building": "동관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.585, 0.520, 0.665, 0.660)]
    },
    "1F_EAST_DIAB": {
        "name": "동관 1층 당뇨병센터·내분비내과", "short_name": "당뇨병센터·내분비내과",
        "floor": "1층", "floor_code": "1F", "building": "동관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.360, 0.340, 0.465, 0.550)]
    },
    "1F_EAST_HEART": {
        "name": "동관 1층 심장병원", "short_name": "심장병원",
        "floor": "1층", "floor_code": "1F", "building": "동관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.562, 0.725, 0.665, 0.920)]
    },

    # ================= [신관 1층] =================
    "1F_NEW_BLOOD": {
        "name": "신관 1층 채혈실", "short_name": "신관 채혈실",
        "floor": "1층", "floor_code": "1F", "building": "신관",
        "hours": "평일 06:10~17:30 (주말·공휴일 미운영)",
        "boxes": [(0.742, 0.550, 0.795, 0.635)]
    },
    "1F_NEW_PED_XRAY": {
        "name": "신관 1층 소아영상의학과", "short_name": "소아영상의학과",
        "floor": "1층", "floor_code": "1F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.898, 0.415, 0.970, 0.812)]
    },
    "1F_NEW_OBGYN": {
        "name": "신관 1층 산부인과", "short_name": "산부인과",
        "floor": "1층", "floor_code": "1F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.680, 0.295, 0.795, 0.535)]
    },
    "1F_NEW_ENT": {
        "name": "신관 1층 이비인후과·이비인후과 검사실", "short_name": "이비인후과·검사실",
        "floor": "1층", "floor_code": "1F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.680, 0.065, 0.865, 0.258)]
    },
    "1F_NEW_PED_ECG": {
        "name": "신관 1층 소아심장·소아심전도검사실", "short_name": "소아심장·심전도실",
        "floor": "1층", "floor_code": "1F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.898, 0.275, 0.970, 0.350)]
    },
    "1F_NEW_PED_INJ": {
        "name": "신관 1층 소아주사실", "short_name": "소아주사실",
        "floor": "1층", "floor_code": "1F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.898, 0.350, 0.970, 0.415)]
    },

    # ================= [서관 2층] =================
    "2F_WEST_CT": {
        "name": "서관 2층 CT실 / 투시조영실", "short_name": "CT실 / 투시조영실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.223, 0.106, 0.307, 0.292), (0.223, 0.319, 0.259, 0.585), (0.267, 0.398, 0.307, 0.585)]
    },
    "2F_WEST_DIAG": {
        "name": "서관 2층 진단검사의학과 (CT/MR 채혈실)", "short_name": "진단검사의학과(CT/MR채혈)",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "야간/휴일 전용 (18:30~익일 06:10)",
        "boxes": [(0.005, 0.228, 0.096, 0.692)]
    },
    "2F_WEST_PREADM": {
        "name": "서관 2층 입원전검사실", "short_name": "입원전검사실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:30~17:00 (토요일 미운영)",
        "boxes": [(0.155, 0.718, 0.193, 0.909)]
    },
    "2F_WEST_US": {
        "name": "서관 2층 초음파실", "short_name": "서관 초음파실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:00~17:30",
        "boxes": [(0.220, 0.718, 0.310, 0.873)]
    },
    "2F_WEST_BREAST": {
        "name": "서관 2층 유방·두경부 영상의학검사실", "short_name": "유방·두경부검사실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:00~17:30",
        "boxes": [(0.116, 0.320, 0.215, 0.585)]
    },
    "2F_WEST_BRONCHO": {
        "name": "서관 2층 기관지내시경·호흡기검사실", "short_name": "기관지내시경·호흡기",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.220, 0.875, 0.310, 0.990)]
    },

    # ================= [동관 2층] =================
    "2F_EAST_XRAY": {
        "name": "동관 2층 영상의학과 일반촬영실", "short_name": "동관 일반촬영실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:00~18:00 (야간/당직 운영)",
        "boxes": [(0.340, 0.275, 0.420, 0.355), (0.340, 0.355, 0.410, 0.556), (0.390, 0.556, 0.410, 0.638)]
    },
    "2F_EAST_MR": {
        "name": "동관 2층 MR실", "short_name": "동관 MR실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 07:30~20:00",
        "boxes": [(0.340, 0.007, 0.435, 0.255)]
    },
    "2F_EAST_ANGIO": {
        "name": "동관 2층 혈관조영실 (1~9)", "short_name": "혈관조영실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.440, 0.007, 0.575, 0.255)]
    },
    "2F_EAST_NUC": {
        "name": "동관 2층 동관 핵의학과 (혈액/영상검사실)", "short_name": "핵의학과 검사실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:00~17:30",
        "boxes": [(0.485, 0.275, 0.655, 0.640)]
    },
    "2F_EAST_BRAIN": {
        "name": "동관 2층 뇌신경검사실 (근전도,뇌파,수면,유발전위)", "short_name": "뇌신경검사실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.340, 0.730, 0.448, 0.970)]
    },
    "2F_EAST_HEART": {
        "name": "동관 2층 심장검사실 (심전도,심초음파,홀터)", "short_name": "심장검사실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.595, 0.730, 0.655, 0.970)]
    },
    "2F_EAST_CONSULT": {
        "name": "동관 2층 외래회송 상담실", "short_name": "외래회송 상담실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.455, 0.730, 0.548, 0.865)]
    },

    # ================= [신관 2층] =================
    "2F_NEW_MR": {
        "name": "신관 2층 MR실", "short_name": "신관 MR실",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.685, 0.255, 0.815, 0.450)]
    },
    "2F_NEW_XRAY_US": {
        "name": "신관 2층 일반촬영실·투시조영실·초음파실", "short_name": "일반촬영·초음파실",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:00~17:30",
        "boxes": [(0.695, 0.450, 0.815, 0.685)]
    },
    "2F_NEW_DENTAL": {
        "name": "신관 2층 치과 / 소아치과", "short_name": "치과·소아치과",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.685, 0.035, 0.878, 0.225)]
    },
    "2F_NEW_EYE": {
        "name": "신관 2층 안과 / 안과검사실 / 소아안과", "short_name": "안과·안과검사실",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.895, 0.250, 0.975, 0.685)]
    },
    "2F_NEW_BMD": {
        "name": "신관 2층 신관 핵의학과 골밀도검사실", "short_name": "골밀도검사실",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.685, 0.725, 0.728, 0.970)]
    },
    "2F_NEW_PLASTIC": {
        "name": "신관 2층 성형외과", "short_name": "성형외과",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.730, 0.780, 0.810, 0.970)]
    },
    "2F_NEW_DERMA": {
        "name": "신관 2층 피부과", "short_name": "피부과",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.908, 0.780, 0.965, 0.970)]
    }
}

ELEVATORS = {
    "서관": {"name": "서관 엘리베이터", "2F_box": (0.100, 0.355, 0.120, 0.550), "1F_box": (0.148, 0.608, 0.195, 0.652)},
    "동관": {"name": "동관 엘리베이터", "2F_box": (0.475, 0.640, 0.538, 0.692), "1F_box": (0.488, 0.588, 0.545, 0.638)},
    "신관": {"name": "신관 엘리베이터", "2F_box": (0.860, 0.618, 0.885, 0.672), "1F_box": (0.825, 0.573, 0.886, 0.622)}
}

PATIENT_EXAMS = [
    {
        "title": "[검사] 일반촬영 (흉부 X-ray)",
        "sub": "평일 08:00~17:30 동관 1층 / 그 외 시간 동관 2층",
        "default_key": "1F_EAST_XRAY",
        "cat": "XRAY"
    },
    {
        "title": "[검사] 가정의학과 검체검사",
        "sub": "서관 1층 채혈실(평일 06:10~18:30) / 야간 서관 2층",
        "default_key": "1F_WEST_BLOOD",
        "cat": "BLOOD"
    },
    {
        "title": "[검사] 복부 조영 CT",
        "sub": "서관 2층 CT실(평일 08:00~18:00)",
        "default_key": "2F_WEST_CT",
        "cat": "CT"
    },
    {
        "title": "[검사] 뇌 신경 MRI",
        "sub": "신관 2층 신관 MR실(평일 08:00~18:00)",
        "default_key": "2F_NEW_MR",
        "cat": "MR"
    }
]

# ---------------------------------------------------------
# 4. 시간·상황 매칭 규칙 엔진 (일반촬영 X-ray 시간별 동적 분기 탑재)
# ---------------------------------------------------------
def resolve_dest_key(exam, start_key, day_type, time_str):
    cat = exam["cat"]
    t_val = int(time_str.replace(":", ""))
    start_bldg = MAP_ROOMS[start_key]["building"]

    # 1) 일반촬영(X-ray) 시간별 분기 규칙
    if cat == "XRAY":
        # 평일 08:00 ~ 17:30 ➔ 동관 1층 영상의학과 외래촬영실
        if day_type == "평일(월~금)" and 800 <= t_val <= 1730:
            return "1F_EAST_XRAY"
        # 그 외 시간대 (17:30 이후, 08:00 이전, 주말/공휴일) ➔ 동관 2층 일반촬영실
        else:
            return "2F_EAST_XRAY"

    # 2) 채혈실 시간별 분기 규칙
    elif cat == "BLOOD":
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
# 5. 이미지 로드 및 도면 가공 (방 관통 방지 복도 동선)
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
        teals = [(0.340, 0.270, 0.430, 0.642), (0.685, 0.248, 0.833, 0.452), (0.220, 0.872, 0.316, 0.916)]
    else:
        teals = [(0.015, 0.215, 0.108, 0.505), (0.335, 0.555, 0.391, 0.660), (0.895, 0.412, 0.999, 0.816)]

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

def draw_colored_map(base_arr, red_key=None, green_key=None, elev_box=None, mode="SAME", floor_code="2F"):
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
            is_bg = (sub[:,:,0] > 240) & (sub[:,:,1] > 242) & (sub[:,:,2] > 242)
            sub[is_bg] = rgb
            arr[y1:y2, x1:x2] = sub
        return (int(np.mean([c[0] for c in centers])), int(np.mean([c[1] for c in centers]))), boxes

    red_res = fill_box(red_key, [255, 200, 200])     # 내 위치: 연빨강
    green_res = fill_box(green_key, [188, 245, 200]) # 목적지: 연녹색

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

    # 방을 관통하지 않는 층별 중앙 복도선 (1층 67.2% / 2층 66.5%)
    corridor_y = int(H * 0.672) if floor_code == "1F" else int(H * 0.665)

    if mode == "SAME" and red_res and green_res and red_key != green_key:
        sx, sy = red_res[0]
        dx, dy = green_res[0]
        draw.line([(sx, sy), (sx, corridor_y), (dx, corridor_y), (dx, dy)], fill=(0, 102, 102), width=lw)
        draw.ellipse([sx-r_rad, sy-r_rad, sx+r_rad, sy+r_rad], fill=(217, 48, 37), outline=(255, 255, 255), width=2)
        draw.ellipse([dx-r_rad, dy-r_rad, dx+r_rad, dy+r_rad], fill=(30, 142, 62), outline=(255, 255, 255), width=2)

    elif mode == "TO_ELEV" and red_res and elev_center:
        sx, sy = red_res[0]
        ex, ey = elev_center
        draw.line([(sx, sy), (sx, corridor_y), (ex, corridor_y), (ex, ey)], fill=(217, 48, 37), width=lw)
        draw.ellipse([sx-r_rad, sy-r_rad, sx+r_rad, sy+r_rad], fill=(217, 48, 37), outline=(255, 255, 255), width=2)
        draw.ellipse([ex-r_rad, ey-r_rad, ex+r_rad, ey+r_rad], fill=(255, 140, 0), outline=(255, 255, 255), width=2)

    elif mode == "FROM_ELEV" and elev_center and green_res:
        ex, ey = elev_center
        dx, dy = green_res[0]
        draw.line([(ex, ey), (ex, corridor_y), (dx, corridor_y), (dx, dy)], fill=(30, 142, 62), width=lw)
        draw.ellipse([ex-r_rad, ey-r_rad, ex+r_rad, ey+r_rad], fill=(255, 140, 0), outline=(255, 255, 255), width=2)
        draw.ellipse([dx-r_rad, dy-r_rad, dx+r_rad, dy+r_rad], fill
