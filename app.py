import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Gemini API 키 설정
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 시스템 프롬프트
REACT_SYSTEM_PROMPT = """
당신은 기술 블로그 작성을 도와주는 챗봇입니다.
당신은 ReAct 방식(Reasoning + Acting)을 사용합니다.
각 단계에서 사용자의 입력을 해석하고, 당신이 이해한 내용이 맞는지 다시 물어본 후 사용자 확인을 받은 다음에만 다음 단계로 넘어갑니다.

사용자 입력이 모호하거나 불명확할 경우 반드시 명확하게 다시 물어보세요.
사용자의 의도를 스스로 판단하지 말고, 반드시 확인하세요.

진행 순서는 다음과 같습니다:
1. [주제 파악]
2. [키워드 추천 및 선택]
3. [문체/대상 스타일 선택]
4. [글의 구조 제안 및 확정]
5. [소제목 및 흐름 구성]
6. [초안 작성]

각 단계에서는 다음과 같은 패턴을 따르세요:
- 🧐 Reasoning: 사용자의 입력을 바탕으로 당신이 이해한 내용을 정리합니다.
- ⚙️ Acting: 이해한 내용을 사용자에게 보여주고, 맞는지 물어봅니다.
- ✅ 사용자 확인 이후에만 다음 단계로 진행하세요.
"""

# 단계별 프롬프트 템플릿
PROMPT_TOPIC_QUESTION = """
안녕하세요! 저는 기술 블로그 초안 작성을 도와드리는 챗봇입니다. 😊
먼저, 어떤 주제로 블로그를 작성하고 싶으신가요?
간단히 말씀해 주세요.
"""

PROMPT_TOPIC_CONFIRM = """
🧐 사용자의 답변을 바탕으로 제가 이해한 주제는 다음과 같습니다:  
**"{inferred_topic}"**

⚙️ 이 주제로 블로그를 작성하시는 게 맞을까요?
맞으면 \"네\", 아니면 다시 말씀해주세요.
"""

PROMPT_KEYWORD_QUESTION = """
주제 \"**{topic}**\"와 관련해서 아래와 같은 키워드를 추천드려요:

🔎 추천 키워드:
{recommended_keywords}

이 중에서 다루고 싶은 키워드를 **복수로 선택**해주시고,
추천 키워드에 없더라도 추가하고 싶은 키워드가 있다면 자유롭게 말씀해주세요!
예: \"API, Mock 서버, 실습 예제\"
"""

PROMPT_KEYWORD_CONFIRM = """
🧐 제가 이해한 최종 키워드는 다음과 같습니다:  
{selected_keywords}

⚙️ 이 키워드를 중심으로 글을 작성해도 괜찮을까요?
수정하거나 추가하고 싶은 키워드가 있다면 알려주세요!
"""

PROMPT_STYLE_QUESTION = """
이번엔 블로그의 스타일을 정해볼게요.
아래는 참고할 수 있는 예시입니다:

- 형식: 튜토리얼, 기술 리뷰, 문제 해결 사례
- 문체: 친근한, 공식적인, 중립적
- 독자 대상: 초보자, 중급 개발자, 전문가

예시에서 골라도 좋고, 자유롭게 원하는 스타일로 작성해주셔도 괜찮습니다.
예: \"튜토리얼 형식, 친근한 톤, 초보자 대상\"
"""

PROMPT_STYLE_CONFIRM = """
🧐 제가 이해한 스타일은 다음과 같습니다:

- 형식: **{format_style}**
- 문체: **{tone}**
- 대상 독자: **{audience}**

⚙️ 이 스타일로 글을 작성해도 괜찮을까요?
자유롭게 수정하거나 추가하고 싶은 요소가 있다면 말씀해주세요.
"""

PROMPT_STRUCTURE_SUGGEST = """
위의 주제, 키워드, 스타일을 바탕으로 아래와 같은 글 구조를 제안드려요:

📝 제안된 구조:
{suggested_structure}

⚙️ 이 구조는 참고용이니, 마음껏 수정하셔도 좋아요!
섹션을 추가하거나 순서를 바꾸고 싶으시면 알려주세요.
"""

PROMPT_SUBTITLES_CONFIRM = """
아래는 각 섹션의 소제목입니다:

📌 소제목 목록:
{finalized_subtitles}

⚙️ 이 흐름대로 글을 작성해도 괜찮을까요?
수정하거나 추가하고 싶은 항목이 있다면 말씀해주세요!
"""

PROMPT_DRAFT_SECTION = """
✍️ 섹션 \"**{section_title}**\"에 대해 다음과 같은 초안을 작성해봤어요:

```
{generated_content}
```

⚙️ 괜찮으신가요?
내용을 바꾸고 싶거나, 더 추가하고 싶은 내용이 있다면 알려주세요!
"""

# Gemini 모델 불러오기
def get_chat_model():
    return genai.GenerativeModel("gemini-pro-1.5")

# 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.step = "topic_question"
    st.session_state.collected = {}

# 챗 UI
st.title("🧠 기술 블로그 초안 생성 챗봇")
st.markdown("---")

# 메시지 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 챗봇 메시지 전송 함수
def bot_say(message):
    st.session_state.messages.append({"role": "assistant", "content": message})
    with st.chat_message("assistant"):
        st.markdown(message)

# 사용자 메시지 처리 함수
def user_say():
    user_input = st.chat_input("메시지를 입력하세요")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        handle_input(user_input)

# 단계별 처리 로직
def handle_input(user_input):
    step = st.session_state.step
    model = get_chat_model()

    if step == "topic_question":
        st.session_state.step = "topic_confirm"
        st.session_state.collected["user_topic"] = user_input

        prompt = f"""
{REACT_SYSTEM_PROMPT}

사용자 입력: "{user_input}"

위 입력을 기반으로 기술 블로그 주제를 추론해 한 문장으로 요약하고, 다음 질문 형식으로 출력:
\n\n예시: \n🧠 사용자의 입력을 바탕으로 제가 이해한 주제는 다음과 같습니다: \"Postman 사용법\"\n⚙️ 이 주제로 블로그를 작성하시는 게 맞을까요?
"""
        response = model.generate_content(prompt)
        inferred_text = response.text
        bot_say(inferred_text)

    elif step == "topic_confirm":
        if "네" in user_input:
            bot_say("좋아요! 이제 관련 키워드를 추천드릴게요.")
            st.session_state.step = "keyword_question"
        else:
            bot_say("주제를 다시 말씀해주세요.")
            st.session_state.step = "topic_question"

# 첫 질문 표시
if not st.session_state.messages:
    bot_say(PROMPT_TOPIC_QUESTION)

# 사용자 입력 대기
user_say()
