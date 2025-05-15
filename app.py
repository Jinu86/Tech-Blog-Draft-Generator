import streamlit as st
import google.generativeai as genai
import time
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

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
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("waiting_for_input", True)
    
# 대화 히스토리에 메시지 추가
def add_message(role, content):
    st.session_state.messages.append({"role": role, "content": content})

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

# 단계 진행 확인 프롬프트
def check_confirmation_prompt(step, user_input, context):
    prompts = {
        1: f"사용자가 입력한 주제: '{user_input}'에 대해, 이것이 기술 블로그 주제로 적절한지 평가하고, 사용자가 '네', '좋아요', '맞아요', '맞습니다', '다음 단계로', '진행해주세요' 등 확정 의사를 표현했는지 분석하세요. 확정 의사가 있으면 'CONFIRMED'를, 없으면 'NEEDS_CONFIRMATION'을 반환하세요.",
        2: f"사용자가 입력한 키워드: '{user_input}'에 대해, 이것이 앞서 논의한 주제와 관련된 적절한 키워드인지 평가하고, 사용자가 확정 의사('네', '좋아요', '좋습니다', '다음', '진행' 등)를 표현했는지 분석하세요. 확정 의사가 있으면 'CONFIRMED'를, 없으면 'NEEDS_CONFIRMATION'을 반환하세요.",
        3: f"사용자가 입력한 대상 독자: '{user_input}'에 대해, 이것이 명확한 대상 독자를 나타내는지 평가하고, 사용자가 확정 의사('네', '좋아요', '좋습니다', '다음', '진행' 등)를 표현했는지 분석하세요. 확정 의사가 있으면 'CONFIRMED'를, 없으면 'NEEDS_CONFIRMATION'을 반환하세요.",
        4: f"사용자가 입력한 글 구조: '{user_input}'에 대해, 이것이 명확한 글 구조를 나타내는지 평가하고, 사용자가 확정 의사('네', '좋아요', '좋습니다', '다음', '진행' 등)를 표현했는지 분석하세요. 확정 의사가 있으면 'CONFIRMED'를, 없으면 'NEEDS_CONFIRMATION'을 반환하세요.",
        5: f"사용자가 입력한 소제목: '{user_input}'에 대해, 이것이 앞서 논의한 주제, 키워드, 구조에 부합하는 적절한 소제목들인지 평가하고, 사용자가 확정 의사('네', '좋아요', '좋습니다', '다음', '진행' 등)를 표현했는지 분석하세요. 확정 의사가 있으면 'CONFIRMED'를, 없으면 'NEEDS_CONFIRMATION'을 반환하세요.",
    }
    
    if step in prompts:
        try:
            response = model.generate_content(prompts[step])
            result = response.text.strip()
            return "CONFIRMED" in result
        except Exception as e:
            st.error(f"확인 과정에서 오류 발생: {e}")
            return False
    return False

# Gemini API 호출 함수
def ask_gemini(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ 오류가 발생했습니다: {e}"

# 단계별 처리 함수
def process_step(step, user_input):
    if step == 1:  # 주제 입력
        if st.session_state.waiting_for_input:
            context = "아직 주제가 입력되지 않았습니다."
            prompt = react_prompt(context, "기술 블로그 주제 입력 요청 및 의도 파악")
            response = ask_gemini(prompt)
            add_message("assistant", response)
            st.session_state.waiting_for_input = False
        else:
            confirmation = check_confirmation_prompt(step, user_input, st.session_state.messages)
            if confirmation:
                st.session_state.topic = user_input
                st.session_state.step = 2
                st.session_state.waiting_for_input = True
                # 추가 응답으로 다음 단계 안내
                next_prompt = react_prompt(f"주제 '{user_input}'가 확정되었습니다.", "키워드 입력 단계로 자연스럽게 넘어가세요.")
                response = ask_gemini(next_prompt)
                add_message("assistant", response)
            else:
                context = f"사용자가 입력한 주제: {user_input}"
                prompt = react_prompt(context, "주제에 대한 의견 제시 및 확정 질문")
                response = ask_gemini(prompt)
                add_message("assistant", response)
    
    elif step == 2:  # 키워드 입력
        if st.session_state.waiting_for_input:
            context = f"주제: {st.session_state.topic}"
            prompt = react_prompt(context, "주제에 적합한 키워드 추천 및 선택 요청")
            response = ask_gemini(prompt)
            add_message("assistant", response)
            st.session_state.waiting_for_input = False
        else:
            confirmation = check_confirmation_prompt(step, user_input, st.session_state.messages)
            if confirmation:
                st.session_state.keywords = user_input
                st.session_state.step = 3
                st.session_state.waiting_for_input = True
                next_prompt = react_prompt(f"키워드 '{user_input}'가 확정되었습니다.", "글 스타일/독자층 단계로 자연스럽게 넘어가세요.")
                response = ask_gemini(next_prompt)
                add_message("assistant", response)
            else:
                context = f"주제: {st.session_state.topic}, 사용자가 제안한 키워드: {user_input}"
                prompt = react_prompt(context, "제안된 키워드에 대한 피드백 및 확정 질문")
                response = ask_gemini(prompt)
                add_message("assistant", response)
    
    elif step == 3:  # 스타일/독자층 선택
        if st.session_state.waiting_for_input:
            context = f"주제: {st.session_state.topic}, 키워드: {st.session_state.keywords}"
            prompt = react_prompt(context, "글의 대상 독자층 질문")
            response = ask_gemini(prompt)
            add_message("assistant", response)
            st.session_state.waiting_for_input = False
        else:
            confirmation = check_confirmation_prompt(step, user_input, st.session_state.messages)
            if confirmation:
                st.session_state.audience = user_input
                st.session_state.step = 4
                st.session_state.waiting_for_input = True
                next_prompt = react_prompt(f"대상 독자층 '{user_input}'이 확정되었습니다.", "글 구조 단계로 자연스럽게 넘어가세요.")
                response = ask_gemini(next_prompt)
                add_message("assistant", response)
            else:
                context = f"주제: {st.session_state.topic}, 키워드: {st.session_state.keywords}, 제안된 독자층: {user_input}"
                prompt = react_prompt(context, "제안된 독자층에 대한 피드백 및 확정 질문")
                response = ask_gemini(prompt)
                add_message("assistant", response)
    
    elif step == 4:  # 글 구조 선택
        if st.session_state.waiting_for_input:
            context = f"주제: {st.session_state.topic}, 키워드: {st.session_state.keywords}, 독자층: {st.session_state.audience}"
            prompt = react_prompt(context, "글의 구조에 대한 질문")
            response = ask_gemini(prompt)
            add_message("assistant", response)
            st.session_state.waiting_for_input = False
        else:
            confirmation = check_confirmation_prompt(step, user_input, st.session_state.messages)
            if confirmation:
                st.session_state.structure = user_input
                st.session_state.step = 5
                st.session_state.waiting_for_input = True
                next_prompt = react_prompt(f"글 구조 '{user_input}'가 확정되었습니다.", "소제목 구성 단계로 자연스럽게 넘어가세요.")
                response = ask_gemini(next_prompt)
                add_message("assistant", response)
            else:
                context = f"주제: {st.session_state.topic}, 키워드: {st.session_state.keywords}, 독자층: {st.session_state.audience}, 제안된 구조: {user_input}"
                prompt = react_prompt(context, "제안된 구조에 대한 짧은 예시 및 확정 질문")
                response = ask_gemini(prompt)
                add_message("assistant", response)
    
    elif step == 5:  # 소제목 구성
        if st.session_state.waiting_for_input:
            context = f"주제: {st.session_state.topic}, 키워드: {st.session_state.keywords}, 독자층: {st.session_state.audience}, 구조: {st.session_state.structure}"
            prompt = react_prompt(context, "소제목 제안 및 사용자 의견 요청")
            response = ask_gemini(prompt)
            add_message("assistant", response)
            st.session_state.waiting_for_input = False
        else:
            confirmation = check_confirmation_prompt(step, user_input, st.session_state.messages)
            if confirmation:
                st.session_state.headings = user_input
                st.session_state.step = 6
                st.session_state.waiting_for_input = True
                # 소제목이 확정되면 바로 초안 작성 단계로
                context = f"주제: {st.session_state.topic}, 키워드: {st.session_state.keywords}, 독자층: {st.session_state.audience}, 구조: {st.session_state.structure}, 소제목: {user_input}"
                prompt = react_prompt(context, "마크다운 형식의 기술 블로그 초안 작성")
                add_message("assistant", "✨ 소제목이 확정되었습니다. 초안을 작성 중입니다...")
                with st.spinner("초안 작성 중..."):
                    draft = ask_gemini(prompt)
                st.session_state.draft = draft
                add_message("assistant", "📝 초안이 작성되었습니다!")
            else:
                context = f"주제: {st.session_state.topic}, 키워드: {st.session_state.keywords}, 독자층: {st.session_state.audience}, 구조: {st.session_state.structure}, 제안된 소제목: {user_input}"
                prompt = react_prompt(context, "제안된 소제목에 대한 피드백 및 확정 질문")
                response = ask_gemini(prompt)
                add_message("assistant", response)
    
    elif step == 6:  # 초안 표시 및 최종 피드백
        if "draft_displayed" not in st.session_state or not st.session_state.draft_displayed:
            feedback_prompt = react_prompt(f"블로그 초안이 작성되었습니다. 내용: {st.session_state.draft[:200]}...", "작성된 초안에 대한 간략한 설명 및 피드백 요청")
            feedback = ask_gemini(feedback_prompt)
            add_message("assistant", feedback)
            st.session_state.draft_displayed = True
        else:
            # 사용자의 추가 피드백 처리
            context = f"사용자의 피드백: {user_input}"
            prompt = react_prompt(context, "추가 질문이나 수정 요청에 대한 답변")
            response = ask_gemini(prompt)
            add_message("assistant", response)

# UI 및 흐름 처리
def run_app():
    st.title("📝 기술 블로그 초안 작성 챗봇")
    init_session()
    
    # 사이드바 - 진행 상황
    st.sidebar.title("📌 진행 상황")
    steps = [
        "주제 입력", "키워드 선택", "스타일 선택",
        "글 구조 선택", "소제목 구성", "초안 작성"
    ]
    for i, s in enumerate(steps, 1):
        status = "✅" if i < st.session_state.step else ("🟡" if i == st.session_state.step else "⚪")
        st.sidebar.write(f"{status} {i}. {s}")
    
    # 다시 시작 버튼
    if st.sidebar.button("🔄 처음부터 다시 시작"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()
    
    # 초기 메시지 표시
    if not st.session_state.messages:
        initial_message = "안녕하세요! 기술 블로그 초안 작성을 도와드리겠습니다. 어떤 주제로 블로그를 작성하고 싶으신가요?"
        add_message("assistant", initial_message)

    # 메시지 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 초안이 생성되었다면 별도 표시
    if st.session_state.step == 6 and st.session_state.draft:
        st.markdown("### 📄 작성된 초안")
        st.code(st.session_state.draft, language="markdown")
        st.download_button(
            label="📥 마크다운 파일로 다운로드",
            data=st.session_state.draft,
            file_name="blog_draft.md",
            mime="text/markdown"
        )
    
    # 사용자 입력
    if prompt := st.chat_input("메시지 입력..."):
        # 사용자 메시지 표시
        with st.chat_message("user"):
            st.markdown(prompt)
        # 메시지 저장
        add_message("user", prompt)
        # 현재 단계에 맞는 처리
        process_step(st.session_state.step, prompt)
        
if __name__ == "__main__":
    run_app()
