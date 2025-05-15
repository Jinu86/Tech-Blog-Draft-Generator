import streamlit as st
import google.generativeai as genai
import os
from google.api_core.exceptions import GoogleAPIError

#--- 환경 변수 설정 ---
API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("GEMINI API 키가 설정되지 않았습니다. 설정 후 다시 실행해주세요.")
    st.stop()

# Gemini API 구성
genai.configure(api_key=API_KEY)
MODEL = "gemini-pro-1.5"

# 페이지 설정
st.set_page_config(
    page_title="기술 블로그 초안 생성 챗봇",
    page_icon="📝",
    layout="centered"
)

# 세션 초기화
if 'state' not in st.session_state:
    st.session_state.state = 'ask_topic'
    st.session_state.history = []  # 대화 히스토리 저장
    st.session_state.data = {
        'topic': '', 'keywords': [], 'style': '', 'structure': '',
        'subtitles': [], 'current_idx': 0, 'drafts': []
    }

# 내부 함수: 메시지 추가 및 API 호출
def add_user_message(msg):
    st.session_state.history.append({'role': 'user', 'content': msg})

def add_bot_message(msg):
    st.session_state.history.append({'role': 'assistant', 'content': msg})

# Gemini 호출
def chat_with_gemini(prompt):
    try:
        resp = genai.ChatCompletion.create(
            model=MODEL,
            messages=[{'role': m['role'], 'content': m['content']} for m in st.session_state.history] + [{'role': 'user', 'content': prompt}]
        )
        return resp.choices[0].message['content']
    except GoogleAPIError as e:
        error_msg = f"API 호출 중 오류가 발생했습니다: {e.message}"
        add_bot_message(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"알 수 없는 오류가 발생했습니다: {str(e)}"
        add_bot_message(error_msg)
        return error_msg

# 대화 렌더링
for chat in st.session_state.history:
    if chat['role'] == 'user':
        st.chat_message('user').write(chat['content'])
    else:
        st.chat_message('assistant').write(chat['content'])

# 사용자 입력 받기
user_input = st.chat_input('')
if user_input:
    add_user_message(user_input)
    # 현재 단계 로직 처리
    if st.session_state.state == 'ask_topic':
        st.session_state.data['topic'] = user_input
        bot = f"(🤔 주제 파악 중…) '{user_input}'이 맞나요?"
        add_bot_message(bot)
        st.session_state.state = 'confirm_topic'
    elif st.session_state.state == 'confirm_topic':
        if '네' in user_input:
            add_bot_message("좋아요! 키워드를 추천해드릴게요.")
            st.session_state.state = 'ask_keywords'
        else:
            add_bot_message("그럼 다시 주제를 말씀해주세요.")
            st.session_state.state = 'ask_topic'
    elif st.session_state.state == 'ask_keywords':
        # 추천 후 키워드 입력 처리
        add_bot_message("(🤔 키워드 고민 중…)")
        rec = chat_with_gemini(f"주제: {st.session_state.data['topic']}에 적합한 키워드를 추천해주세요.")
        add_bot_message(rec)
        add_bot_message("추천 키워드를 기반으로, 원하시는 키워드를 쉼표로 입력해주세요.")
        st.session_state.state = 'confirm_keywords'
    elif st.session_state.state == 'confirm_keywords':
        kws = [k.strip() for k in user_input.split(',')]
        st.session_state.data['keywords'] = kws
        bot = f"(🤔 키워드 확인…) 선택하신 키워드: {', '.join(kws)} 이 맞나요?"
        add_bot_message(bot)
        st.session_state.state = 'confirm_keywords_pending'
    elif st.session_state.state == 'confirm_keywords_pending':
        if '네' in user_input:
            add_bot_message("좋습니다. 스타일을 알려주세요 (초심자용, 실무자용, 발표용).")
            st.session_state.state = 'ask_style'
        else:
            add_bot_message("다시 키워드를 입력해주세요.")
            st.session_state.state = 'ask_keywords'
    elif st.session_state.state == 'ask_style':
        st.session_state.data['style'] = user_input
        bot = f"(🤔 스타일 확인…) '{user_input}' 스타일로 진행할까요?"
        add_bot_message(bot)
        st.session_state.state = 'confirm_style'
    elif st.session_state.state == 'confirm_style':
        if '네' in user_input:
            add_bot_message("구조를 알려주세요. 예: 서론-목차-본문-결론")
            st.session_state.state = 'ask_structure'
        else:
            add_bot_message("다시 스타일을 입력해주세요.")
            st.session_state.state = 'ask_style'
    elif st.session_state.state == 'ask_structure':
        st.session_state.data['structure'] = user_input
        bot = f"(🤔 구조 확인…) '{user_input}' 구조로 진행합니다."
        add_bot_message(bot)
        st.session_state.state = 'confirm_structure'
    elif st.session_state.state == 'confirm_structure':
        if '네' in user_input:
            add_bot_message("소제목을 추천해드릴게요.")
            st.session_state.state = 'ask_subtitles'
        else:
            add_bot_message("다시 구조를 입력해주세요.")
            st.session_state.state = 'ask_structure'
    elif st.session_state.state == 'ask_subtitles':
        subs = [s.strip() for s in user_input.split(',')]
        st.session_state.data['subtitles'] = subs
        bot = f"(🤔 소제목 확인…) 입력하신 소제목: {', '.join(subs)}"
        add_bot_message(bot)
        add_bot_message("'준비 완료'라고 입력하시면 본문 생성으로 넘어갑니다.")
        st.session_state.state = 'confirm_subtitles'
    elif st.session_state.state == 'confirm_subtitles':
        if '준비 완료' in user_input:
            add_bot_message("본문을 생성합니다…")
            st.session_state.state = 'write_section'
        else:
            add_bot_message("다시 소제목을 입력해주세요.")
            st.session_state.state = 'ask_subtitles'
    elif st.session_state.state == 'write_section':
        idx = st.session_state.data['current_idx']
        section = st.session_state.data['subtitles'][idx]
        draft = chat_with_gemini(f"섹션: {section}에 대해 작성해주세요.")
        add_bot_message(f"**{section}**\n{draft}")
        add_bot_message("수정할 부분이 있으면 작성해주세요. 없으면 '다음'이라고 입력해주세요.")
        st.session_state.state = 'edit_section'
    elif st.session_state.state == 'edit_section':
        if '다음' not in user_input:
            section = st.session_state.data['subtitles'][st.session_state.data['current_idx']]
            draft = chat_with_gemini(f"{section} 섹션을 이렇게 수정해주세요: {user_input}")
            add_bot_message(f"**{section}**\n{draft}")
        st.session_state.data['drafts'].append(user_input if '다음' in user_input else draft)
        st.session_state.data['current_idx'] += 1
        if st.session_state.data['current_idx'] < len(st.session_state.data['subtitles']):
            add_bot_message("다음 섹션으로 넘어갑니다.")
            st.session_state.state = 'write_section'
        else:
            add_bot_message("모든 섹션이 완료되었습니다. 전체 검토로 넘어갑니다.")
            st.session_state.state = 'final_review'
    elif st.session_state.state == 'final_review':
        add_bot_message("(🤔 전체 초안 완성!) 아래는 전체 초안입니다:")
        for sec, text in zip(st.session_state.data['subtitles'], st.session_state.data['drafts']):
            add_bot_message(f"**{sec}**\n{text}")
        add_bot_message("수정할 구역이나 포맷 변경을 자유롭게 입력해주세요.")
        st.session_state.state = 'final_edit'
    elif st.session_state.state == 'final_edit':
        result = chat_with_gemini(f"전체 초안을 다음과 같이 처리해주세요: {user_input}")
        add_bot_message(result)
        st.balloons()

    # 리렌더링
    st.experimental_rerun()
