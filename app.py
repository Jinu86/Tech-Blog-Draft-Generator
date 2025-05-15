import streamlit as st
from google.generativeai import GenerativeModel
import google.generativeai as genai
import time
import os

# Gemini API 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = GenerativeModel("gemini-pro")

# 세션 상태 초기화 함수
def init_session():
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "user_inputs" not in st.session_state:
        st.session_state.user_inputs = {}

# 챗봇 메시지 출력 함수
def bot(message):
    with st.chat_message("assistant"):
        st.markdown(message)

# 사용자 메시지 출력 함수
def user(message):
    with st.chat_message("user"):
        st.markdown(message)

# 프롬프트 설계 함수 (단계별)
def generate_prompt():
    inputs = st.session_state.user_inputs
    style = inputs.get("style", "일반적인 개발자 대상")
    structure = inputs.get("structure", "서론-목차-본문-결론")
    keywords = ", ".join(inputs.get("keywords", []))
    subtitles = "\n".join(f"- {s}" for s in inputs.get("subtitles", []))
    topic = inputs.get("topic", "")

    return f"""
당신은 기술 블로그 작성 도우미 챗봇입니다. 사용자가 주제를 입력하면 아래와 같은 흐름으로 블로그 초안 작성을 도와주세요. 각 단계는 반드시 질문 → 응답 → 요약 확인 → 다음 질문 형태로 ReAct 방식으로 진행되어야 합니다.

1. 주제 확인 → 키워드 추천 및 복수 선택 유도
2. 예상 독자 기반 스타일 선택 (초심자/실무자 등)
3. 글 구조 선택 (예시 포함)
4. 소제목 추천 및 편집
5. 초안 작성 (Markdown)

현재까지 사용자의 입력은 다음과 같습니다:

- 주제: {topic}
- 키워드: {keywords}
- 예상 독자 및 스타일: {style}
- 글 구조: {structure}
- 소제목: {subtitles}

이 정보를 바탕으로 기술 블로그 초안을 Markdown 형식으로 작성해주세요. 각 섹션은 간결하고 논리적으로 구성되며, 너무 딱딱하지 않게 자연스러운 설명으로 이루어져야 합니다. 중복 설명은 피하고, 실제 예제나 코드가 있다면 간단히 포함해도 좋습니다. 마지막에는 "이 내용이 만족스러우신가요?"라고 사용자 피드백을 유도하세요.
"""

# 메인 앱 시작
st.set_page_config(page_title="기술 블로그 작성 챗봇", layout="centered")
st.title("🧠 기술 블로그 초안 생성기 (Gemini + Streamlit)")

init_session()

# 챗봇 질문 흐름
step = st.session_state.step
chat_history = st.session_state.chat_history
user_inputs = st.session_state.user_inputs

# 사용자 입력 받기
user_input = st.chat_input("질문에 답해주세요")

# 기존 채팅 히스토리 렌더링
for role, msg in chat_history:
    with st.chat_message(role):
        st.markdown(msg)

# 각 단계 처리
if step == 1:
    if not chat_history:
        bot("안녕하세요! 기술 블로그 챗봇입니다. 먼저, 작성하고 싶은 블로그의 주제를 간단히 알려주세요.")
    if user_input:
        user(user_input)
        user_inputs["topic"] = user_input
        chat_history.append(("user", user_input))
        bot(f"감사합니다! 입력하신 주제는 다음과 같습니다: \n\n**{user_input}**\n\n이 주제가 맞으신가요? 맞다면 '네', 아니라면 다시 입력해주세요.")
        chat_history.append(("assistant", f"감사합니다! 입력하신 주제는 다음과 같습니다: **{user_input}**\n\n이 주제가 맞으신가요?"))
        st.session_state.step = 1.1

elif step == 1.1:
    if user_input:
        user(user_input)
        chat_history.append(("user", user_input))
        if "네" in user_input:
            bot("좋아요! 이제 이 주제와 관련된 키워드를 추천드릴게요. 잠시만 기다려주세요...")
            time.sleep(1)
            prompt = f"'{user_inputs['topic']}'이라는 주제에 관련된 기술 블로그 키워드를 5~7개 추천해주세요."
            response = model.generate_content(prompt)
            keywords = [k.strip("- ") for k in response.text.strip().split("\n") if k.strip()]
            user_inputs["recommended_keywords"] = keywords
            bot("다음 중에서 사용하고 싶은 키워드를 복수 선택하거나, 추가로 입력하고 싶은 키워드를 말씀해주세요:\n\n" + "\n".join(f"- {k}" for k in keywords))
            st.session_state.step = 2
        else:
            bot("그럼 주제를 다시 입력해주세요.")
            st.session_state.step = 1

elif step == 2:
    if user_input:
        user(user_input)
        chat_history.append(("user", user_input))
        confirm_prompt = f"다음은 사용자가 입력한 키워드입니다: '{user_input}'. 쉼표가 없어도 키워드 리스트로 파악하여 정리해줘."
        response = model.generate_content(confirm_prompt)
        parsed_keywords = [k.strip("- ") for k in response.text.strip().split("\n") if k.strip()]
        user_inputs["keywords"] = parsed_keywords
        bot(f"제가 이해한 키워드는 다음과 같아요:\n\n{', '.join(parsed_keywords)}\n\n이 키워드들이 맞나요? 맞다면 '네'라고 답해주세요. 아니면 다시 수정해주세요.")
        st.session_state.step = 2.1

elif step == 2.1:
    if user_input:
        user(user_input)
        chat_history.append(("user", user_input))
        if "네" in user_input:
            bot("좋습니다! 이제 예상 독자를 기준으로 글의 스타일을 정해볼게요.\n예: 초심자 대상, 실무자 대상, 기술 발표용 등. 어떤 스타일로 작성할까요?")
            st.session_state.step = 3
        else:
            bot("그럼 키워드를 다시 입력해주세요.")
            st.session_state.step = 2

# 이후 단계도 동일한 ReAct 흐름으로 연결되며 구성됨...

# 예: 마지막 단계에서 초안 생성
if step == 6:
    prompt = generate_prompt()
    bot("초안을 작성 중입니다. 잠시만 기다려주세요...")
    response = model.generate_content(prompt)
    st.session_state.user_inputs["draft"] = response.text
    bot(response.text)
    bot("이 내용이 만족스러우신가요? 수정하고 싶은 부분이 있으면 알려주세요!")
    st.session_state.step = 6.1

# 재시작 옵션
with st.sidebar:
    if st.button("🔄 전체 대화 초기화"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
