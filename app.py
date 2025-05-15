import streamlit as st
import google.generativeai as genai
import time
import os

# Gemini API 설정
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")

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
            "history": []
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
    st.title("📝 기술 블로그 초안 작성 챗봇")
    init_session()
    step = st.session_state.step
    history = st.session_state.history

    # 진행 단계 표시
    st.sidebar.title("📌 진행 상황")
    steps = [
        "주제 입력", "키워드 선택", "스타일 선택",
        "글 구조 선택", "소제목 구성", "초안 작성"
    ]
    for i, s in enumerate(steps, 1):
        status = "✅" if i < step else ("🟡" if i == step else "⚪")
        st.sidebar.write(f"{status} {i}. {s}")

    # 다시 시작
    if st.sidebar.button("🔄 처음부터 다시 시작"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.experimental_rerun()

    st.divider()

    # 단계별 처리
    if step == 1:
        st.subheader("1️⃣ 주제 입력")
        topic = st.text_input("기술 블로그 주제를 입력해주세요:", value=st.session_state.topic)
        if st.button("➡️ 다음 단계"):
            if not topic.strip():
                st.error("주제를 입력해주세요.")
            else:
                prompt = react_prompt("사용자 입력 주제: " + topic, "해당 주제의 맥락을 조금 더 설명해달라고 물어보세요.")
                st.session_state.topic = topic
                st.session_state.history.append(("주제", topic))
                st.session_state.step += 1
                st.experimental_rerun()

    elif step == 2:
        st.subheader("2️⃣ 키워드 추천 및 선택")
        with st.spinner("키워드 추천 중..."):
            prompt = react_prompt(
                f"주제: {st.session_state.topic}",
                "주제에 기반해 기술 블로그의 핵심 키워드를 5~7개 추천하고, 사용자가 선택하거나 추가 입력할 수 있도록 유도하세요."
            )
            suggestion = ask_gemini(prompt)
        st.markdown(suggestion)
        keywords_input = st.text_input("사용할 키워드를 쉼표 없이 자연어로 입력하거나 추천에서 선택해주세요:")
        if st.button("✅ 키워드 확인"):
            confirm_prompt = react_prompt(
                f"사용자 키워드 입력: {keywords_input}",
                "사용자의 입력을 키워드 리스트로 추출하고, 요약해서 맞는지 확인 질문을 하세요."
            )
            confirm = ask_gemini(confirm_prompt)
            st.session_state.keywords = keywords_input
            st.markdown(confirm)
            if st.button("➡️ 확인 후 다음 단계"):
                st.session_state.step += 1
                st.session_state.history.append(("키워드", keywords_input))
                st.experimental_rerun()

    elif step == 3:
        st.subheader("3️⃣ 글 스타일 선택")
        audience = st.text_input("이 글의 예상 독자는 누구인가요? (예: 초심자, 실무자 등)")
        if st.button("➡️ 다음 단계"):
            if not audience:
                st.warning("예상 독자를 입력해주세요.")
            else:
                confirm = ask_gemini(react_prompt(f"입력: {audience}", "이 스타일이 맞는지 요약해서 재확인 요청"))
                st.markdown(confirm)
                if st.button("확인 완료하고 다음 단계로"):
                    st.session_state.audience = audience
                    st.session_state.step += 1
                    st.session_state.history.append(("스타일", audience))
                    st.experimental_rerun()

    elif step == 4:
        st.subheader("4️⃣ 글 구조 선택")
        structure = st.text_input("어떤 글 구조를 원하시나요? 예: 문제→해결, 서론→본문→결론 등")
        if st.button("➡️ 구조 확인 및 예시 생성"):
            if not structure:
                st.warning("구조를 입력해주세요.")
            else:
                prompt = react_prompt(f"구조: {structure}", "이 구조로 예시 문단을 생성하고, 사용자에게 맞는지 질문하세요.")
                example = ask_gemini(prompt)
                st.markdown(example)
                if st.button("이 구조로 계속 진행하기"):
                    st.session_state.structure = structure
                    st.session_state.step += 1
                    st.session_state.history.append(("구조", structure))
                    st.experimental_rerun()

    elif step == 5:
        st.subheader("5️⃣ 소제목 구성")
        with st.spinner("소제목 제안 중..."):
            prompt = react_prompt(
                f"주제: {st.session_state.topic}, 키워드: {st.session_state.keywords}, 구조: {st.session_state.structure}",
                "소제목을 4~6개 제안하고, 수정할 수 있게 하세요."
            )
            response = ask_gemini(prompt)
        st.markdown(response)
        headings = st.text_area("수정이 필요한 경우 직접 수정하거나, 그대로 사용하실 수 있습니다:")
        if st.button("➡️ 소제목 확정"):
            st.session_state.headings = headings
            st.session_state.step += 1
            st.session_state.history.append(("소제목", headings))
            st.experimental_rerun()

    elif step == 6:
        st.subheader("6️⃣ 최종 초안 작성")
        with st.spinner("초안 작성 중 (GPT)..."):
            prompt = react_prompt(
                f"주제: {st.session_state.topic}\n키워드: {st.session_state.keywords}\n스타일: {st.session_state.audience}\n구조: {st.session_state.structure}\n소제목: {st.session_state.headings}",
                "위 정보를 기반으로 마크다운 형식의 기술 블로그 초안을 작성하세요. 자연스럽고 논리적인 흐름이 중요하며, 필요한 경우 코드 블록도 포함하세요."
            )
            draft = ask_gemini(prompt)
        st.markdown("#### ✨ 초안 결과 (Markdown) ✨")
        st.code(draft, language="markdown")
        st.session_state.draft = draft

        if st.button("📋 복사 완료 및 종료"):
            st.success("초안이 복사되었습니다. 다른 플랫폼에 자유롭게 붙여넣기 하세요!")

if __name__ == "__main__":
    run_app()
