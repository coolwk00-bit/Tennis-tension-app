import streamlit as st
import pandas as pd
import math
import os
from datetime import datetime

# 1. 페이지 기본 설정
st.set_page_config(page_title="테니스 텐션 예측기", page_icon="🎾", layout="centered")
st.title("🎾 테니스 라켓 & 스트링 통합 텐션 예측기")
st.caption("HEAD CPI 알고리즘 & 테니스웨어하우스 데이터 기반 (v15 로직 적용)")

# --- 데이터 저장/불러오기 함수 설정 ---
LOG_FILE = 'user_tension_log.csv'

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

# 2. 엑셀 데이터 불러오기
@st.cache_data
def load_data():
    file_name = '라켓_스트링_통합예측기_v15(가중치최종조정).xlsx'
    try:
        string_df = pd.read_excel(file_name, sheet_name='스트링DB')
        racket_df = pd.read_excel(file_name, sheet_name='라켓DB')
        racket_df = racket_df.dropna(subset=['라켓이름'])
        return string_df, racket_df
    except Exception as e:
        st.error(f"엑셀 파일을 찾을 수 없거나 오류가 발생했습니다: {e}")
        return pd.DataFrame(), pd.DataFrame()

string_df, racket_df = load_data()

if not string_df.empty and not racket_df.empty:
    tab1, tab2 = st.tabs(["🎾 텐션 예측 및 기록", "📖 나의 텐션 히스토리 (수정 가능)"])

    # --- 첫 번째 탭: 예측 및 기록 ---
    with tab1:
        st.header("1️⃣ 기존 장비 세팅")
        col1, col2 = st.columns(2)
        with col1:
            old_racket_name = st.selectbox("현재 라켓", racket_df['라켓이름'].tolist())
        with col2:
            old_string_name = st.selectbox("현재 스트링", string_df['String'].tolist())

        st.subheader("기준 텐션 입력 (둘 중 하나만 입력)")
        col3, col4 = st.columns(2)
        with col3:
            old_tension_work = st.number_input("기존 작업 텐션 (lbs)", min_value=0.0, max_value=80.0, value=52.0, step=1.0)
        with col4:
            old_tension_meter = st.number_input("최고였던 텐션미터 수치", min_value=0.0, max_value=100.0, value=0.0, step=0.1)

        st.divider()

        st.header("2️⃣ 바꿀 장비 세팅")
        col5, col6 = st.columns(2)
        with col5:
            new_racket_name = st.selectbox("바꿀 라켓", racket_df['라켓이름'].tolist(), index=2)
        with col6:
            new_string_name = st.selectbox("바꿀 스트링", string_df['String'].tolist(), index=5)

        st.divider()

        if 'final_tension' not in st.session_state:
            st.session_state.final_tension = 0.0

        if st.button("추천 텐션 계산하기", type="primary"):
            old_r = racket_df[racket_df['라켓이름'] == old_racket_name].iloc[0]
            old_s = string_df[string_df['String'] == old_string_name].iloc[0]
            new_r = racket_df[racket_df['라켓이름'] == new_racket_name].iloc[0]
            new_s = string_df[string_df['String'] == new_string_name].iloc[0]

            if old_tension_meter > 0:
                ref_t = (old_tension_meter * 0.65) / (1 - old_s['Tension Loss (%)'] / 100)
            else:
                ref_t = old_tension_work

            cpi_adj = (new_r['종합파워인덱스(HEAD_CPI맞춤)'] - old_r['종합파워인덱스(HEAD_CPI맞춤)']) * 0.0105
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

    # --- 두 번째 탭: 히스토리 보기 및 수정 ---
    with tab2:
        st.header("📖 나의 텐션 히스토리 (수정/삭제 가능)")
        logs_df = load_logs()
        
        if logs_df.empty:
            st.info("아직 저장된 기록이 없습니다. 예측기에서 첫 번째 메모를 남겨보세요!")
        else:
            st.markdown("💡 **Tip:** 표 안의 셀을 **더블 클릭**하면 메모나 텐션 수치를 직접 수정할 수 있습니다. 행의 맨 왼쪽 체크박스를 선택하고 키보드 `Delete` 키를 누르면 기록을 지울 수도 있습니다.")
            
            # 최신 기록이 맨 위로 오게 정렬 후 인덱스 재설정
            logs_df = logs_df.sort_values(by="날짜", ascending=False).reset_index(drop=True)
            
            # 데이터 에디터 적용 (사용자가 화면에서 직접 수정 가능)
            edited_df = st.data_editor(
                logs_df,
                num_rows="dynamic", # 사용자가 행을 직접 삭제/추가할 수 있게 허용
                use_container_width=True,
                key="tension_editor"
            )
            
            col_save, col_down = st.columns(2)
            with col_save:
                # 사용자가 수정한 표를 원본 CSV 파일에 그대로 덮어쓰기
                if st.button("🔄 수정한 기록 덮어쓰기 (저장)", type="primary"):
                    edited_df.to_csv(LOG_FILE, index=False, encoding='utf-8-sig')
                    st.success("수정된 기록이 성공적으로 저장되었습니다!")
                    
            with col_down:
                csv = edited_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="📥 내 기록 엑셀(CSV)로 다운로드",
                    data=csv,
                    file_name='my_tension_history.csv',
                    mime='text/csv',
                )
