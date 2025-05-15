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
st.set_page_config(page_title="기술 블로그 초안 생성 챗봇", page_icon="📝")
st.title("📝 기술 블로그 초안 생성 챗봇")

# 세션 초기화
if 'state' not in st.session_state:
    st.session_state.state = 'ask_topic'
    st.session_state.data = {
        'topic': '', 'keywords': [], 'style': '', 'structure': '',
        'subtitles': [], 'current_idx': 0, 'drafts': []
    }

# 내부 함수: API 호출 with error handling
def chat_with_gemini(prompt):
    try:
        resp = genai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {'role': 'system', 'content': '당신은 기술 블로그 초안 작성 도우미입니다.'},
                {'role': 'user', 'content': prompt}
            ]
        )
        return resp.choices[0].message['content']
    except GoogleAPIError as e:
        st.error(f"API 호출 중 오류가 발생했습니다: {e.message}")
        st.stop()
    except Exception as e:
        st.error(f"알 수 없는 오류가 발생했습니다: {str(e)}")
        st.stop()

# 프로그레스 표시 함수
def show_progress():
    total = len(st.session_state.data['subtitles'])
    idx = st.session_state.data['current_idx']
    if total > 0:
        progress = int((idx / total) * 100)
        st.progress(progress)

# 단계별 흐름 처리
if st.session_state.state == 'ask_topic':
    user = st.text_input("주제를 말씀해주세요:")
    if user:
        st.session_state.data['topic'] = user
        st.session_state.state = 'confirm_topic'
        st.experimental_rerun()

elif st.session_state.state == 'confirm_topic':
    prompt = f"(🤔 주제 파악 중…) '{st.session_state.data['topic']}' 이 맞나요?"
    st.markdown(chat_with_gemini(prompt))
    if st.button("네"): st.session_state.state='ask_keywords'; st.experimental_rerun()
    if st.button("아니요"): st.session_state.state='ask_topic'; st.experimental_rerun()

elif st.session_state.state == 'ask_keywords':
    prompt = f"(🤔 키워드 고민 중…) 주제: {st.session_state.data['topic']}에 적합한 키워드를 추천해주세요."
    rec = chat_with_gemini(prompt)
    st.markdown(rec)
    kw = st.text_input("원하는 키워드를 쉼표로 입력해주세요:")
    if kw:
        st.session_state.data['keywords'] = [k.strip() for k in kw.split(',')]
        st.session_state.state='confirm_keywords'; st.experimental_rerun()

elif st.session_state.state == 'confirm_keywords':
    kws = ', '.join(st.session_state.data['keywords'])
    prompt = f"(🤔 키워드 확인…) 선택하신 키워드: {kws} 이 맞나요?"
    st.markdown(chat_with_gemini(prompt))
    if st.button("네"): st.session_state.state='ask_style'; st.experimental_rerun()
    if st.button("아니요"): st.session_state.state='ask_keywords'; st.experimental_rerun()

elif st.session_state.state == 'ask_style':
    user = st.text_input("어떤 스타일(초심자용, 실무자용, 발표용)으로 작성할까요?")
    if user:
        st.session_state.data['style'] = user
        st.session_state.state='confirm_style'; st.experimental_rerun()

elif st.session_state.state == 'confirm_style':
    prompt = f"(🤔 스타일 확인…) '{st.session_state.data['style']}' 스타일로 진행할까요?"
    st.markdown(chat_with_gemini(prompt))
    if st.button("네"): st.session_state.state='ask_structure'; st.experimental_rerun()
    if st.button("아니요"): st.session_state.state='ask_style'; st.experimental_rerun()

elif st.session_state.state == 'ask_structure':
    user = st.text_input("어떤 글 구조로 진행할까요? (예: 서론-목차-본문-결론)")
    if user:
        st.session_state.data['structure'] = user
        st.session_state.state='confirm_structure'; st.experimental_rerun()

elif st.session_state.state == 'confirm_structure':
    prompt = f"(🤔 구조 확인…) '{st.session_state.data['structure']}' 구조로 진행합니다."
    st.markdown(chat_with_gemini(prompt))
    if st.button("네"): st.session_state.state='ask_subtitles'; st.experimental_rerun()
    if st.button("아니요"): st.session_state.state='ask_structure'; st.experimental_rerun()

elif st.session_state.state == 'ask_subtitles':
    prompt = (
        f"(🤔 소제목 뽑는 중…) 주제: {st.session_state.data['topic']}, "
        f"키워드: {', '.join(st.session_state.data['keywords'])}, "
        f"구조: {st.session_state.data['structure']}에 맞춰 소제목 5개 추천해주세요."
    )
    rec = chat_with_gemini(prompt)
    st.markdown(rec)
    subs = st.text_input("소제목을 쉼표로 입력해주세요:")
    if subs:
        st.session_state.data['subtitles'] = [s.strip() for s in subs.split(',')]
        st.session_state.state='write_section'; st.experimental_rerun()

elif st.session_state.state == 'write_section':
    show_progress()
    idx = st.session_state.data['current_idx']
    section = st.session_state.data['subtitles'][idx]
    prompt = f"(🤔 본문 생성 중…) 섹션: {section}에 대해 작성해주세요."
    draft = chat_with_gemini(prompt)
    st.markdown(f"**## {section}**\n{draft}")
    edit = st.text_area(
        "수정할 부분이 있으면 작성하고, 없으면 '다음'이라고 입력하세요:",
        key="edit"
    )
    if st.button("제출"):
        if edit.strip().lower() != '다음':
            draft = chat_with_gemini(f"{section} 섹션을 이렇게 수정해주세요: {edit}")
            st.markdown(f"**## {section}**\n{draft}")
        st.session_state.data['drafts'].append(draft)
        st.session_state.data['current_idx'] += 1
        if st.session_state.data['current_idx'] < len(st.session_state.data['subtitles']):
            st.experimental_rerun()
        else:
            st.session_state.state='final_review'; st.experimental_rerun()

elif st.session_state.state == 'final_review':
    st.markdown("(🤔 전체 초안 완성!) 아래는 전체 초안입니다:")
    for sec, text in zip(st.session_state.data['subtitles'], st.session_state.data['drafts']):
        st.markdown(f"**## {sec}**\n{text}")
    st.write("수정할 구역이나 포맷 변경을 요청해주세요.")
    req = st.text_input("요청:", key="final_req")
    if st.button("제출 최종 요청") and req:
        result = chat_with_gemini(f"전체 초안을 다음과 같이 처리해주세요: {req}")
        st.markdown(result)
        st.balloons()
