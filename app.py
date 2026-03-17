import streamlit as st
import pandas as pd
import math
import os
from datetime import datetime

# 1. 페이지 기본 설정
st.set_page_config(page_title="테니스 텐션 예측기", page_icon="🎾", layout="wide")
st.title("🎾 테니스 라켓 & 스트링 \n통합 텐션 예측기")
st.caption("HEAD CPI 알고리즘 & 테니스웨어하우스 데이터 기반 (v16 로직 적용)")

# --- 데이터 저장/불러오기 설정 ---
LOG_FILE = 'user_tension_log.csv'
CUSTOM_RACKET_FILE = 'custom_rackets.csv' 

def save_log(old_r, old_s, new_r, new_s, tension, memo):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_data = pd.DataFrame([{
        "날짜": now,
        "기존 라켓": old_r,
        "기존 스트링": old_s,
        "바꾼 라켓": new_r,
        "바꾼 스트링": new_s,
        "작업 텐션(lbs)": round(tension, 1),
        "사용자 메모": memo
    }])
    if os.path.exists(LOG_FILE):
        existing_data = pd.read_csv(LOG_FILE)
        updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        updated_data.to_csv(LOG_FILE, index=False, encoding='utf-8-sig')
    else:
        new_data.to_csv(LOG_FILE, index=False, encoding='utf-8-sig')

def load_logs():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    return pd.DataFrame()

def save_custom_racket(name, size, pattern, ra, tip, mid, shaft, weight, bal):
    avg_thick = round((tip * 0.3) + (mid * 0.5) + (shaft * 0.2), 2)
    m, c = map(int, pattern.split('x'))
    pattern_math = 360 - (m * c)
    cpi = round(300 + (size - 100) * 30 + (ra - 62) * 30 + (avg_thick - 23) * 20 + (weight - 326) * -5 + (bal - 32.5) * 40 + pattern_math * 3, 0)
    
    new_racket = pd.DataFrame([{
        '라켓이름': name,
        '헤드사이즈': size,
        '스트링패턴': pattern,
        '강성(RA)': ra,
        '상단(mm)': tip,
        '중단(mm)': mid,
        '하단(mm)': shaft,
        '스트링무게(g)': weight,
        '밸런스(cm)': bal,
        '프레임_가중평균(mm)': avg_thick,
        '종합파워인덱스(HEAD_CPI맞춤)': cpi,
        '참고_실제CPI': '사용자 직접추가'
    }])

    if os.path.exists(CUSTOM_RACKET_FILE):
        existing = pd.read_csv(CUSTOM_RACKET_FILE)
        updated = pd.concat([existing, new_racket], ignore_index=True)
        updated.to_csv(CUSTOM_RACKET_FILE, index=False, encoding='utf-8-sig')
    else:
        new_racket.to_csv(CUSTOM_RACKET_FILE, index=False, encoding='utf-8-sig')

# 2. 데이터 불러오기
@st.cache_data
def load_data():
    file_name = '라켓_스트링_통합예측기_v16(가중치상향조정).xlsx'
    try:
        string_df = pd.read_excel(file_name, sheet_name='스트링DB')
        racket_df = pd.read_excel(file_name, sheet_name='라켓DB')
        racket_df = racket_df.dropna(subset=['라켓이름'])
        
        if os.path.exists(CUSTOM_RACKET_FILE):
            custom_df = pd.read_csv(CUSTOM_RACKET_FILE)
            racket_df = pd.concat([racket_df, custom_df], ignore_index=True)
            
        return string_df, racket_df
    except Exception as e:
        st.error(f"엑셀 파일을 찾을 수 없거나 오류가 발생했습니다: {e}")
        return pd.DataFrame(), pd.DataFrame()

string_df, racket_df = load_data()

if not string_df.empty and not racket_df.empty:
    tab1, tab2, tab3 = st.tabs(["🎾 텐션 예측 및 기록", "📖 나의 텐션 히스토리", "🛠️ 새 라켓 실시간 추가"])

    with tab1:
        col_main1, col_main2 = st.columns(2)
        
        with col_main1:
            st.header("1️⃣ 기존 장비 세팅")
            old_racket_name = st.selectbox("현재 라켓", racket_df['라켓이름'].tolist())
            old_string_name = st.selectbox("현재 스트링", string_df['String'].tolist())

            st.subheader("기준 텐션 (둘 중 하나만 입력)")
            old_tension_work = st.number_input("기존 작업 텐션 (lbs)", min_value=0.0, max_value=80.0, value=52.0, step=1.0)
            old_tension_meter = st.number_input("최고였던 텐션미터 수치", min_value=0.0, max_value=100.0, value=0.0, step=0.1)

        with col_main2:
            st.header("2️⃣ 바꿀 장비 세팅")
            new_racket_name = st.selectbox("바꿀 라켓", racket_df['라켓이름'].tolist(), index=2)
            new_string_name = st.selectbox("바꿀 스트링", string_df['String'].tolist(), index=5)

        st.divider()

        if 'final_tension' not in st.session_state:
            st.session_state.final_tension = 0.0

        if st.button("🚀 추천 텐션 계산하기", type="primary", use_container_width=True):
            old_r = racket_df[racket_df['라켓이름'] == old_racket_name].iloc[0]
            old_s = string_df[string_df['String'] == old_string_name].iloc[0]
            new_r = racket_df[racket_df['라켓이름'] == new_racket_name].iloc[0]
            new_s = string_df[string_df['String'] == new_string_name].iloc[0]

            if old_tension_meter > 0:
                ref_t = (old_tension_meter * 0.65) / (1 - old_s['Tension Loss (%)'] / 100)
            else:
                ref_t = old_tension_work

            # v16 가중치 (v15 대비 20% 상향)
            cpi_adj = (new_r['종합파워인덱스(HEAD_CPI맞춤)'] - old_r['종합파워인덱스(HEAD_CPI맞춤)']) * 0.0126
            loss_adj = (new_s['Tension Loss (%)'] - old_s['Tension Loss (%)']) * 0.153
            stiff_adj = (old_s['Stiffness (lb/in)'] - new_s['Stiffness (lb/in)']) * 0.0306
            thick_adj = (old_s['두께(mm)'] - new_s['두께(mm)']) * 15.3

            st.session_state.final_tension = ref_t + loss_adj + stiff_adj + thick_adj + cpi_adj

            st.header("🎯 최종 추천 작업 텐션")
            st.metric(label="계산된 텐션 (lbs)", value=f"{round(st.session_state.final_tension, 1)} lbs", delta=f"{round(st.session_state.final_tension - ref_t, 1)} lbs (기존대비)")
            
            st.subheader("💡 장비 변경 체감 조언")
            cpi_diff = new_r['종합파워인덱스(HEAD_CPI맞춤)'] - old_r['종합파워인덱스(HEAD_CPI맞춤)']
            stiff_diff = new_s['Stiffness (lb/in)'] - old_s['Stiffness (lb/in)']
            
            advice_text = ""
            if cpi_diff >= 20: advice_text += "▶ **[라켓 파워 증가]** 이전보다 공이 잘 나갑니다(비거리 증가).\n\n"
            elif cpi_diff <= -20: advice_text += "▶ **[라켓 파워 감소]** 이전보다 덜 나가며 컨트롤이 강조됩니다.\n\n"
            else: advice_text += "▶ **[라켓 파워 유지]** 체감 라켓 파워는 기존과 비슷한 수준입니다.\n\n"
            
            if stiff_diff >= 15: advice_text += "▶ **[타구감 더 딱딱함]** 새 스트링이 단단하여 타구감이 다소 딱딱해집니다.\n\n"
            elif stiff_diff <= -15: advice_text += "▶ **[타구감 더 부드러움]** 새 스트링이 푹신하고 안락한 느낌을 줍니다.\n\n"
            else: advice_text += "▶ **[타구감 유지]** 스트링에서 체감되는 단단함은 기존과 비슷합니다.\n\n"

            if new_s['두께(mm)'] < old_s['두께(mm)']: advice_text += "▶ **[스핀/반발력 UP]** 스트링이 얇아져서 스핀과 반발력이 미세하게 상승합니다."
            elif new_s['두께(mm)'] > old_s['두께(mm)']: advice_text += "▶ **[내구성/컨트롤 UP]** 스트링이 두꺼워져 내구성과 묵직한 컨트롤에 유리합니다."
            else: advice_text += "▶ **[두께 유지]** 스트링 게이지(두께)는 동일합니다."

            st.success(advice_text)

        if st.session_state.final_tension > 0:
            st.divider()
            st.subheader("📝 사용자 코멘트 및 기록 저장")
            user_note = st.text_area("예측된 텐션으로 작업 후 실제 쳐본 느낌을 기록해두세요.", height=100)
            
            if st.button("💾 이 세팅과 메모 저장하기"):
                save_log(old_racket_name, old_string_name, new_racket_name, new_string_name, st.session_state.final_tension, user_note)
                st.toast('성공적으로 기록되었습니다! [나의 텐션 히스토리] 탭에서 확인하세요.', icon='🎉')

    with tab2:
        st.header("📖 나의 텐션 히스토리 (수정/삭제 가능)")
        logs_df = load_logs()
        
        if logs_df.empty:
            st.info("아직 저장된 기록이 없습니다. 예측기에서 첫 번째 메모를 남겨보세요!")
        else:
            logs_df = logs_df.sort_values(by="날짜", ascending=False).reset_index(drop=True)
            edited_df = st.data_editor(logs_df, num_rows="dynamic", use_container_width=True)
            
            col_save, col_down = st.columns(2)
            with col_save:
                if st.button("🔄 수정한 기록 덮어쓰기 (저장)", type="primary"):
                    edited_df.to_csv(LOG_FILE, index=False, encoding='utf-8-sig')
                    st.success("수정된 기록이 성공적으로 저장되었습니다!")
            with col_down:
                csv = edited_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 내 기록 엑셀(CSV)로 다운로드", data=csv, file_name='my_tension_history.csv', mime='text/csv')

    with tab3:
        st.header("🛠️ 새 라켓 실시간 추가하기")
        st.markdown("테니스 웨어하우스 스펙을 바탕으로 새로운 라켓을 추가하면, 파워 인덱스(CPI)가 자동 계산되어 즉시 드롭다운 목록에 반영됩니다.")
        
        with st.form("add_racket_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                r_name = st.text_input("라켓 이름 (예: 요넥스 브이코어 100 2023)")
                r_size = st.number_input("헤드사이즈 (sq in)", min_value=85, max_value=120, value=100)
                r_pattern = st.selectbox("스트링 패턴", ["16x19", "18x20", "16x20", "18x19", "16x18", "14x18"])
            with c2:
                r_ra = st.number_input("강성 (RA)", min_value=40, max_value=85, value=65)
                r_weight = st.number_input("스트링 장착 후 무게 (g)", min_value=250.0, max_value=360.0, value=318.0, step=1.0)
                r_bal = st.number_input("스트링 장착 후 밸런스 (cm)", min_value=30.0, max_value=36.0, value=33.0, step=0.1)
            with c3:
                r_tip = st.number_input("상단 두께 (Tip) mm", min_value=15.0, max_value=30.0, value=23.0, step=0.1)
                r_mid = st.number_input("중단 두께 (Mid) mm", min_value=15.0, max_value=30.0, value=26.0, step=0.1)
                r_shaft = st.number_input("하단 두께 (Shaft) mm", min_value=15.0, max_value=30.0, value=23.0, step=0.1)
            
            submitted = st.form_submit_button("저장 및 데이터베이스 업데이트", use_container_width=True)
            
            if submitted:
                if r_name.strip() == "":
                    st.error("❗ 라켓 이름을 반드시 입력해주세요.")
                else:
                    save_custom_racket(r_name, r_size, r_pattern, r_ra, r_tip, r_mid, r_shaft, r_weight, r_bal)
                    st.cache_data.clear()
                    st.success(f"🎉 '{r_name}' 라켓이 성공적으로 추가되었습니다! 파워 인덱스가 자동 계산되었습니다.")
                    st.rerun()
