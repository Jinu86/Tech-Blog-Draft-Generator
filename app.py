import streamlit as st
import google.generativeai as genai
import time
import os

# Gemini API 설정
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-pro")

# 초기 세션 상태 설정
def init_session():
    st.session_state.setdefault("step", 1)
    st.session_state.setdefault("topic", "")
    st.session_state.setdefault("keywords", [])
    st.session_state.setdefault("audience", "")
    st.session_state.setdefault("style", "")
    st.session_state.setdefault("structure", "")
    st.session_state.setdefault("headings", [])
    st.session_state.setdefault("draft", "")
    st.session_state.setdefault("history", [])

# ReAct 프롬프트 생성 함수
def react_prompt(context, question):
    return f"""
당신은 기술 블로그 작성을 도와주는 챗봇입니다. 모든 대화는 ReAct 방식(질문→응답→추론→다음 질문)으로 진행되어야 하며,
모든 단계는 다음과 같은 원칙을 따라야 합니다:

1. 챗봇이 먼저 질문합니다.
2. 응답이 불충분할 경우, 명확히 재질문합니다.
3. 응답에 대해 챗봇이 이해한 내용을 요약하고 사용자에게 재확인합니다.
4. 최종 확인을 받은 뒤에야 다음 단계로 넘어갑니다.
5. 예시는 필요 시 제공됩니다.

현재까지 사용자와의 대화 문맥:
{context}

다음 단계에서 얻고자 하는 질문:
{question}

위 원칙에 따라 사용자에게 질문하세요:
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
    st.title("📝 기술 블로그 초안 작성 챗봇")
    init_session()
    step = st.session_state.step
    history = st.session_state.history

    st.sidebar.title("📌 진행 상황")
    steps = [
        "주제 입력", "키워드 선택", "스타일 선택",
        "글 구조 선택", "소제목 구성", "초안 작성"
    ]
    for i, s in enumerate(steps, 1):
        status = "✅" if i < step else ("🟡" if i == step else "⚪")
        st.sidebar.write(f"{status} {i}. {s}")

    if st.sidebar.button("🔄 처음부터 다시 시작"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()

    st.divider()

    if prompt := st.chat_input("답변을 입력하세요..."):
        st.chat_message("user").write(prompt)
        st.session_state.user_input = prompt

        # 단계별 처리
        if step == 1:
            topic = prompt.strip()
            confirm = ask_gemini(react_prompt(f"주제 입력: {topic}", "사용자 입력 내용을 확인하고, 이 주제에 대한 이해가 맞는지 물어보세요."))
            st.chat_message("assistant").markdown(confirm)
            st.session_state.topic = topic
            st.session_state.step += 1
            st.session_state.history.append(("주제", topic))

        elif step == 2:
            if "keywords_suggested" not in st.session_state:
                with st.spinner("GPT가 키워드를 생성 중입니다..."):
                    suggestion = ask_gemini(react_prompt(f"주제: {st.session_state.topic}", "추천 키워드 제시 + 선택 유도"))
                    st.session_state.keywords_suggested = suggestion
                    st.chat_message("assistant").markdown(suggestion)
            raw_keywords = prompt.strip()
            confirm_prompt = react_prompt(f"입력 키워드: {raw_keywords}", "키워드를 리스트로 정리하고 맞는지 물어보세요")
            confirm = ask_gemini(confirm_prompt)
            st.chat_message("assistant").markdown(confirm)
            keyword_list = [k.strip() for k in raw_keywords.split(",") if k.strip()]
            st.session_state.keywords = keyword_list
            st.session_state.step += 1
            st.session_state.history.append(("키워드", keyword_list))

        elif step == 3:
            audience = prompt.strip()
            confirm = ask_gemini(react_prompt(f"입력: {audience}", "이 독자층이 맞는지 재확인 질문"))
            st.chat_message("assistant").markdown(confirm)
            st.session_state.audience = audience
            st.session_state.step += 1
            st.session_state.history.append(("스타일", audience))

        elif step == 4:
            structure = prompt.strip()
            example = ask_gemini(react_prompt(f"구조: {structure}", "이 구조로 짧은 예시 문단을 생성하고 사용자 확인 요청"))
            st.chat_message("assistant").markdown(example)
            st.session_state.structure = structure
            st.session_state.step += 1
            st.session_state.history.append(("구조", structure))

        elif step == 5:
            if "headings_suggested" not in st.session_state:
                with st.spinner("GPT가 소제목을 제안 중입니다..."):
                    prompt_head = react_prompt(
                        f"주제: {st.session_state.topic}, 키워드: {st.session_state.keywords}, 구조: {st.session_state.structure}",
                        "소제목을 4~6개 추천하고 사용자에게 수정할 수 있도록 하세요."
                    )
                    response = ask_gemini(prompt_head)
                    st.session_state.headings_suggested = response
                    st.chat_message("assistant").markdown(response)
            headings = prompt.strip()
            st.chat_message("assistant").write("✅ 소제목을 확인했어요. 초안을 작성할게요!")
            st.session_state.headings = headings
            st.session_state.step += 1
            st.session_state.history.append(("소제목", headings))

        elif step == 6:
            st.chat_message("assistant").write("6️⃣ 지금까지 입력하신 내용을 기반으로 전체 초안을 작성할게요!")
            with st.spinner("GPT가 마크다운 블로그 초안을 작성 중입니다..."):
                prompt_draft = react_prompt(
                    f"주제: {st.session_state.topic}\n키워드: {st.session_state.keywords}\n스타일: {st.session_state.audience}\n구조: {st.session_state.structure}\n소제목: {st.session_state.headings}",
                    "위 정보를 기반으로 마크다운 형식의 기술 블로그 초안을 작성하세요. 자연스럽고 논리적인 흐름이 중요하며, 필요한 경우 코드 블록도 포함하세요."
                )
                draft = ask_gemini(prompt_draft)
            st.markdown("#### ✨ 초안 결과 (Markdown) ✨")
            st.code(draft, language="markdown")
            st.session_state.draft = draft

if __name__ == "__main__":
    run_app()
