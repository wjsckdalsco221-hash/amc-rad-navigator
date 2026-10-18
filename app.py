import os
import json
import streamlit as st
import numpy as np
from PIL import Image, ImageDraw
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. Streamlit Secrets 기반 API 키 로드 및 LLM 클라이언트 설정
# ---------------------------------------------------------
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ---------------------------------------------------------
# 2. 기본 레이아웃 및 세션 상태 초기화 (모든 선택값 기본 공란 None 세팅)
# ---------------------------------------------------------
st.set_page_config(
    page_title="서울아산병원 AI 검사실 길 안내 에이전트",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "page" not in st.session_state:
    st.session_state.page = "home"
if "nav_mode" not in st.session_state:
    st.session_state.nav_mode = "exam"
if "selected_exam_idx" not in st.session_state:
    st.session_state.selected_exam_idx = 0

# [1] 내 출발 위치 세션: 초기 실행 시 무조건 공란(None)
if "sel_bldg" not in st.session_state:
    st.session_state.sel_bldg = None
if "sel_floor" not in st.session_state:
    st.session_state.sel_floor = None
if "start_key" not in st.session_state:
    st.session_state.start_key = None
if "loc_error" not in st.session_state:
    st.session_state.loc_error = False

# [2] 검사 외 찾아갈 장소 세션: 초기 실행 시 무조건 공란(None)
if "sel_dest_bldg" not in st.session_state:
    st.session_state.sel_dest_bldg = None
if "sel_dest_floor" not in st.session_state:
    st.session_state.sel_dest_floor = None
if "custom_dest_key" not in st.session_state:
    st.session_state.custom_dest_key = None
if "custom_dest_error" not in st.session_state:
    st.session_state.custom_dest_error = False

# 시간 설정 세션
if "day_type" not in st.session_state:
    st.session_state.day_type = "평일(월~금)"
if "time_str" not in st.session_state:
    st.session_state.time_str = "14:00"

# AI 에이전트 추론 메시지 세션
if "ai_reasoning_msg" not in st.session_state:
    st.session_state.ai_reasoning_msg = ""

# ---------------------------------------------------------
# 3. 반응형 CSS
# ---------------------------------------------------------
if st.session_state.page == "home":
    container_max_width = "480px"
    padding_top = "2.2rem"
else:
    container_max_width = "1200px"
    padding_top = "1.8rem"

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
    padding: 16px 20px;
    border-radius: 14px;
    margin-bottom: 16px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.12);
}}
.app-header h3 {{
    margin: 0;
    font-size: 1.2rem;
    font-weight: 800;
    color: #FFFFFF;
}}
.app-header p {{
    margin: 5px 0 0 0;
    font-size: 0.84rem;
    color: #D2EBEB;
}}
.agent-banner {{
    background: #E8F5E9;
    border: 1.5px solid #2E7D32;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 14px;
    font-size: 0.88rem;
    color: #1B5E20;
    line-height: 1.45;
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
    font-size: 0.84rem;
    padding: 4px 12px;
    border-radius: 20px;
    white-space: nowrap;
    margin-top: 2px;
}}
.exam-info-col {{
    flex: 1;
}}
.exam-title-txt {{
    font-size: 1.02rem;
    font-weight: 800;
    color: #111111;
    margin-bottom: 4px;
}}
.exam-sub-txt {{
    font-size: 0.84rem;
    color: #555555;
    line-height: 1.4;
}}
div.stButton > button {{
    background-color: #2E6930 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 0.5rem 1.0rem !important;
    width: 100% !important;
}}
div.stButton > button:hover {{
    background-color: #235225 !important;
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
.loc-alert-card {{
    background: #FFF8E1;
    border: 2px solid #FFA000;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 14px;
    box-shadow: 0 4px 12px rgba(255, 160, 0, 0.2);
    animation: fadeIn 0.3s ease-in-out;
}}
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(-6px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. 도면 기반 실제 검사실·시설 마스터 좌표 사전
# ---------------------------------------------------------
MAP_ROOMS = {
    # [서관 1층]
    "1F_WEST_BLOOD": {
        "name": "서관 1층 채혈실", "short_name": "서관 채혈실",
        "floor": "1층", "floor_code": "1F", "building": "서관",
        "hours": "평일 06:10~18:30, 토 06:30~13:30 (주간)",
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
        "name": "서관 1층 원무상담실·서관통합창구", "short_name": "서관통합창구",
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

    # [동관 1층]
    "1F_EAST_XRAY": {
        "name": "동관 1층 영상의학과 외래촬영실", "short_name": "영상의학과 외래촬영실",
        "floor": "1층", "floor_code": "1F", "building": "동관",
        "hours": "평일 08:00~17:30 (주간)",
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
        "name": "동관 1층 당뇨병센터·내분비내과", "short_name": "당뇨병센터",
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

    # [신관 1층]
    "1F_NEW_BLOOD": {
        "name": "신관 1층 채혈실", "short_name": "신관 채혈실",
        "floor": "1층", "floor_code": "1F", "building": "신관",
        "hours": "평일 06:10~17:30 (휴일 미운영)",
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

    # [서관 2층]
    "2F_WEST_CT": {
        "name": "서관 2층 CT실 / 투시조영실", "short_name": "서관 CT실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.223, 0.106, 0.307, 0.292), (0.223, 0.319, 0.259, 0.585), (0.267, 0.398, 0.307, 0.585)]
    },
    "2F_WEST_DIAG": {
        "name": "서관 2층 진단검사의학과 (CT/MR 채혈실)", "short_name": "진단검사의학과(CT/MR채혈실)",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "야간/당직 (18:30~익일 06:10)",
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
        "name": "서관 2층 기관지내시경·호흡기검사실", "short_name": "기관지내시경실",
        "floor": "2층", "floor_code": "2F", "building": "서관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.220, 0.875, 0.310, 0.990)]
    },

    # [동관 2층]
    "2F_EAST_XRAY": {
        "name": "동관 2층 영상의학과 일반촬영실", "short_name": "동관 일반촬영실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:00~18:00 (야간/당직)",
        "boxes": [(0.340, 0.275, 0.420, 0.355), (0.340, 0.355, 0.410, 0.556), (0.390, 0.556, 0.410, 0.638)]
    },
    "2F_EAST_MR": {
        "name": "동관 2층 MR실", "short_name": "동관 MR실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 07:30~20:00",
        "boxes": [(0.340, 0.007, 0.435, 0.255)]
    },
    "2F_EAST_ANGIO": {
        "name": "동관 2층 혈관조영실", "short_name": "혈관조영실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.440, 0.007, 0.575, 0.255)]
    },
    "2F_EAST_HEART": {
        "name": "동관 2층 심장검사실", "short_name": "심장검사실",
        "floor": "2층", "floor_code": "2F", "building": "동관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.595, 0.730, 0.655, 0.970)]
    },

    # [신관 2층]
    "2F_NEW_MR": {
        "name": "신관 2층 MR실", "short_name": "신관 MR실",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:00~18:00",
        "boxes": [(0.685, 0.255, 0.815, 0.450)]
    },
    "2F_NEW_XRAY_US": {
        "name": "신관 2층 일반촬영실·초음파실", "short_name": "일반촬영·초음파실",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:00~17:30",
        "boxes": [(0.695, 0.450, 0.815, 0.685)]
    },
    "2F_NEW_EYE": {
        "name": "신관 2층 안과 / 안과검사실", "short_name": "안과·안과검사실",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.895, 0.250, 0.975, 0.685)]
    },
    "2F_NEW_DENTAL": {
        "name": "신관 2층 치과 / 소아치과", "short_name": "치과·소아치과",
        "floor": "2층", "floor_code": "2F", "building": "신관",
        "hours": "평일 08:30~17:30",
        "boxes": [(0.685, 0.035, 0.878, 0.225)]
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
        "sub": "평일 주간(08:00~17:30) 동관 1층 / 그 외 시간 동관 2층",
        "default_key": "1F_EAST_XRAY",
        "cat": "XRAY"
    },
    {
        "title": "[검사] 가정의학과 검체검사 (외래채혈)",
        "sub": "주간(06:10~18:30) 서관 1층 / 야간(18:30~) 서관 2층",
        "default_key": "1F_WEST_BLOOD",
        "cat": "BLOOD"
    },
    {
        "title": "[검사] 복부 조영 CT",
        "sub": "서관 2층 CT실 (평일 08:00~18:00)",
        "default_key": "2F_WEST_CT",
        "cat": "CT"
    },
    {
        "title": "[검사] 뇌 신경 MRI",
        "sub": "신관 2층 신관 MR실 (평일 08:00~18:00)",
        "default_key": "2F_NEW_MR",
        "cat": "MR"
    }
]

# ---------------------------------------------------------
# 5. Action Tool: 의료·시간 라우팅 규칙 엔진
# ---------------------------------------------------------
def resolve_dest_key(exam, start_key, day_type, time_str):
    cat = exam["cat"]
    t_val = int(time_str.replace(":", ""))

    if cat == "XRAY":
        if day_type == "평일(월~금)" and 800 <= t_val <= 1730:
            return "1F_EAST_XRAY"
        else:
            return "2F_EAST_XRAY"

    elif cat == "BLOOD":
        if 610 <= t_val <= 1830:
            return "1F_WEST_BLOOD"
        else:
            return "2F_WEST_DIAG"

    return exam["default_key"]

def determine_next_step(completed_exam_tag, day_type, time_str, is_fasting=False):
    if completed_exam_tag == "XRAY":
        start_key = "1F_EAST_XRAY" if (day_type == "평일(월~금)" and 800 <= int(time_str.replace(":", "")) <= 1730) else "2F_EAST_XRAY"
        next_idx = 1
    elif completed_exam_tag == "BLOOD":
        start_key = "1F_WEST_BLOOD"
        next_idx = 2
    elif completed_exam_tag == "CT":
        start_key = "2F_WEST_CT"
        next_idx = 3
    elif completed_exam_tag == "MR":
        start_key = "2F_NEW_MR"
        next_idx = 0
    else:
        start_key = "1F_EAST_XRAY"
        next_idx = 1

    target_exam = PATIENT_EXAMS[next_idx]
    dest_key = resolve_dest_key(target_exam, start_key, day_type, time_str)

    return {
        "start_key": start_key,
        "selected_exam_idx": next_idx,
        "dest_key": dest_key,
        "dest_name": MAP_ROOMS[dest_key]["name"]
    }

# ---------------------------------------------------------
# 6. 순수 Gemini LLM Agent 엔진
# ---------------------------------------------------------
def run_ai_agent(user_query, day_type, time_str):
    if not client:
        st.error("⚠️ Streamlit Cloud의 Secrets에 GEMINI_API_KEY가 등록되지 않았습니다.")
        return "API 키 설정을 확인해 주세요.", False

    system_prompt = f"""
    당신은 서울아산병원 외래 환자 길 안내 전문 AI 에이전트입니다.
    현재 원내 시각은 [{day_type} {time_str}]입니다.

    환자의 입력 문장을 임상적으로 분석하여 다음 정보를 반드시 지정된 JSON 규격으로만 응답하세요:
    1. completed_exam: 방금 마친 검사 코드 (반드시 "XRAY", "BLOOD", "CT", "MR" 중 하나 선택)
    2. is_fasting: 환자가 금식 중이거나 배고픔을 호소하는지 여부 (true / false)
    3. thought: 환자의 상황 파악 및 다음 동선 추천 사유를 한 줄 요약
    4. reply: 환자에게 건넬 친절하고 명확한 안내 멘트 (1~2문장)

    [출력 JSON 스키마]:
    {{
        "completed_exam": "XRAY" | "BLOOD" | "CT" | "MR",
        "is_fasting": boolean,
        "thought": "string",
        "reply": "string"
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_query,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.0
            )
        )

        parsed = json.loads(response.text)
        comp_exam = parsed.get("completed_exam", "XRAY")
        is_fast = parsed.get("is_fasting", False)

        tool_res = determine_next_step(comp_exam, day_type, time_str, is_fast)

        st.session_state.start_key = tool_res["start_key"]
        s_meta = MAP_ROOMS[tool_res["start_key"]]
        st.session_state.sel_bldg = s_meta["building"]
        st.session_state.sel_floor = s_meta["floor"]
        st.session_state.selected_exam_idx = tool_res["selected_exam_idx"]
        st.session_state.nav_mode = "exam"
        st.session_state.loc_error = False

        guide_msg = parsed.get("reply", f"다음 순서인 {tool_res['dest_name']}(으)로 이동하시면 됩니다.")
        st.session_state.ai_reasoning_msg = f"🤖 **AI Agent Reasoning**: {parsed.get('thought', '선행 검사 완료 인지')} ➔ **{tool_res['dest_name']}** 최적 경로 배정"
        return guide_msg, True

    except Exception as e:
        st.error(f"⚠️ Gemini API 호출 중 오류가 발생했습니다: {str(e)}")
        return "API 응답을 처리하지 못했습니다. 네트워크 상태 및 API 키 유효성을 확인해 주세요.", False

# ---------------------------------------------------------
# 7. 도면 탐색 및 그래픽 정밀 렌더러 (방 관통 방지 복도 라우팅 엔진)
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

    red_res = fill_box(red_key, [255, 200, 200])
    green_res = fill_box(green_key, [188, 245, 200])

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
    corridor_y = int(H * 0.672) if floor_code == "1F" else int(H * 0.665)

    # -------------------------------------------------------------
    # 방 관통 방지: 검사실별 실제 보행자 복도 진입 경로 계산기
    # -------------------------------------------------------------
    def get_corridor_access_path(key, center):
        cx, cy = center
        # 신관 2층 MR실: 일반촬영실 방을 관통하지 않고 우측 수직 복도(신관 엘리베이터 앞)를 경유
        if key == "2F_NEW_MR":
            aisle_x = int(0.855 * W)
            return [(aisle_x, corridor_y), (aisle_x, cy), (cx, cy)]
        # 신관 2층 치과: 우측 수직 복도를 타고 최상단 진입
        elif key == "2F_NEW_DENTAL":
            aisle_x = int(0.855 * W)
            return [(aisle_x, corridor_y), (aisle_x, cy), (cx, cy)]
        # 동관 2층 MR실: 일반촬영실을 관통하지 않고 동관 엘리베이터 옆 수직 통로를 경유
        elif key == "2F_EAST_MR":
            aisle_x = int(0.445 * W)
            return [(aisle_x, corridor_y), (aisle_x, cy), (cx, cy)]
        # 일반 검사실: 메인 가로 복도에서 곧장 해당 검사실 입구로 진입
        else:
            return [(cx, corridor_y), (cx, cy)]

    # 1. 동일 층 이동 경로
    if mode == "SAME" and red_res and green_res and red_key != green_key:
        sx, sy = red_res[0]
        dx, dy = green_res[0]
        s_path = get_corridor_access_path(red_key, (sx, sy))
        d_path = get_corridor_access_path(green_key, (dx, dy))

        line_pts = [(sx, sy)]
        if len(s_path) > 2:
            line_pts.append(s_path[1])
        line_pts.append(s_path[0])
        line_pts.append(d_path[0])
        if len(d_path) > 2:
            line_pts.append(d_path[1])
        line_pts.append((dx, dy))

        draw.line(line_pts, fill=(0, 102, 102), width=lw)
        draw.ellipse([sx-r_rad, sy-r_rad, sx+r_rad, sy+r_rad], fill=(217, 48, 37), outline=(255, 255, 255), width=2)
        draw.ellipse([dx-r_rad, dy-r_rad, dx+r_rad, dy+r_rad], fill=(30, 142, 62), outline=(255, 255, 255), width=2)

    # 2. 내 위치 -> 엘리베이터 이동 경로
    elif mode == "TO_ELEV" and red_res and elev_center:
        sx, sy = red_res[0]
        ex, ey = elev_center
        s_path = get_corridor_access_path(red_key, (sx, sy))

        line_pts = [(sx, sy)]
        if len(s_path) > 2:
            line_pts.append(s_path[1])
        line_pts.append(s_path[0])
        line_pts.append((ex, corridor_y))
        line_pts.append((ex, ey))

        draw.line(line_pts, fill=(217, 48, 37), width=lw)
        draw.ellipse([sx-r_rad, sy-r_rad, sx+r_rad, sy+r_rad], fill=(217, 48, 37), outline=(255, 255, 255), width=2)
        draw.ellipse([ex-r_rad, ey-r_rad, ex+r_rad, ey+r_rad], fill=(255, 140, 0), outline=(255, 255, 255), width=2)

    # 3. 엘리베이터 하차 -> 목적지 이동 경로 (방 관통 방지 적용!)
    elif mode == "FROM_ELEV" and elev_center and green_res:
        ex, ey = elev_center
        dx, dy = green_res[0]
        d_path = get_corridor_access_path(green_key, (dx, dy))

        line_pts = [(ex, ey), (ex, corridor_y), d_path[0]]
        if len(d_path) > 2:
            line_pts.append(d_path[1])
        line_pts.append((dx, dy))

        draw.line(line_pts, fill=(30, 142, 62), width=lw)
        draw.ellipse([ex-r_rad, ey-r_rad, ex+r_rad, ey+r_rad], fill=(255, 140, 0), outline=(255, 255, 255), width=2)
        draw.ellipse([dx-r_rad, dy-r_rad, dx+r_rad, dy+r_rad], fill=(30, 142, 62), outline=(255, 255, 255), width=2)

    return pil_img

# =========================================================
# PAGE 1: 홈 화면 (검사 일정 & AI 에이전트 질문 & 위치 선택)
# =========================================================
if st.session_state.page == "home":
    st.markdown("""
    <div class="app-header">
        <h3>🏥 서울아산병원 AI 검사실 길 안내 에이전트</h3>
        <p>자연어로 질문하시거나 아래에서 위치를 지정하시면 최적 동선 도면을 안내합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    # 1) AI Agent 대화형 질의 섹션
    st.markdown("#### 💬 AI 에이전트에게 음성/텍스트로 물어보기")
    agent_query = st.text_input(
        "질문 입력:",
        placeholder="예: x-ray 검사가 끝났는데, 다음은 어디로 가야해?",
        label_visibility="collapsed"
    )
    
    col_ask1, col_ask2 = st.columns([2.0, 1.0])
    with col_ask1:
        btn_ask = st.button("🤖 AI에게 다음 길 물어보기", use_container_width=True)
    with col_ask2:
        btn_preset = st.button("💡 'X-ray 완료' 질의 입력", use_container_width=True)
        if btn_preset:
            agent_query = "x-ray 검사가 끝났는데, 다음은 어디로 가야해"

    if (btn_ask or btn_preset) and agent_query:
        with st.spinner("AI 에이전트(Gemini)가 최적 검사실 및 맞춤 경로를 추론 중입니다..."):
            reply_text, success = run_ai_agent(agent_query, st.session_state.day_type, st.session_state.time_str)
        if success:
            st.success(reply_text)
            st.session_state.page = "map"
            st.rerun()

    st.markdown("---")

    # 2) 나의 검사 일정 목록
    st.markdown("#### 📅 나의 검사 일정")
    st.caption("안내를 원하시는 검사 우측의 **[길안내]**를 직접 누르셔도 됩니다.")

    for idx, ex in enumerate(PATIENT_EXAMS):
        assigned_key = resolve_dest_key(ex, st.session_state.start_key, st.session_state.day_type, st.session_state.time_str)
        assigned_meta = MAP_ROOMS[assigned_key]

        if ex["cat"] in ["XRAY", "BLOOD"]:
            sub_display = f"{assigned_meta['name']} ({assigned_meta['building']} {assigned_meta['floor']}) <span style='color:#005C5C; font-weight:700;'>[{st.session_state.time_str} 배정]</span>"
        else:
            sub_display = f"{assigned_meta['name']} ({assigned_meta['building']} {assigned_meta['floor']})"

        with st.container():
            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; padding:12px; margin-bottom:6px;">
                <div class="exam-row-wrap">
                    <div class="exam-pill">검사</div>
                    <div class="exam-info-col">
                        <div class="exam-title-txt">{ex['title']}</div>
                        <div class="exam-sub-txt">{sub_display}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🧭 길안내", key=f"btn_go_map_{idx}", use_container_width=True):
                if not st.session_state.start_key:
                    st.session_state.loc_error = True
                    st.rerun()
                else:
                    st.session_state.loc_error = False
                    st.session_state.selected_exam_idx = idx
                    st.session_state.nav_mode = "exam"
                    st.session_state.ai_reasoning_msg = f"수동 선택: **{ex['title']}** 경로 안내"
                    st.session_state.page = "map"
                    st.rerun()

    st.markdown("---")

    # 3) 현재 내 위치 수동 선택란 (초기 공란 유지 및 자동 스크롤)
    st.markdown('<div id="loc_section_anchor"></div>', unsafe_allow_html=True)

    if st.session_state.loc_error and not st.session_state.start_key:
        st.markdown("""
        <div class="loc-alert-card">
            <div style="font-weight:800; font-size:1.02rem; color:#B71C1C; display:flex; align-items:center; gap:6px;">
                📍 현재 계신 내 위치를 먼저 선택해 주세요!
            </div>
            <div style="font-size:0.86rem; color:#4E342E; margin-top:5px; line-height:1.45;">
                정확한 길안내를 위해 아래에서 <b>[관 선택] ➔ [층 선택] ➔ [위치 선택]</b>을 완료하신 후 길안내를 눌러주세요.
            </div>
        </div>
        <script>
            var target = window.parent.document.getElementById('loc_section_anchor') || document.getElementById('loc_section_anchor');
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        </script>
        """, unsafe_allow_html=True)
        st.toast("📍 현재 내 위치를 먼저 선택해 주세요!", icon="⚠️")

    st.markdown("#### 📍 현재 내 위치 수동 선택")

    bldg_options = ["서관", "동관", "신관"]
    floor_options = ["1층", "2층"]

    loc_col1, loc_col2, loc_col3 = st.columns([1.0, 0.9, 1.5])

    with loc_col1:
        sel_bldg_idx = bldg_options.index(st.session_state.sel_bldg) if st.session_state.sel_bldg in bldg_options else None
        new_bldg = st.selectbox(
            "관 선택",
            options=bldg_options,
            index=sel_bldg_idx,
            placeholder="관 선택",
            key="sb_start_bldg"
        )
        if new_bldg != st.session_state.sel_bldg:
            st.session_state.sel_bldg = new_bldg
            st.session_state.start_key = None
            st.rerun()

    with loc_col2:
        sel_floor_idx = floor_options.index(st.session_state.sel_floor) if st.session_state.sel_floor in floor_options else None
        new_floor = st.selectbox(
            "층 선택",
            options=floor_options,
            index=sel_floor_idx,
            placeholder="층 선택",
            key="sb_start_floor"
        )
        if new_floor != st.session_state.sel_floor:
            st.session_state.sel_floor = new_floor
            st.session_state.start_key = None
            st.rerun()

    if st.session_state.sel_bldg and st.session_state.sel_floor:
        filtered_start_keys = [
            k for k, v in MAP_ROOMS.items()
            if v["building"] == st.session_state.sel_bldg and v["floor"] == st.session_state.sel_floor
        ]
    else:
        filtered_start_keys = []

    with loc_col3:
        def_start_idx = filtered_start_keys.index(st.session_state.start_key) if st.session_state.start_key in filtered_start_keys else None
        new_room = st.selectbox(
            "위치 선택",
            options=filtered_start_keys,
            format_func=lambda k: MAP_ROOMS[k]["short_name"],
            index=def_start_idx,
            placeholder="위치 선택" if filtered_start_keys else "관·층 먼저 선택",
            key="sb_start_room"
        )
        if new_room != st.session_state.start_key:
            st.session_state.start_key = new_room
            if new_room:
                st.session_state.loc_error = False
            st.rerun()

    st.markdown("---")

    # 4) 검사 외 찾아갈 장소 선택 (초기 공란 유지 및 미선택 방어/스크롤 연동)
    st.markdown('<div id="dest_section_anchor"></div>', unsafe_allow_html=True)

    if st.session_state.custom_dest_error and not st.session_state.custom_dest_key:
        st.markdown("""
        <div class="loc-alert-card">
            <div style="font-weight:800; font-size:1.02rem; color:#B71C1C; display:flex; align-items:center; gap:6px;">
                🎯 찾아가실 목적지(검사 외 장소)를 먼저 선택해 주세요!
            </div>
            <div style="font-size:0.86rem; color:#4E342E; margin-top:5px; line-height:1.45;">
                아래에서 <b>[관 선택] ➔ [층 선택] ➔ [위치 선택]</b>을 모두 완료하신 후 길안내 시작을 눌러주세요.
            </div>
        </div>
        <script>
            var target = window.parent.document.getElementById('dest_section_anchor') || document.getElementById('dest_section_anchor');
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        </script>
        """, unsafe_allow_html=True)
        st.toast("🎯 찾아가실 목적지를 먼저 선택해 주세요!", icon="⚠️")

    st.markdown("#### 🧭 검사 외 찾아갈 장소 선택")
    st.caption("※ 검사 일정 외 편의시설이나 다른 검사실을 찾으실 때만 선택해 주세요.")

    dest_col1, dest_col2, dest_col3 = st.columns([1.0, 0.9, 1.5])

    with dest_col1:
        sel_dest_bldg_idx = bldg_options.index(st.session_state.sel_dest_bldg) if st.session_state.sel_dest_bldg in bldg_options else None
        new_dest_bldg = st.selectbox(
            "관 선택",
            options=bldg_options,
            index=sel_dest_bldg_idx,
            placeholder="관 선택",
            key="sb_dest_bldg"
        )
        if new_dest_bldg != st.session_state.sel_dest_bldg:
            st.session_state.sel_dest_bldg = new_dest_bldg
            st.session_state.custom_dest_key = None
            st.rerun()

    with dest_col2:
        sel_dest_floor_idx = floor_options.index(st.session_state.sel_dest_floor) if st.session_state.sel_dest_floor in floor_options else None
        new_dest_floor = st.selectbox(
            "층 선택",
            options=floor_options,
            index=sel_dest_floor_idx,
            placeholder="층 선택",
            key="sb_dest_floor"
        )
        if new_dest_floor != st.session_state.sel_dest_floor:
            st.session_state.sel_dest_floor = new_dest_floor
            st.session_state.custom_dest_key = None
            st.rerun()

    if st.session_state.sel_dest_bldg and st.session_state.sel_dest_floor:
        filtered_dest_keys = [
            k for k, v in MAP_ROOMS.items()
            if v["building"] == st.session_state.sel_dest_bldg and v["floor"] == st.session_state.sel_dest_floor
        ]
    else:
        filtered_dest_keys = []

    with dest_col3:
        def_dest_idx = filtered_dest_keys.index(st.session_state.custom_dest_key) if st.session_state.custom_dest_key in filtered_dest_keys else None
        new_dest_room = st.selectbox(
            "위치 선택",
            options=filtered_dest_keys,
            format_func=lambda k: MAP_ROOMS[k]["short_name"],
            index=def_dest_idx,
            placeholder="위치 선택" if filtered_dest_keys else "관·층 먼저 선택",
            key="sb_dest_room"
        )
        if new_dest_room != st.session_state.custom_dest_key:
            st.session_state.custom_dest_key = new_dest_room
            if new_dest_room:
                st.session_state.custom_dest_error = False
            st.rerun()

    if st.button("🧭 이 장소로 길안내 시작", use_container_width=True, key="btn_go_custom"):
        if not st.session_state.start_key:
            st.session_state.loc_error = True
            st.rerun()
        elif not st.session_state.custom_dest_key:
            st.session_state.custom_dest_error = True
            st.rerun()
        else:
            st.session_state.loc_error = False
            st.session_state.custom_dest_error = False
            st.session_state.nav_mode = "custom"
            st.session_state.ai_reasoning_msg = f"수동 선택: 목적지 **{MAP_ROOMS[st.session_state.custom_dest_key]['name']}** 이동"
            st.session_state.page = "map"
            st.rerun()

    # 5) 시뮬레이션용 시간 및 요일 프리셋
    with st.expander("⏰ 현재 요일 및 시간 변경 (운영시간 테스트)", expanded=False):
        x_c1, x_c2 = st.columns(2)
        if x_c1.button("🕒 평일 15:00 (X-ray ➔ 동관 1층)", use_container_width=True, key="btn_xray_day"):
            st.session_state.day_type = "평일(월~금)"
            st.session_state.time_str = "15:00"
            st.rerun()
        if x_c2.button("🌙 평일 18:00 (X-ray ➔ 동관 2층)", use_container_width=True, key="btn_xray_night"):
            st.session_state.day_type = "평일(월~금)"
            st.session_state.time_str = "18:00"
            st.rerun()

# =========================================================
# PAGE 2: 맞춤형 지도 전용 화면
# =========================================================
elif st.session_state.page == "map":
    b_col1, b_col2 = st.columns([1.2, 2.8])
    with b_col1:
        if st.button("⬅️ 검사 목록 및 질문으로 돌아가기", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

    start_key = st.session_state.start_key if st.session_state.start_key else "1F_EAST_XRAY"

    if st.session_state.nav_mode == "custom":
        dest_key = st.session_state.custom_dest_key
    else:
        target_exam = PATIENT_EXAMS[st.session_state.selected_exam_idx]
        dest_key = resolve_dest_key(target_exam, start_key, st.session_state.day_type, st.session_state.time_str)

    s_meta = MAP_ROOMS[start_key]
    d_meta = MAP_ROOMS[dest_key]
    is_diff_floor = (s_meta["floor_code"] != d_meta["floor_code"])
    elev_info = ELEVATORS[s_meta["building"]]

    if st.session_state.ai_reasoning_msg:
        st.markdown(f"<div class='agent-banner'>{st.session_state.ai_reasoning_msg}</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="dest-banner">
        <div style="font-size:0.86rem; font-weight:700;">🟢 실시간 맞춤 길안내 목적지 ({st.session_state.day_type} {st.session_state.time_str} 기준 자동 매칭)</div>
        <div style="font-size:1.3rem; font-weight:800; margin:3px 0;">{d_meta['name']} ({d_meta['building']} {d_meta['floor']})</div>
        <div style="font-size:0.9rem; color:#333; margin-top:4px;">
            • <b>내 출발 위치</b>: [{s_meta['building']} {s_meta['floor']}] {s_meta['name']}<br>
            • <b>운영시간</b>: {d_meta['hours']}<br>
            • <b>이동 안내</b>: 중앙 복도 메인 동선을 따라 연한 녹색 구역으로 이동해 주세요.
        </div>
    </div>
    """, unsafe_allow_html=True)

    leg_c1, leg_c2, leg_c3 = st.columns(3)
    leg_c1.markdown("🔴 **연한 빨간색**: 내 출발 위치")
    leg_c2.markdown("🟢 **연한 녹색**: 가야 할 목적지")
    leg_c3.markdown("🟠 **주황색 사각 박스**: 탑승/하차 엘리베이터")

    path_2f = find_image("2F")
    path_1f = find_image("1F")

    if not path_2f or not path_1f:
        st.warning("⚠️ `서동신_1층_지도.png` 및 `서동신_2층_지도.png` 파일이 지정된 폴더에 있는지 확인해 주세요.")
    else:
        arr_2f = clean_base_map(path_2f, "2F")
        arr_1f = clean_base_map(path_1f, "1F")

        if is_diff_floor:
            st.markdown(f"<div class='map-step-badge'>1단계 지도 : {s_meta['floor']} [{elev_info['name']}]로 이동</div>", unsafe_allow_html=True)
            base_start = arr_2f if s_meta["floor_code"] == "2F" else arr_1f
            elev_start_box = elev_info[f"{s_meta['floor_code']}_box"]
            img_s1 = draw_colored_map(
                base_start, red_key=start_key, elev_box=elev_start_box, mode="TO_ELEV", floor_code=s_meta["floor_code"]
            )
            st.image(img_s1, use_container_width=True)

            st.markdown(f"<div class='map-step-badge'>2단계 지도 : {d_meta['floor']} 하차 ➔ [{d_meta['short_name']}](연한 녹색) 도착</div>", unsafe_allow_html=True)
            base_dest = arr_2f if d_meta["floor_code"] == "2F" else arr_1f
            elev_dest_box = elev_info[f"{d_meta['floor_code']}_box"]
            img_s2 = draw_colored_map(
                base_dest, green_key=dest_key, elev_box=elev_dest_box, mode="FROM_ELEV", floor_code=d_meta["floor_code"]
            )
            st.image(img_s2, use_container_width=True)
        else:
            st.markdown(f"<div class='map-step-badge'>{s_meta['floor']} 동선 지도 : [{s_meta['short_name']}](빨강) ➔ [{d_meta['short_name']}](녹색)</div>", unsafe_allow_html=True)
            base_same = arr_2f if s_meta["floor_code"] == "2F" else arr_1f
            img_same = draw_colored_map(
                base_same, red_key=start_key, green_key=dest_key, mode="SAME", floor_code=s_meta["floor_code"]
            )
            st.image(img_same, use_container_width=True)
