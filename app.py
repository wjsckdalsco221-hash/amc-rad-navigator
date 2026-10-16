import os
import streamlit as st
import numpy as np
from PIL import Image, ImageDraw

# ---------------------------------------------------------
# 1. 모바일 앱 전용 레이아웃 및 상단 잘림 방지 CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="서울아산병원 검사실 길 안내",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
/* 스마트폰 화면 비율(최대 480px) 중앙 정렬 및 상단 잘림 완벽 방지 */
.block-container {
    max-width: 480px !important;
    padding-top: 2.8rem !important;
    padding-bottom: 3rem !important;
    padding-left: 0.9rem !important;
    padding-right: 0.9rem !important;
    margin: 0 auto !important;
}

/* 상단 서울아산병원 길안내 헤더 박스 (잘림 방지 및 가독성 강화) */
.app-header {
    background: linear-gradient(135deg, #005C5C 0%, #003A3A 100%);
    color: white;
    padding: 16px 18px;
    border-radius: 14px;
    margin-top: 4px;
    margin-bottom: 16px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.12);
    box-sizing: border-box;
    width: 100%;
}
.app-header h3 {
    margin: 0;
    font-size: 1.18rem;
    font-weight: 800;
    color: #FFFFFF;
    line-height: 1.35;
    word-break: keep-all;
}
.app-header p {
    margin: 5px 0 0 0;
    font-size: 0.82rem;
    color: #D2EBEB;
    line-height: 1.3;
}

/* 검사 일정 카드 내 뱃지 스타일 */
.badge-exam {
    background-color: #E8F3F3;
    color: #005C5C;
    padding: 3px 9px;
    border-radius: 12px;
    font-size: 0.76rem;
    font-weight: 700;
    margin-right: 6px;
    display: inline-block;
}
.badge-done {
    background-color: #EBF7EE;
    color: #28A745;
    padding: 3px 8px;
    border-radius: 10px;
    font-size: 0.74rem;
    font-weight: 700;
}
.badge-wait {
    background-color: #FFF4E5;
    color: #D97706;
    padding: 3px 8px;
    border-radius: 10px;
    font-size: 0.74rem;
    font-weight: 700;
}

/* 목적지 직관적 안내 배너 */
.dest-banner {
    background-color: #EBF7EE;
    border: 2px solid #28A745;
    border-radius: 12px;
    padding: 12px 14px;
    margin: 10px 0;
    color: #155724;
}

/* 1단계 / 2단계 지도 타이틀 뱃지 */
.map-step-badge {
    background-color: #005C5C;
    color: white;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 0.86rem;
    font-weight: 700;
    margin-top: 12px;
    margin-bottom: 6px;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 관(서관/동관/신관) · 층(1층/2층) · 세부 위치 좌표 데이터
# ---------------------------------------------------------
MAP_ROOMS = {
    # ================= [서관 1층] =================
    "1F_WEST_BLOOD": {
        "name": "서관 채혈실", "short_name": "서관 채혈실",
        "floor": "1층", "floor_code": "1F", "building": "서관",
        "hours": "평일 06:10~18:30 / 토 06:30~13:30",
        "boxes": [(0.241, 0.520, 0.317, 0.654)]
    },
    "1F_WEST_CTMR": {
        "name": "외래/응급 CT·MR실", "short_name": "외래/응급 CT·MR실",
        "floor": "1층", "floor_code": "1F", "building": "서관",
        "hours": "상시 운영 (외래·응급 예약)",
        "boxes": [(0.068, 0.514, 0.106, 0.654)]
    },

    # ================= [서관 2층] =================
    "2F_WEST_CT": {
        "name": "CT실 / 투시조영실", "short_name": "CT실 / 투시조영실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.223, 0.106, 0.307, 0.292), (0.223, 0.319, 0.259, 0.585), (0.267, 0.398, 0.307, 0.585)]
    },
    "2F_WEST_DIAG": {
        "name": "진단검사의학과 (CT/MR 채혈실)", "short_name": "진단검사의학과 (CT/MR 채혈실)",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "야간/휴일 운영 (18:30~익일 06:10)",
        "boxes": [(0.008, 0.228, 0.096, 0.692)]
    },
    "2F_WEST_PREADM": {
        "name": "입원전검사실", "short_name": "입원전검사실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:30~17:00 (토요일 미운영)",
        "boxes": [(0.160, 0.718, 0.193, 0.909), (0.193, 0.718, 0.215, 0.822)]
    },
    "2F_WEST_US": {
        "name": "초음파실", "short_name": "초음파실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:00~17:30",
        "boxes": [(0.240, 0.718, 0.313, 0.873), (0.222, 0.768, 0.240, 0.873)]
    },

    # ================= [동관 1층] =================
    "1F_EAST_XRAY": {
        "name": "영상의학과 외래촬영실", "short_name": "영상의학과 외래촬영실",
        "floor": "1층", "floor_code": "1F", "building": "동관",
        "hours": "평일 08:00~17:30",
        "boxes": [(0.516, 0.313, 0.554, 0.538), (0.505, 0.485, 0.534, 0.538)]
    },

    # ================= [동관 2층] =================
    "2F_EAST_XRAY": {
        "name": "동관 영상의학과 일반촬영실", "short_name": "일반촬영실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:00~18:00 상시 운영",
        "boxes": [(0.344, 0.275, 0.425, 0.355), (0.344, 0.355, 0.416, 0.556), (0.397, 0.556, 0.415, 0.638)]
    },
    "2F_EAST_MR": {
        "name": "동관 MR실", "short_name": "MR실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 07:30~20:00",
        "boxes": [(0.344, 0.007, 0.443, 0.249)]
    },
    "2F_EAST_HEART": {
        "name": "심장검사실", "short_name": "심장검사실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.609, 0.735, 0.669, 0.990)]
    },

    # ================= [신관 1층] =================
    "1F_NEW_BLOOD": {
        "name": "신관 채혈실", "short_name": "신관 채혈실",
        "floor": "1층", "floor_code": "1F", "building": "신관",
        "hours": "평일 06:10~17:30 (주말·공휴일 미운영)",
        "boxes": [(0.749, 0.550, 0.800, 0.635)]
    },
    "1F_NEW_PED_XRAY": {
        "name": "소아영상의학과", "short_name": "소아영상의학과",
        "floor": "1층", "floor_code": "1F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.907, 0.415, 0.998, 0.812)]
    },

    # ================= [신관 2층] =================
    "2F_NEW_MR": {
        "name": "신관 MR실", "short_name": "MR실",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.696, 0.252, 0.829, 0.449)]
    },
    "2F_NEW_XRAY_US": {
        "name": "일반촬영실·초음파실", "short_name": "일반촬영실·초음파실",
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

# 나의 검사 일정 데이터 (2번째 이미지 스타일에 맞춘 구성)
PATIENT_EXAMS = [
    {
        "title": "[검사] 일반촬영 (흉부 X-ray)",
        "loc_desc": "동관 2층 일반촬영실 (평일 08:00~18:00)",
        "status": "완료",
        "default_key": "2F_EAST_XRAY",
        "cat": "XRAY"
    },
    {
        "title": "[검사] 가정의학과 검체검사 (채혈)",
        "loc_desc": "서관 1층 채혈실 (평일 06:10~18:30, 토 06:30~13:30)",
        "status": "대기",
        "default_key": "1F_WEST_BLOOD",
        "cat": "BLOOD"
    },
    {
        "title": "[검사] 복부 조영 CT",
        "loc_desc": "서관 2층 CT실 (평일 08:00~18:00)",
        "status": "대기",
        "default_key": "2F_WEST_CT",
        "cat": "CT"
