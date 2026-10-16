import os
import streamlit as st
import numpy as np
from PIL import Image, ImageDraw

# 페이지 기본 설정 (직원용 기능 제거 완료 · 환자 전용 화면)
st.set_page_config(
    page_title="AMC 위치·시간 인지형 맞춤형 검사실 길 안내 AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 스타일
st.markdown("""
<style>
.main-banner {
    background: linear-gradient(135deg, #005C5C 0%, #003D3D 100%);
    color: white;
    padding: 16px 22px;
    border-radius: 12px;
    margin-bottom: 14px;
}
.main-banner h2 { margin: 0; font-size: 1.4rem; font-weight: 700; color: #FFFFFF; }
.main-banner p { margin: 4px 0 0 0; font-size: 0.88rem; color: #D2EBEB; }
.schedule-card {
    background-color: #FFFFFF;
    border: 1px solid #DCE6E6;
    border-left: 6px solid #005C5C;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 8px;
}
.smart-card {
    background-color: #F4FBFB;
    border: 2px solid #005C5C;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
}
.route-step {
    background-color: #FFFFFF;
    border: 1px solid #B0C4C4;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 8px 0;
    font-weight: 600;
    color: #143C5A;
    font-size: 0.92rem;
}
.step-badge {
    background-color: #005C5C;
    color: white;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.9rem;
    display: inline-block;
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 1층 및 2층 검사실 좌표 사전 (실제 도면 이미지 비율 0.0 ~ 1.0 기준)
# ---------------------------------------------------------
MAP_ROOMS = {
    # ================= [2층 검사실] =================
    "2F_EAST_XRAY": {
        "name": "동관 2층 영상의학과 일반촬영실",
        "floor": "2F", "building": "동관",
        "hours": "월~금 08:00~18:00 상시 운영",
        "boxes": [
            (0.344, 0.275, 0.425, 0.355),
            (0.344, 0.355, 0.416, 0.556),
            (0.397, 0.556, 0.415, 0.638)
        ]
    },
    "2F_WEST_CT": {
        "name": "서관 2층 CT실 / 투시조영실",
        "floor": "2F", "building": "서관",
        "hours": "월~금 08:00~18:00 (예약 및 당일 안내)",
        "boxes": [
            (0.223, 0.106, 0.307, 0.292),
            (0.223, 0.319, 0.259, 0.585),
            (0.267, 0.398, 0.307, 0.585)
        ]
    },
    "2F_WEST_DIAG": {
        "name": "서관 2층 진단검사의학과 (CT/MR 채혈실)",
        "floor": "2F", "building": "서관",
        "hours": "평일 18:30~익일 06:10 / 휴일 17:30~익일 06:30 야간운영",
        "boxes": [(0.008, 0.228, 0.096, 0.692)]
    },
    "2F_WEST_PREADM": {
        "name": "서관 2층 입원전검사실",
        "floor": "2F", "building": "서관",
        "hours": "월~금 08:30~17:00 / 일·공휴일 13:00~17:00 (토요일 미운영)",
        "boxes": [
            (0.160, 0.718, 0.193, 0.909),
            (0.193, 0.718, 0.215, 0.822)
        ]
    },
    "2F_WEST_US": {
        "name": "서관 2층 초음파실",
        "floor": "2F", "building": "서관",
        "hours": "월~금 08:00~17:30 (금식 여부 확인)",
        "boxes": [
            (0.240, 0.718, 0.313, 0.873),
            (0.222, 0.768, 0.240, 0.873)
        ]
    },
    "2F_EAST_MR": {
        "name": "동관 2층 MR실",
        "floor": "2F", "building": "동관",
        "hours": "월~금 07:30~20:00",
        "boxes": [(0.344, 0.007, 0.443, 0.249)]
    },
    "2F_EAST_HEART": {
        "name": "동관 2층 심장검사실",
        "floor": "2F", "building": "동관",
        "hours": "월~금 08:30~17:30",
        "boxes": [(0.609, 0.735, 0.669, 0.990)]
    },
    "2F_NEW_MR": {
        "name": "신관 2층 MR실",
        "floor": "2F", "building": "신관",
        "hours": "월~금 08:00~18:00",
        "boxes": [(0.696, 0.252, 0.829, 0.449)]
    },
    "2F_NEW_XRAY_US": {
        "name": "신관 2층 일반촬영실 · 투시조영실 · 초음파실",
        "floor": "2F", "building": "신관",
        "hours": "월~금 08:00~17:30",
        "boxes": [
            (0.696, 0.449, 0.829, 0.605),
            (0.707, 0.605, 0.820, 0.682)
        ]
    },

    # ================= [1층 검사실] =================
    "1F_WEST_BLOOD": {
        "name": "서관 1층 채혈실",
        "floor": "1F", "building": "서관",
        "hours": "월~금 06:10~18:30 / 토 06:30~13:30 (휴일 CT/MR 시 06:30~17:30)",
        "boxes": [(0.241, 0.520, 0.317, 0.654)]
    },
    "1F_NEW_BLOOD": {
        "name": "신관 1층 채혈실",
        "floor": "1F", "building": "신관",
        "hours": "월~금 06:10~17:30 (토/일/공휴일 미운영)",
        "boxes": [(0.749, 0.550, 0.800, 0.635)]
    },
    "1F_EAST_XRAY": {
        "name": "동관 1층 영상의학과 외래촬영실",
        "floor": "1F", "building": "동관",
        "hours": "월~금 08:00~17:30",
        "boxes": [
            (0.516, 0.313, 0.554, 0.538),
            (0.505, 0.485, 0.534, 0.538)
        ]
    },
    "1F_WEST_CTMR": {
        "name": "서관 1층 외래/응급 CT·MR실",
        "floor": "1F", "building": "서관",
        "hours": "상시 운영 (외래 및 응급 예약)",
        "boxes": [(0.068, 0.514, 0.106, 0.654)]
    },
    "1F_NEW_PED_XRAY": {
        "name": "신관 1층 소아영상의학과",
        "floor": "1F", "building": "신관",
        "hours": "월~금 08:30~17:30",
        "boxes": [(0.907, 0.415, 0.998, 0.812)]
    }
}

# ---------------------------------------------------------
# 2. 건물별(서관·동관·신관) 엘리베이터 좌표 사전 (2층 도면 & 1층 도면 매칭)
# ---------------------------------------------------------
ELEVATORS = {
    "서관": {
        "name": "서관 중앙 엘리베이터",
        "2F_box": (0.100, 0.355, 0.120, 0.550),
        "1F_box": (0.148, 0.608, 0.195, 0.652)
    },
    "동관": {
        "name": "동관 중앙 엘리베이터",
        "2F_box": (0.475, 0.640, 0.538, 0.692),
        "1F_box": (0.488, 0.588, 0.545, 0.638)
    },
    "신관": {
        "name": "신관 중앙 엘리베이터",
        "2F_box": (0.860, 0.618, 0.885, 0.672),
        "1F_box": (0.825, 0.573, 0.886, 0.622)
    }
}

# 가상 환자 시나리오 데이터
PATIENTS = {
    "P001": {
        "name": "김아산 (2층 일반촬영 후 ➔ 1층 채혈 & 2층 CT 환자)",
        "date_str": "2026년 06월 29일 월요일",
        "has_ct_mr": True,
        "exams": [
            {"name": "일반촬영 (흉부 X-ray)", "dept": "영상의학과", "status": "완료", "room_key": "2F_EAST_XRAY", "cat": "XRAY"},
            {"name": "[검사] 가정의학과 검체검사 (1층 채혈실)", "dept": "가정의학과", "status": "대기", "room_key": "1F_WEST_BLOOD", "cat": "BLOOD"},
            {"name": "복부 조영 CT (2층 CT실)", "dept": "영상의학과", "status": "대기", "room_key": "2F_WEST_CT", "cat": "CT"},
            {"name": "뇌 신경 MRI (2층 신관 MR실)", "dept": "영상의학과", "status": "대기", "room_key": "2F_NEW_MR", "cat": "MR"}
        ]
    },
    "P002": {
        "name": "이건강 (1층 외래촬영 후 ➔ 2층 입원전검사 & 초음파 환자)",
        "date_str": "2026년 06월 29일 월요일",
        "has_ct_mr": False,
        "exams": [
            {"name": "동관 1층 외래 일반촬영", "dept": "영상의학과", "status": "완료", "room_key": "1F_EAST_XRAY", "cat": "XRAY"},
            {"name": "[검사] 서관 2층 입원전검사실 검사", "dept": "내과", "status": "대기", "room_key": "2F_WEST_PREADM", "cat": "PREADM"},
            {"name": "서관 2층 상복부 초음파", "dept": "영상의학과", "status": "대기", "room_key": "2F_WEST_US", "cat": "US"}
        ]
    }
}

# ---------------------------------------------------------
# 3. 시간·상황에 따른 채혈실/검사실 자동 매칭 규칙 엔진
# ---------------------------------------------------------
def resolve_destination_room(exam, start_key, day_type, time_str, has_ct_mr):
    t_val = int(time_str.replace(":", ""))
    cat = exam["cat"]
    start_bldg = MAP_ROOMS[start_key]["building"]

    if cat == "BLOOD":
        if day_type == "평일(월~금)":
            if 610 <= t_val <= 1730:
                # 출발 건물이 신관이면 신관 1층 채혈실, 그 외에는 서관 1층 채혈실 추천
                if start_bldg == "신관":
                    return "OK", "1F_NEW_BLOOD", f"현재 시각({day_type} {time_str}) 주간 운영 중이며, 현재 계신 신관에서 바로 내려가실 수 있는 '신관 1층 채혈실(06:10~17:30)'로 안내합니다."
                return "OK", "1F_WEST_BLOOD", f"현재 시각({day_type} {time_str}) 정상 운영 중인 '서관 1층 채혈실(06:10~18:30)'로 맞춤 안내합니다."
            elif 1730 < t_val <= 1830:
                return "OK", "1F_WEST_BLOOD", f"⚠️ 현재 시각({time_str})에는 '신관 1층 채혈실(17:30 마감)' 운영이 종료되었습니다. 18:30까지 운영 중인 '서관 1층 채혈실'로 안내합니다."
            else:
                return "OK", "2F_WEST_DIAG", f"현재 시각({time_str})은 1층 주간 채혈실 마감 시간대입니다. 야간 운영 검사실인 '서관 2층 진단검사의학과(CT/MR 채혈실)'로 안내합니다."
        elif day_type == "토요일":
            if 630 <= t_val <= 1330:
                return "OK", "1F_WEST_BLOOD", "토요일 오전 운영 중인 '서관 1층 채혈실(06:30~13:30)'로 안내합니다 (신관 1층 채혈실은 토요일 미운영)."
            elif 1330 < t_val <= 1730 and has_ct_mr:
                return "OK", "1F_WEST_BLOOD", "당일 CT/MR 검사가 예정된 환자분이므로 휴일 특례 기준(06:30~17:30)에 따라 '서관 1층 채혈실' 이용이 가능합니다."
            else:
                return "OK", "2F_WEST_DIAG", "토요일 오후/야간 시간대이므로 '서관 2층 진단검사의학과(CT/MR 채혈실)'로 안내합니다."
        else:  # 일요일/공휴일
            if 630 <= t_val <= 1730 and has_ct_mr:
                return "OK", "1F_WEST_BLOOD", "휴일 당일 CT/MR 검사 환자 특례 기준에 따라 '서관 1층 채혈실(06:30~17:30)'로 안내합니다."
            else:
                return "OK", "2F_WEST_DIAG", "일요일/공휴일 운영 검사실인 '서관 2층 진단검사의학과(CT/MR 채혈실)'로 안내합니다."

    elif cat == "PREADM":
        if day_type == "토요일":
            return "RESTRICTED", "2F_WEST_PREADM", "⛔ '서관 2층 입원전검사실'은 토요일 미운영입니다(평일 08:30~17:00, 일/공휴일 13:00~17:00 운영). 헛걸음 방지를 위해 방문을 보류해 주세요."
        return "OK", "2F_WEST_PREADM", f"현재 시각({day_type} {time_str}) 정상 운영 중인 '서관 2층 입원전검사실'로 안내합니다."

    return "OK", exam["room_key"], f"다음 예정 검사실인 '{MAP_ROOMS[exam['room_key']]['name']}'로 맞춤 경로를 안내합니다."

# ---------------------------------------------------------
# 4. 1층 / 2층 도면 이미지 로드 및 기존 청록색 박스 초기화
# ---------------------------------------------------------
def find_floor_image(floor_str):
    if floor_str == "2F":
        candidates = ["서동신_2층_지도.png", "서동신_2층_지도_2.png", "서동신_2층_지도.jpg"]
        keyword = "2층"
    else:
        candidates = ["서동신_1층_지도.png", "서동신_1층_지도_2.png", "서동신_1층_지도.jpg"]
        keyword = "1층"

    for c in candidates:
        if os.path.exists(c):
            return c
    for f in os.listdir("."):
        if f.lower().endswith((".png", ".jpg", ".jpeg")) and keyword in f:
            return f
    return None

@st.cache_data
def load_and_clean_map(img_path, floor_str):
    """
    원본 도면 이미지(1층, 2층)에 기본적으로 칠해져 있던 진한 청록색 방들을
    다른 일반 방들과 동일하게 깔끔한 흰색 배경 + 검은색 글씨로 초기화합니다.
    """
    img = Image.open(img_path).convert("RGB")
    arr = np.array(img)
    H, W, _ = arr.shape

    if floor_str == "2F":
        teal_regions = [
            (0.340, 0.270, 0.430, 0.642),  # 동관 2층 일반촬영실
            (0.692, 0.248, 0.833, 0.452),  # 신관 2층 MR실
            (0.220, 0.872, 0.316, 0.916)   # 서관 2층 기관지내시경실
        ]
    else:
        teal_regions = [
            (0.015, 0.215, 0.108, 0.505),  # 서관 1층 간담도췌외과
            (0.335, 0.555, 0.391, 0.660),  # 동관 1층 외래회송상담실
            (0.905, 0.412, 0.999, 0.816)   # 신관 1층 소아영상의학과
        ]

    for (x1p, y1p, x2p, y2p) in teal_regions:
        x1, y1 = int(x1p * W), int(y1p * H)
        x2, y2 = int(x2p * W), int(y2p * H)
        sub = arr[y1:y2, x1:x2].astype(np.int16)
        r, g, b = sub[:, :, 0], sub[:, :, 1], sub[:, :, 2]

        is_teal = (g > r + 20) & (b > r + 20) & (r < 95)
        is_white_text = (r > 175) & (g > 190) & (b > 190)

        sub[is_white_text] = [30, 30, 30]
        sub[is_teal] = [255, 255, 255]
        arr[y1:y2, x1:x2] = sub.astype(np.uint8)

    return arr

# ---------------------------------------------------------
# 5. 도면 위 방 컬러 매핑 (연한 빨간색 / 연한 녹색 / 엘리베이터 강조)
# ---------------------------------------------------------
def draw_custom_floor_map(base_arr, red_room_key=None, green_room_key=None, elev_box=None, mode="SAME_FLOOR"):
    """
    mode:
      - "SAME_FLOOR": 동일 층 이동 (red_room_key ➔ green_room_key)
      - "TO_ELEV": 출발 층에서 가까운 엘리베이터로 이동 (red_room_key ➔ elev_box)
      - "FROM_ELEV": 도착 층 엘리베이터에서 목표 검사실로 이동 (elev_box ➔ green_room_key)
    """
    arr = base_arr.copy()
    H, W, _ = arr.shape

    def paint_room_boxes(room_key, fill_rgb):
        if not room_key or room_key not in MAP_ROOMS:
            return None
        boxes = MAP_ROOMS[room_key]["boxes"]
        centers = []
        for (x1p, y1p, x2p, y2p) in boxes:
            x1, y1 = int(x1p * W), int(y1p * H)
            x2, y2 = int(x2p * W), int(y2p * H)
            centers.append(((x1 + x2) // 2, (y1 + y2) // 2))

            sub = arr[y1:y2, x1:x2]
            is_bg = (sub[:, :, 0] > 242) & (sub[:, :, 1] > 244) & (sub[:, :, 2] > 244)
            sub[is_bg] = fill_rgb
            arr[y1:y2, x1:x2] = sub

        cx = int(np.mean([c[0] for c in centers]))
        cy = int(np.mean([c[1] for c in centers]))
        return (cx, cy), boxes

    # 1) 내 위치(A) 연한 빨간색 채색 (#FFC8C8)
    red_res = paint_room_boxes(red_room_key, [255, 200, 200])
    # 2) 가야 할 검사실(B) 연한 녹색 채색 (#BCF5C8)
    green_res = paint_room_boxes(green_room_key, [188, 245, 200])

    pil_img = Image.fromarray(arr)
    draw = ImageDraw.Draw(pil_img)
    border_w = max(3, int(W * 0.0025))

    if red_res:
        _, r_boxes = red_res
        for (x1p, y1p, x2p, y2p) in r_boxes:
            draw.rectangle([int(x1p * W), int(y1p * H), int(x2p * W), int(y2p * H)], outline=(217, 48, 37), width=border_w)

    if green_res:
        _, g_boxes = green_res
        for (x1p, y1p, x2p, y2p) in g_boxes:
            draw.rectangle([int(x1p * W), int(y1p * H), int(x2p * W), int(y2p * H)], outline=(30, 142, 62), width=border_w)

    # 3) 엘리베이터 강조 표시 (주황/황금색 테두리 및 마커)
    elev_center = None
    if elev_box is not None:
        ex1, ey1 = int(elev_box[0] * W), int(elev_box[1] * H)
        ex2, ey2 = int(elev_box[2] * W), int(elev_box[3] * H)
        elev_center = ((ex1 + ex2) // 2, (ey1 + ey2) // 2)
        pad = max(6, int(W * 0.004))
        draw.rectangle([ex1 - pad, ey1 - pad, ex2 + pad, ey2 + pad], outline=(255, 140, 0), width=border_w + 2)

    # 4) 동선 연결선 및 출발/도착 포인트 원형 마커 그리기
    line_w = max(4, int(W * 0.003))
    r_rad = max(10, int(W * 0.0075))
    corridor_y = int(H * 0.65)

    if mode == "SAME_FLOOR" and red_res and green_res and red_room_key != green_room_key:
        (sx, sy), _ = red_res
        (dx, dy), _ = green_res
        draw.line([(sx, sy), (sx, corridor_y), (dx, corridor_y), (dx, dy)], fill=(0, 102, 102), width=line_w)
        draw.ellipse([sx - r_rad, sy - r_rad, sx + r_rad, sy + r_rad], fill=(217, 48, 37), outline=(255, 255, 255), width=2)
        draw.ellipse([dx - r_rad, dy - r_rad, dx + r_rad, dy + r_rad], fill=(30, 142, 62), outline=(255, 255, 255), width=2)

    elif mode == "TO_ELEV" and red_res and elev_center:
        (sx, sy), _ = red_res
        (ex, ey) = elev_center
        draw.line([(sx, sy), (sx, ey), (ex, ey)], fill=(217, 48, 37), width=line_w)
        draw.ellipse([sx - r_rad, sy - r_rad, sx + r_rad, sy + r_rad], fill=(217, 48, 37), outline=(255, 255, 255), width=2)
        draw.ellipse([ex - r_rad, ey - r_rad, ex + r_rad, ey + r_rad], fill=(255, 140, 0), outline=(255, 255, 255), width=2)

    elif mode == "FROM_ELEV" and elev_center and green_res:
        (ex, ey) = elev_center
        (dx, dy), _ = green_res
        draw.line([(ex, ey), (dx, ey), (dx, dy)], fill=(30, 142, 62), width=line_w)
        draw.ellipse([ex - r_rad, ey - r_rad, ex + r_rad, ey + r_rad], fill=(255, 140, 0), outline=(255, 255, 255), width=2)
        draw.ellipse([dx - r_rad, dy - r_rad, dx + r_rad, dy + r_rad], fill=(30, 142, 62), outline=(255, 255, 255), width=2)

    return pil_img

# ---------------------------------------------------------
# 6. 세션 상태 관리 및 사이드바 컨트롤러
# ---------------------------------------------------------
if "patient_id" not in st.session_state:
    st.session_state.patient_id = "P001"
if "start_key" not in st.session_state:
    st.session_state.start_key = "2F_EAST_XRAY"  # 기본 출발: 동관 2층 일반촬영실
if "selected_exam_idx" not in st.session_state:
    st.session_state.selected_exam_idx = 1       # 기본 도착: 1층 채혈실 (2층 -> 1층 층간 이동 시연!)
if "day_type" not in st.session_state:
    st.session_state.day_type = "평일(월~금)"
if "time_str" not in st.session_state:
    st.session_state.time_str = "14:20"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "안녕하세요! 출발 위치와 도착 검사실의 층수가 다를 경우, 1단계(엘리베이터 이동 지도)와 2단계(도착 층 검사실 이동 지도) 2장의 지도로 알기 쉽게 안내해 드립니다."}
    ]

with st.sidebar:
    st.markdown("### 🧭 환자 위치(A) 및 시간 설정")
    st.caption("층수가 다른 검사실을 선택하면 **2장의 연속 지도(엘리베이터 경유)**가 자동으로 제공됩니다.")

    st.session_state.patient_id = st.selectbox(
        "👤 가상 환자 선택",
        options=list(PATIENTS.keys()),
        format_func=lambda k: PATIENTS[k]["name"]
    )

    st.session_state.start_key = st.selectbox(
        "🔴 현재 내 위치(A) 선택 (연한 빨간색)",
        options=list(MAP_ROOMS.keys()),
        format_func=lambda k: f"[{MAP_ROOMS[k]['building']} {MAP_ROOMS[k]['floor']}] {MAP_ROOMS[k]['name']}",
        index=list(MAP_ROOMS.keys()).index(st.session_state.start_key)
    )

    st.session_state.day_type = st.selectbox(
        "📅 현재 요일",
        options=["평일(월~금)", "토요일", "일요일/공휴일"]
    )

    st.session_state.time_str = st.select_slider(
        "⏰ 현재 시각",
        options=["08:30", "11:20", "14:20", "17:45", "19:10"],
        value=st.session_state.time_str
    )

    st.divider()
    st.markdown("#### ⚡ 원클릭 시연 프리셋")
    if st.button("🛗 [층간 이동 2장 지도] 동관 2층 촬영실 ➔ 서관 1층 채혈실", use_container_width=True, type="primary"):
        st.session_state.patient_id = "P001"
        st.session_state.start_key = "2F_EAST_XRAY"
        st.session_state.selected_exam_idx = 1  # 1층 채혈실
        st.session_state.day_type = "평일(월~금)"
        st.session_state.time_str = "14:20"

    if st.button("🛗 [층간 이동 2장 지도] 서관 1층 채혈실 ➔ 서관 2층 CT실", use_container_width=True):
        st.session_state.patient_id = "P001"
        st.session_state.start_key = "1F_WEST_BLOOD"
        st.session_state.selected_exam_idx = 2  # 2층 CT실
        st.session_state.day_type = "평일(월~금)"
        st.session_state.time_str = "14:20"

    if st.button("🚶 [동일 층 1장 지도] 동관 2층 촬영실 ➔ 서관 2층 CT실", use_container_width=True):
        st.session_state.patient_id = "P001"
        st.session_state.start_key = "2F_EAST_XRAY"
        st.session_state.selected_exam_idx = 2  # 2층 CT실
        st.session_state.day_type = "평일(월~금)"
        st.session_state.time_str = "14:20"

    if st.button("🛑 [예외 차단] 토요일 입원전검사실 미운영 안내", use_container_width=True):
        st.session_state.patient_id = "P002"
        st.session_state.start_key = "1F_EAST_XRAY"
        st.session_state.selected_exam_idx = 1  # 서관 2층 입원전검사실
        st.session_state.day_type = "토요일"
        st.session_state.time_str = "11:20"

# ---------------------------------------------------------
# 7. 메인 환자 안내 화면
# ---------------------------------------------------------
st.markdown("""
<div class="main-banner">
    <h2>🏥 AI 에이전트 기반 위치·시간 인지형 맞춤형 검사실 길 안내 시스템</h2>
    <p>현재 내 위치(연한 빨간색)와 가야 할 검사실(연한 녹색)의 층수가 다를 경우, ① 가까운 엘리베이터 이동 지도와 ② 엘리베이터 하차 후 목적지 이동 지도를 연속 제공합니다.</p>
</div>
""", unsafe_allow_html=True)

current_patient = PATIENTS[st.session_state.patient_id]
exams = current_patient["exams"]
if st.session_state.selected_exam_idx >= len(exams):
    st.session_state.selected_exam_idx = 0

col_left, col_right = st.columns([0.85, 1.55], gap="large")

with col_left:
    st.markdown(f"#### 📋 나의 검사 일정 ({current_patient['date_str']})")
    for ex in exams:
        is_done = (ex["status"] == "완료")
        r_meta = MAP_ROOMS[ex["room_key"]]
        st.markdown(f"""
        <div class="schedule-card" style="{'border-left: 6px solid #28A745;' if is_done else ''}">
            <strong style="font-size:0.93rem;">{ex['name']}</strong>
            <span style="float:right; font-size:0.8rem; font-weight:700; color:{'#28A745' if is_done else '#D9534F'};">
                {'✅ 완료' if is_done else '⏳ 대기'}
            </span>
            <div style="font-size:0.8rem; color:#666; margin-top:4px;">
                처방과: {ex['dept']} | 기본 위치: {r_meta['building']} {r_meta['floor']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    exam_labels = [f"🟢 {e['name']}" for e in exams]
    st.session_state.selected_exam_idx = st.selectbox(
        "🟢 안내받을 다음 검사 선택:",
        options=range(len(exams)),
        format_func=lambda i: exam_labels[i],
        index=st.session_state.selected_exam_idx
    )

    target_exam = exams[st.session_state.selected_exam_idx]
    start_key = st.session_state.start_key

    # 시간·상황에 맞는 최종 목적지 검사실(dest_key) 판별
    status_code, dest_key, reason_msg = resolve_destination_room(
        target_exam, start_key, st.session_state.day_type, st.session_state.time_str, current_patient["has_ct_mr"]
    )

    s_info = MAP_ROOMS[start_key]
    d_info = MAP_ROOMS[dest_key]
    is_diff_floor = (s_info["floor"] != d_info["floor"])

    # 층간 이동 시 사용할 가까운 엘리베이터 결정 (출발 건물 엘리베이터 우선)
    elev_bldg = s_info["building"]
    elev_info = ELEVATORS[elev_bldg]

    if status_code == "RESTRICTED":
        st.error(f"### 🛑 방문 보류 안내\n\n{reason_msg}")
    else:
        if is_diff_floor:
            route_summary = (
                f"① <b>[{s_info['floor']} 이동]</b> 내 위치({s_info['name']})에서 가까운 <b>{elev_info['name']}</b> 탑승<br>"
                f"② <b>[{d_info['floor']} 이동]</b> {d_info['floor']} 하차 후 <b>{d_info['name']}</b>(연한 녹색) 도착"
            )
            walk_min = 5
        else:
            route_summary = f"내 위치({s_info['name']}) ➔ {s_info['floor']} 실내 연결복도 이동 ➔ <b>{d_info['name']}</b> 도착"
            walk_min = 3

        st.markdown(f"""
        <div class="smart-card">
            <div style="font-size:0.84rem; color:#005C5C; font-weight:700;">
                ✅ {'🛗 층간 이동 (2장의 연속 지도 안내)' if is_diff_floor else '🚶 동일 층 이동 (1장의 지도 안내)'}
            </div>
            <div style="margin-top:6px; font-size:0.92rem;">
                🔴 <b>출발 (내 위치)</b>: [{s_info['floor']}] {s_info['name']}<br>
                🟢 <b>도착 (가야할 곳)</b>: [{d_info['floor']}] {d_info['name']}
            </div>
            <div class="route-step">
                👣 <b>단계별 이동 경로 (예상 도보 약 {walk_min}분)</b><br>{route_summary}
            </div>
            <div style="font-size:0.82rem; color:#444;">
                • <b>시간·상황 매칭 근거</b>: {reason_msg}<br>
                • <b>운영 시간</b>: {d_info['hours']}
            </div>
        </div>
        """, unsafe_allow_html=True)

with col_right:
    map_2f_path = find_floor_image("2F")
    map_1f_path = find_floor_image("1F")

    # 파일이 없을 경우 즉시 업로드할 수 있는 UI 제공
    if not map_2f_path or not map_1f_path:
        st.warning("폴더에서 1층 또는 2층 지도 이미지를 찾지 못했습니다. 아래에서 파일을 선택해 주세요.")
        u1, u2 = st.columns(2)
        if not map_2f_path:
            up2 = u1.file_uploader("서동신_2층_지도.png 업로드", type=["png", "jpg", "jpeg"])
            if up2:
                with open("서동신_2층_지도.png", "wb") as f:
                    f.write(up2.getbuffer())
                st.rerun()
        if not map_1f_path:
            up1 = u2.file_uploader("서동신_1층_지도.png 업로드", type=["png", "jpg", "jpeg"])
            if up1:
                with open("서동신_1층_지도.png", "wb") as f:
                    f.write(up1.getbuffer())
                st.rerun()
    else:
        arr_2f = load_and_clean_map(map_2f_path, "2F")
        arr_1f = load_and_clean_map(map_1f_path, "1F")

        if status_code != "RESTRICTED":
            if is_diff_floor:
                st.markdown("#### 🗺️ 층간 이동 맞춤형 2단계 연속 도면 안내")
                st.caption("🔴 **연한 빨간색**: 내 위치(A)  |  🟠 **주황색 박스**: 경유 엘리베이터  |  🟢 **연한 녹색**: 가야 할 검사실(B)")

                # 1단계 지도 (출발 층: 내 위치 -> 가까운 엘리베이터)
                st.markdown(f"<div class='step-badge'>1단계 지도 ({s_info['floor']}) : 내 위치(연한 빨간색) ➔ 가까운 [{elev_info['name']}]로 이동</div>", unsafe_allow_html=True)
                base_start = arr_2f if s_info["floor"] == "2F" else arr_1f
                elev_start_box = elev_info[f"{s_info['floor']}_box"]
                img_step1 = draw_custom_floor_map(
                    base_start, red_room_key=start_key, green_room_key=None, elev_box=elev_start_box, mode="TO_ELEV"
                )
                st.image(img_step1, use_container_width=True)

                # 2단계 지도 (도착 층: 내린 엘리베이터 -> 목표 검사실)
                st.markdown(f"<div class='step-badge'>2단계 지도 ({d_info['floor']}) : [{elev_info['name']}] 하차 ➔ 가야 할 [{d_info['name']}](연한 녹색) 도착</div>", unsafe_allow_html=True)
                base_dest = arr_2f if d_info["floor"] == "2F" else arr_1f
                elev_dest_box = elev_info[f"{d_info['floor']}_box"]
                img_step2 = draw_custom_floor_map(
                    base_dest, red_room_key=None, green_room_key=dest_key, elev_box=elev_dest_box, mode="FROM_ELEV"
                )
                st.image(img_step2, use_container_width=True)

            else:
                # 동일 층 이동 (1장의 지도에 빨간색 -> 녹색 표시)
                st.markdown(f"#### 🗺️ [{s_info['floor']} 통합 도면] 동일 층 실시간 위치·목적지 안내")
                st.caption("🔴 **연한 빨간색**: 내 위치(A)  |  🟢 **연한 녹색**: 가야 할 검사실(B)")
                base_same = arr_2f if s_info["floor"] == "2F" else arr_1f
                img_same = draw_custom_floor_map(
                    base_same, red_room_key=start_key, green_room_key=dest_key, elev_box=None, mode="SAME_FLOOR"
                )
                st.image(img_same, use_container_width=True)

    # 하단 대화형 AI 도우미
    st.markdown("---")
    st.markdown("#### 💬 대화형 AI 길 안내 도우미")
    user_q = st.chat_input("질문을 입력하세요 (예: 2층 촬영실인데 1층 채혈실 어떻게 내려가나요?)")
    if user_q:
        st.session_state.chat_history.append({"role": "user", "content": user_q})
        if is_diff_floor:
            reply = (
                f"현재 계신 **{s_info['name']}({s_info['floor']})**과 가실 **{d_info['name']}({d_info['floor']})**은 층수가 다릅니다.\n\n"
                f"1. **첫 번째 지도({s_info['floor']})**에서 **연한 빨간색(내 위치)** 근처의 **{elev_info['name']}**(주황색 표시)를 탑승하세요.\n"
                f"2. **두 번째 지도({d_info['floor']})**의 엘리베이터에서 내리신 뒤 **연한 녹색**으로 표시된 **{d_info['name']}**(으)로 이동하시면 됩니다."
            )
        else:
            reply = (
                f"현재 위치와 목적지가 모두 **{s_info['floor']}**에 있습니다. "
                f"지도에서 **연한 빨간색({s_info['name']})**에서 출발하여 **연한 녹색({d_info['name']})**으로 이동해 주세요."
            )
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

    for msg in st.session_state.chat_history[-2:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
