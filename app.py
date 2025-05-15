import streamlit as st
import google.generativeai as genai
import os
import time

# Gemini API 설정
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-pro")

# 초기 세션 상태 설정
def init_session():
    if "step" not in st.session_state:
        st.session_state.update({
            "step": 1,
            "topic": "",
            "keywords": [],
            "audience": "",
            "style": "",
            "structure": "",
            "headings": [],
            "draft": "",
            "history": [],
            "chat_input": "",
            "chat_log": []
        })

# Gemini API 호출 함수
def ask_gemini(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ 오류가 발생했습니다: {e}"

# ReAct 기반 프롬프트 생성 함수
def react_prompt(context, question):
    return f"""
당신은 기술 블로그 작성을 도와주는 챗봇입니다.
ReAct 방식(질문→답변→추론→다음 질문)으로 사용자의 정보를 단계별로 수집합니다.

규칙:
- 반드시 챗봇이 먼저 질문합니다.
- 사용자의 응답이 불충분하면 보충 질문을 하세요.
- 사용자의 응답을 요약하고, 요약한 내용이 맞는지 확인 질문을 하세요.
- 사용자가 확인해야 다음 단계로 넘어갑니다.
- 대화는 일반적인 채팅 형태로 구성합니다.

현재 문맥:
{context}

챗봇이 사용자에게 던질 질문:
{question}

이제 사용자에게 자연스럽게 질문을 해주세요.
"""

# 단계별 프롬프트 설계
def step_prompt():
    step = st.session_state.step
    if step == 1:
        return react_prompt("", "기술 블로그를 작성할 주제를 알려주세요. 가능한 구체적일수록 좋아요.")
    elif step == 2:
        return react_prompt(f"주제: {st.session_state.topic}", "그 주제를 기반으로 글의 핵심 키워드를 제안드릴게요. 이 중에서 선택하거나 직접 추가해주셔도 돼요.")
    elif step == 3:
        return react_prompt(f"주제: {st.session_state.topic}, 키워드: {', '.join(st.session_state.keywords)}", "이 글은 어떤 분들이 읽을까요? 예: 입문자, 실무자, 발표 청중 등")
    elif step == 4:
        return react_prompt("", "글의 전체적인 구성은 어떻게 할까요? 예: 서론–본문–결론, 문제–해결, 코드–설명 반복 등")
    elif step == 5:
        return react_prompt(f"주제: {st.session_state.topic}, 키워드: {', '.join(st.session_state.keywords)}, 구조: {st.session_state.structure}", "전체 글을 구성할 소제목을 제안드릴게요. 수정하거나 새로 입력하셔도 됩니다.")
    elif step == 6:
        return react_prompt(f"주제: {st.session_state.topic}\n키워드: {', '.join(st.session_state.keywords)}\n예상 독자: {st.session_state.audience}\n구조: {st.session_state.structure}\n소제목: {', '.join(st.session_state.headings)}", "이제 전체 초안을 작성할게요. 스타일, 구조, 키워드, 소제목을 반영해서 작성하겠습니다.")
    return ""

# 사용자의 응답을 분석해서 상태 저장 (간단한 추출)
def parse_user_reply(reply):
    step = st.session_state.step
    if step == 1:
        st.session_state.topic = reply
    elif step == 2:
        st.session_state.keywords = [kw.strip() for kw in reply.split() if len(kw) > 1]
    elif step == 3:
        st.session_state.audience = reply
    elif step == 4:
        st.session_state.structure = reply
    elif step == 5:
        st.session_state.headings = [h.strip("- ") for h in reply.split("\n") if h.strip()]
    elif step == 6:
        st.session_state.draft = reply

    st.session_state.history.append((f"step{step}", reply))
    st.session_state.step += 1

# Streamlit 앱 실행 함수
def run_app():
    st.set_page_config(page_title="기술 블로그 작성 도우미", layout="wide")
    st.title("📝 기술 블로그 초안 작성 챗봇")
    init_session()

    # 채팅 인터페이스
    chat_log = st.container()
    with chat_log:
        for speaker, message in st.session_state.chat_log:
            if speaker == "user":
                st.chat_message("user").markdown(message)
            else:
                st.chat_message("assistant").markdown(message)

    # 사용자 입력
    user_input = st.chat_input("메시지를 입력하세요")
    if user_input:
        st.session_state.chat_log.append(("user", user_input))
        parse_user_reply(user_input)

        # 다음 단계 질문 생성
        prompt = step_prompt()
        response = ask_gemini(prompt)
        st.session_state.chat_log.append(("assistant", response))
        st.rerun()

    # 마지막 단계에서 초안 출력
    if st.session_state.step > 6 and st.session_state.draft:
        st.markdown("#### ✨ 최종 블로그 초안 (Markdown) ✨")
        st.code(st.session_state.draft, language="markdown")

if __name__ == "__main__":
    run_app()
