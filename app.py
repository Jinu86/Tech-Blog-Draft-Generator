import streamlit as st
import google.generativeai as genai
import os

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
            "chat": []
        })

# ReAct 프롬프트 생성 함수
def react_prompt(context, question):
    return f"""
당신은 사용자의 기술 블로그 작성을 돕는 챗봇입니다.
ReAct 방식(질문→답변→추론→다음 질문)으로 대화하며, 각 단계에서 충분한 정보를 얻기 전에는 다음 단계로 넘어가지 마세요.

현재까지 사용자와의 대화 문맥:
{context}

다음 단계에서 얻고자 하는 질문:
{question}

필수 조건:
- 반드시 챗봇이 먼저 질문합니다.
- 사용자의 응답이 불충분하면 명확히 재질문합니다.
- 사용자의 응답에 대해 챗봇이 이해한 바를 요약해서 재확인합니다.
- 최종 확인을 받아야 다음 단계로 넘어갑니다.
- 예시는 필요 시 제시합니다.

이제 사용자에게 질문하세요:
"""

# Gemini API 호출 함수
def ask_gemini(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ 오류가 발생했습니다: {e}"

# UI 및 흐름 처리
def run_app():
    st.set_page_config(page_title="기술 블로그 챗봇")
    st.title("🤖 기술 블로그 작성 챗봇")
    init_session()
    step = st.session_state.step
    history = st.session_state.history
    chat = st.session_state.chat

    st.sidebar.title("📌 진행 상황")
    steps = [
        "주제 입력", "키워드 선택", "스타일 선택",
        "글 구조 선택", "소제목 구성", "초안 작성"
    ]
    for i, s in enumerate(steps, 1):
        status = "✅" if i < step else ("🟡" if i == step else "⚪")
        st.sidebar.write(f"{status} {i}. {s}")

    if st.sidebar.button("🔄 처음부터 다시 시작"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.experimental_rerun()

    for role, msg in chat:
        st.chat_message(role).write(msg)

    user_input = st.chat_input("메시지를 입력하세요")

    if user_input:
        st.session_state.chat.append(("user", user_input))

        if step == 1:
            st.session_state.topic = user_input.strip()
            prompt = react_prompt("사용자 입력 주제: " + user_input, "해당 주제의 맥락을 조금 더 설명해달라고 물어보세요.")
            response = ask_gemini(prompt)
            st.session_state.chat.append(("assistant", response))
            st.session_state.history.append(("주제", user_input))
            st.session_state.step += 1

        elif step == 2:
            if not st.session_state.keywords:
                prompt = react_prompt(f"주제: {st.session_state.topic}", "주제에 기반한 키워드 5~7개 추천 후 선택 또는 추가 입력 받기")
                suggestion = ask_gemini(prompt)
                st.session_state.chat.append(("assistant", suggestion))
            else:
                prompt = react_prompt(f"사용자 입력 키워드: {user_input}", "입력한 키워드를 리스트로 추출하고 요약해 확인 요청")
                confirm = ask_gemini(prompt)
                keywords = [kw.strip() for kw in user_input.replace("\n", ",").replace("과", ",").split(",") if kw.strip()]
                st.session_state.keywords = keywords
                st.session_state.chat.append(("assistant", confirm))
                st.session_state.history.append(("키워드", keywords))
                st.session_state.step += 1

        elif step == 3:
            st.session_state.audience = user_input.strip()
            prompt = react_prompt(f"예상 독자: {user_input}", "이 스타일이 맞는지 확인 질문하기")
            confirm = ask_gemini(prompt)
            st.session_state.chat.append(("assistant", confirm))
            st.session_state.history.append(("스타일", user_input))
            st.session_state.step += 1

        elif step == 4:
            st.session_state.structure = user_input.strip()
            prompt = react_prompt(f"구조 입력: {user_input}", "이 구조로 한 문단 예시를 보여주고 적합한지 확인")
            example = ask_gemini(prompt)
            st.session_state.chat.append(("assistant", example))
            st.session_state.history.append(("구조", user_input))
            st.session_state.step += 1

        elif step == 5:
            st.session_state.headings = [h.strip() for h in user_input.replace("\n", ",").split(",") if h.strip()]
            prompt = react_prompt(f"소제목 입력: {user_input}", "수정 가능 여부 확인 및 소제목 확정 요청")
            confirm = ask_gemini(prompt)
            st.session_state.chat.append(("assistant", confirm))
            st.session_state.history.append(("소제목", st.session_state.headings))
            st.session_state.step += 1

        elif step == 6:
            prompt = react_prompt(
                f"주제: {st.session_state.topic}\n키워드: {', '.join(st.session_state.keywords)}\n스타일: {st.session_state.audience}\n구조: {st.session_state.structure}\n소제목: {', '.join(st.session_state.headings)}",
                "위 정보를 바탕으로 마크다운 형식의 기술 블로그 초안을 작성하고, 자연스러운 흐름으로 구성하세요."
            )
            draft = ask_gemini(prompt)
            st.session_state.draft = draft
            st.session_state.chat.append(("assistant", "초안이 완성되었습니다. 아래에 전체 내용을 보여드릴게요:"))
            st.chat_message("assistant").code(draft, language="markdown")

if __name__ == "__main__":
    run_app()
