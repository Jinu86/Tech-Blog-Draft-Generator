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
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("chat_history", [])
    
# 채팅 기록에 메시지 추가
def add_chat_message(role, content):
    st.session_state.chat_history.append({"role": role, "content": content})

# 확인 질문 분석 함수
def check_confirm_intent(user_input):
    confirm_phrases = ["네", "좋아요", "확인", "다음", "진행", "맞아요", "맞습니다", "넵", "알겠습니다", "그렇게 해주세요"]
    return any(phrase in user_input.lower() for phrase in confirm_phrases)

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

    # 사이드바 - 진행 상황
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

    # 초기 메시지 추가 (첫 실행 시)
    if len(st.session_state.chat_history) == 0:
        if step == 1:
            initial_message = "안녕하세요! 기술 블로그 초안 작성을 도와드리겠습니다. 어떤 주제로 블로그를 작성하고 싶으신가요?"
            add_chat_message("assistant", initial_message)

    # 채팅 히스토리 표시
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 초안 생성 후 표시
    if step == 6 and st.session_state.draft and len(st.session_state.chat_history) > 0:
        st.markdown("### 📄 작성된 초안")
        st.code(st.session_state.draft, language="markdown")
        st.download_button(
            label="📥 마크다운 파일로 다운로드",
            data=st.session_state.draft,
            file_name="blog_draft.md",
            mime="text/markdown"
        )

    # 사용자 입력 처리
    if prompt := st.chat_input("메시지 입력..."):
        # 사용자 입력을 채팅 기록에 추가
        add_chat_message("user", prompt)
        
        # 단계별 처리
        if step == 1:  # 주제 입력
            # 첫 단계에서는 입력한 내용을 주제로 사용
            topic = prompt.strip()
            st.session_state.topic = topic
            
            # 주제에 대한 확인 메시지 생성
            confirm_prompt = react_prompt(f"주제 입력: {topic}", "사용자 입력 내용을 확인하고, 이 주제에 대한 이해가 맞는지 물어보세요.")
            confirm_message = ask_gemini(confirm_prompt)
            add_chat_message("assistant", confirm_message)
            
            # 다음 단계로 진행 여부 메시지 추가 (사용자 응답 기다림)
            st.session_state.history.append(("주제", topic))
            st.session_state.waiting_confirm = True
            
        elif step == 2:  # 키워드 선택
            # 이전 응답이 확인이면 키워드 추천 진행, 아니면 키워드 처리
            if st.session_state.get("waiting_confirm", False):
                if check_confirm_intent(prompt):
                    # 키워드 추천 진행
                    keyword_prompt = react_prompt(f"주제: {st.session_state.topic}", "추천 키워드 제시 + 선택 유도")
                    keyword_suggestion = ask_gemini(keyword_prompt)
                    add_chat_message("assistant", keyword_suggestion)
                    st.session_state.waiting_confirm = False
                else:
                    # 아직 확인이 안됐으면 주제 단계로 유지
                    st.session_state.step = 1
                    topic_feedback = ask_gemini(react_prompt(f"사용자 응답: {prompt}", "사용자가 주제를 확정하지 않았습니다. 더 명확한 주제를 요청하세요."))
                    add_chat_message("assistant", topic_feedback)
            else:
                # 키워드 입력을 처리
                keywords = prompt.strip()
                confirm_prompt = react_prompt(f"입력 키워드: {keywords}", "키워드를 리스트로 정리하고 맞는지 물어보세요")
                confirm = ask_gemini(confirm_prompt)
                add_chat_message("assistant", confirm)
                
                st.session_state.keywords = keywords
                st.session_state.history.append(("키워드", keywords))
                st.session_state.step = 3
                st.session_state.waiting_confirm = True
                
        elif step == 3:  # 독자층/스타일 선택
            if st.session_state.get("waiting_confirm", False):
                if check_confirm_intent(prompt):
                    # 독자층 질문 진행
                    audience_prompt = "3️⃣ 이 글을 읽을 예상 독자는 누구인가요? (예: 초심자, 실무자, 발표용 등)"
                    add_chat_message("assistant", audience_prompt)
                    st.session_state.waiting_confirm = False
                else:
                    # 다시 키워드 단계로
                    st.session_state.step = 2
                    keyword_feedback = ask_gemini(react_prompt(f"사용자 응답: {prompt}", "사용자가 키워드를 확정하지 않았습니다. 다시 키워드를 요청하세요."))
                    add_chat_message("assistant", keyword_feedback)
            else:
                # 독자층 처리
                audience = prompt.strip()
                confirm = ask_gemini(react_prompt(f"입력: {audience}", "이 독자층이 맞는지 재확인 질문"))
                add_chat_message("assistant", confirm)
                
                st.session_state.audience = audience
                st.session_state.history.append(("스타일", audience))
                st.session_state.step = 4
                st.session_state.waiting_confirm = True
                
        elif step == 4:  # 글 구조 선택
            if st.session_state.get("waiting_confirm", False):
                if check_confirm_intent(prompt):
                    # 글 구조 질문 진행
                    structure_prompt = "4️⃣ 원하는 글의 구조는 어떻게 되시나요? (예: 문제→해결, 서론→본문→결론 등)"
                    add_chat_message("assistant", structure_prompt)
                    st.session_state.waiting_confirm = False
                else:
                    # 다시 독자층 단계로
                    st.session_state.step = 3
                    audience_feedback = ask_gemini(react_prompt(f"사용자 응답: {prompt}", "사용자가 독자층을 확정하지 않았습니다. 다시 독자층을 요청하세요."))
                    add_chat_message("assistant", audience_feedback)
            else:
                # 구조 처리
                structure = prompt.strip()
                example = ask_gemini(react_prompt(f"구조: {structure}", "이 구조로 짧은 예시 문단을 생성하고 사용자 확인 요청"))
                add_chat_message("assistant", example)
                
                st.session_state.structure = structure
                st.session_state.history.append(("구조", structure))
                st.session_state.step = 5
                st.session_state.waiting_confirm = True
                
        elif step == 5:  # 소제목 구성
            if st.session_state.get("waiting_confirm", False):
                if check_confirm_intent(prompt):
                    # 소제목 제안 진행
                    heading_prompt = react_prompt(
                        f"주제: {st.session_state.topic}, 키워드: {st.session_state.keywords}, 구조: {st.session_state.structure}",
                        "소제목을 4~6개 추천하고 사용자에게 수정할 수 있도록 하세요."
                    )
                    heading_suggestion = ask_gemini(heading_prompt)
                    add_chat_message("assistant", heading_suggestion)
                    st.session_state.waiting_confirm = False
                else:
                    # 다시 구조 단계로
                    st.session_state.step = 4
                    structure_feedback = ask_gemini(react_prompt(f"사용자 응답: {prompt}", "사용자가 구조를 확정하지 않았습니다. 다시 구조를 요청하세요."))
                    add_chat_message("assistant", structure_feedback)
            else:
                # 소제목 처리
                headings = prompt.strip()
                confirm = "✅ 소제목을 확인했어요. 이대로 초안을 작성할까요? ('네' 또는 '좋아요'로 대답해주세요)"
                add_chat_message("assistant", confirm)
                
                st.session_state.headings = headings
                st.session_state.history.append(("소제목", headings))
                st.session_state.waiting_confirm = True
                
        elif step == 6:  # 초안 작성
            if not st.session_state.draft:
                # 초안 작성 시작
                draft_message = "✨ 초안을 작성 중입니다. 잠시만 기다려주세요..."
                add_chat_message("assistant", draft_message)
                
                with st.spinner("GPT가 마크다운 블로그 초안을 작성 중입니다..."):
                    draft_prompt = react_prompt(
                        f"주제: {st.session_state.topic}\n키워드: {st.session_state.keywords}\n스타일: {st.session_state.audience}\n구조: {st.session_state.structure}\n소제목: {st.session_state.headings}",
                        "위 정보를 기반으로 마크다운 형식의 기술 블로그 초안을 작성하세요. 자연스럽고 논리적인 흐름이 중요하며, 필요한 경우 코드 블록도 포함하세요."
                    )
                    draft = ask_gemini(draft_prompt)
                
                st.session_state.draft = draft
                completion_message = "📝 초안 작성이 완료되었습니다! 마크다운 형식으로 다운로드하거나, 추가 수정 사항이 있으면 알려주세요."
                add_chat_message("assistant", completion_message)
            else:
                # 피드백 처리
                feedback_prompt = react_prompt(f"사용자 피드백: {prompt}, 초안: {st.session_state.draft[:200]}...", 
                                              "사용자의 피드백에 응답하고, 필요한 경우 도움을 제공하세요.")
                feedback_response = ask_gemini(feedback_prompt)
                add_chat_message("assistant", feedback_response)
                
        # 대화 내용 갱신
        st.experimental_rerun()

if __name__ == "__main__":
    run_app()
