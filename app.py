import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from enum import Enum

# Step 상수 정의
class Step(Enum):
    TOPIC_QUESTION = "topic_question"
    TOPIC_CONFIRM = "topic_confirm"
    KEYWORD_QUESTION = "keyword_question"
    KEYWORD_CONFIRM = "keyword_confirm"
    STYLE_QUESTION = "style_question"
    STYLE_CONFIRM = "style_confirm"
    FLOW_SUGGEST = "flow_suggest"           # 새로운 단계: 글 흐름 제안
    FLOW_CONFIRM = "flow_confirm"           # 새로운 단계: 글 흐름 확인
    SECTION_EDIT = "section_edit"           # 새로운 단계: 섹션 수정
    INTRO_WRITE = "intro_write"             # 새로운 단계: 도입부 작성
    INTRO_CONFIRM = "intro_confirm"         # 새로운 단계: 도입부 확인
    SECTION_WRITE = "section_write"         # 새로운 단계: 섹션 작성
    SECTION_CONFIRM = "section_confirm"     # 새로운 단계: 섹션 확인
    FULL_DRAFT = "full_draft"
    DONE = "done"

# 환경 변수 로드
load_dotenv()

# Gemini API 키 설정
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 시스템 프롬프트
REACT_SYSTEM_PROMPT = """
당신은 기술 블로그 작성을 도와주는 챗봇입니다.
사용자의 입력을 이해하고, 자연스러운 대화를 통해 사용자가 블로그 글을 작성할 수 있도록 도와주세요.

사용자의 의견과 요청을 항상 확인하고, 모호하거나 불명확한 내용은 추가 질문을 통해 명확히 해주세요.
다음 단계로 넘어가기 전에 항상 현재 내용이 맞는지 사용자에게 확인을 받으세요.

블로그 작성은 다음 순서로 진행됩니다:
1. 주제 파악하기
2. 키워드 추천 및 선택하기
3. 문체와 스타일 설정하기
4. 글의 흐름 제안하기
5. 도입부 작성하기
6. 각 섹션 작성하기
7. 전체 초안 확인하기

기술 블로그 작성 시 다음 사항을 고려해주세요:
- 기술적 정확성을 유지하세요.
- 실제 작동하는 코드 예제를 포함하세요.
- 다른 기술이나 접근법과 비교 분석해주세요.
- 실무에서의 활용 사례를 포함하세요.
- 이전 섹션과의 일관성을 유지하세요.

사용자와 자연스러운 대화를 통해 단계별로 블로그 작성을 도와주세요.
모든 응답은 구조화된 형식(1, 2, 3 번호 매기기)이나 특수 이모지 없이 자연스러운 대화체로 작성해주세요.
"""

# 단계별 프롬프트 템플릿

PROMPT_TOPIC_QUESTION = """
안녕하세요! 저는 기술 블로그 초안 작성을 도와드리는 챗봇입니다. 😊
먼저, 어떤 주제로 블로그를 작성하고 싶으신가요?
간단히 말씀해 주세요.
"""

PROMPT_TOPIC_CONFIRM = """
제가 이해한 주제는 다음과 같습니다:  
**"{inferred_topic}"**

이 주제로 블로그를 작성하시는 게 맞을까요?
맞으면 "네", 아니면 다시 말씀해주세요.
"""

PROMPT_KEYWORD_QUESTION = """
주제 "**{topic}**"와 관련해서 아래와 같은 키워드를 추천드려요:

🔎 추천 키워드:
{recommended_keywords}

이 중에서 다루고 싶은 키워드를 **복수로 선택**해주시고,
추천 키워드에 없더라도 추가하고 싶은 키워드가 있다면 자유롭게 말씀해주세요!
예: "API, Mock 서버, 실습 예제"
"""

PROMPT_KEYWORD_CONFIRM = """
제가 이해한 최종 키워드는 다음과 같습니다:  
{selected_keywords}

이 키워드를 중심으로 글을 작성해도 괜찮을까요?
수정하거나 추가하고 싶은 키워드가 있다면 알려주세요!
"""

PROMPT_STYLE_QUESTION = """
이번엔 블로그의 스타일을 정해볼게요.
아래는 참고할 수 있는 예시입니다:

- 형식: 튜토리얼, 기술 리뷰, 문제 해결 사례
- 문체: 친근한, 공식적인, 중립적
- 독자 대상: 초보자, 중급 개발자, 전문가

예시에서 골라도 좋고, 자유롭게 원하는 스타일로 작성해주셔도 괜찮습니다.
예: "튜토리얼 형식, 친근한 톤, 초보자 대상"
"""

PROMPT_STYLE_CONFIRM = """
제가 이해한 스타일은 다음과 같습니다:

- 형식: **{format_style}**
- 문체: **{tone}**
- 대상 독자: **{audience}**

이 스타일로 글을 작성해도 괜찮을까요?
자유롭게 수정하거나 추가하고 싶은 요소가 있다면 말씀해주세요.
"""

PROMPT_FLOW_SUGGEST = """
위의 주제, 키워드, 스타일을 바탕으로 아래와 같은 글 흐름을 제안드려요:

📝 제안된 흐름:
{suggested_flow}

이 흐름은 참고용이니, 마음껏 수정하셔도 좋아요!
섹션을 추가하거나 순서를 바꾸고 싶으시면 알려주세요.
"""

PROMPT_FLOW_CONFIRM = """
아래는 각 섹션의 흐름입니다:

흐름 목록:
{finalized_flow}

이 흐름대로 글을 작성해도 괜찮을까요?
수정하거나 추가하고 싶은 항목이 있다면 말씀해주세요!
"""

PROMPT_SECTION_EDIT = """
섹션 "{section_title}"에 대해 다음과 같은 수정을 제안해드릴게요:

```
{suggested_changes}
```

이 수정이 마음에 드시나요?
수정하거나 다시 작성하고 싶으면 말씀해주세요!
"""

PROMPT_INTRO_WRITE = """
이 글의 서론 부분인 "{section_title}"에 대한 초안을 작성해주세요.

다음 요소를 포함해주세요:
1. 주제에 대한 간결한 소개와 중요성
2. 독자가 이 글을 읽어야 하는 이유
3. 글에서 다룰 내용에 대한 간략한 개요
4. 독자의 관심을 끌 수 있는 흥미로운 시작점

주제: {topic}
키워드: {keywords}
스타일: {style}
"""

PROMPT_INTRO_CONFIRM = """
제가 이해한 도입부는 다음과 같습니다:

```
{intro_content}
```

이 도입부로 글을 작성해도 괜찮을까요?
수정하거나 추가하고 싶은 요소가 있다면 말씀해주세요.
"""

PROMPT_SECTION_WRITE = """
이 글의 본문 부분인 "{section_title}"에 대한 초안을 작성해주세요.

다음 요소를 포함해주세요:
1. 해당 섹션의 핵심 개념 설명
2. 실제 작동하는 코드 예제와 설명
3. 다른 접근법과의 비교 분석
4. 실무 적용 사례 또는 예시

이전 섹션 내용을 참고하여 일관성을 유지하세요:
{previous_sections}

주제: {topic}
키워드: {keywords}
스타일: {style}
"""

PROMPT_SECTION_CONFIRM = """
제가 이해한 섹션은 다음과 같습니다:

```
{section_content}
```

이 섹션으로 진행해도 괜찮을까요?
수정하거나 추가하고 싶은 요소가 있다면 말씀해주세요.
"""

# 수정 요청에 대한 프롬프트
PROMPT_REVISION = """
다음 섹션의 초안을 수정해주세요:
섹션 제목: {section_title}

사용자 요청: {user_request}

기존 초안:
{original_draft}

이전 섹션 내용:
{previous_sections}

수정 시 다음 사항을 고려해주세요:
1. 사용자의 요청사항을 자연스럽게 반영해주세요. 특히 "여기만 바꿔줘", "이 부분을 수정해줘" 등 특정 부분만 수정하라는 요청에 주의해주세요.
2. 기술적 정확성을 유지하면서도 이해하기 쉽게 작성해주세요.
3. 글의 전체적인 흐름과 일관성을 유지해주세요.
4. 코드 예제가 있다면 정확하고 실행 가능하게 수정해주세요.
5. 기존 초안의 좋은 부분은 그대로 유지해주세요.
6. 사용자가 특정 부분만 수정을 요청했다면, 그 부분만 수정하고 나머지는 그대로 두세요.

주제: {topic}
키워드: {keywords}
스타일: {style}
"""

# Gemini 모델 불러오기
def get_chat_model():
    return genai.GenerativeModel("gemini-1.5-pro")

# 전체 초안 표시 함수
def show_full_draft():
    subtitles = st.session_state.collected.get("finalized_flow", [])
    full_draft = ""
    
    # 제목 생성
    topic = st.session_state.collected.get('user_topic', '')
    full_draft += f"# {topic}\n\n"
    
    # 각 섹션 내용 합치기
    for subtitle in subtitles:
        content = st.session_state.generated_drafts.get(subtitle, "")
        full_draft += f"## {subtitle}\n{content}\n\n"
    
    # 전체 초안을 세션 상태에 저장
    st.session_state.full_draft = full_draft
    
    # 전체 초안 표시
    st.session_state.step = Step.DONE.value
    bot_say(f"모든 초안 작성을 완료했어요! 아래는 전체 초안입니다:")
    
    # 복사 가능한 코드 블록으로 전체 초안 표시
    with st.expander("📋 전체 초안 (클릭하여 복사하기)", expanded=True):
        st.code(full_draft, language="markdown")
        st.info("위 코드 블록을 클릭하면 전체 내용을 복사할 수 있습니다.")
    
    bot_say("필요한 경우 수정하거나 복사해서 사용하세요. '전체 초안 보기'라고 입력하시면 언제든지 다시 볼 수 있습니다.")

# 사이드바 진행 단계 표시
with st.sidebar:
    st.markdown("### 🧭 진행 단계")
    steps = [
        ("topic", "1. 주제 입력"),
        ("keyword", "2. 키워드 선택"),
        ("style", "3. 스타일 설정"),
        ("flow", "4. 글 흐름 제안"),
        ("intro", "5. 도입부 작성"),
        ("section", "6. 섹션 작성"),
        ("full_draft", "7. 전체 초안 확인")
    ]
    current_step = st.session_state.step
    for key, label in steps:
        if current_step.startswith(key):
            # 현재 단계는 파란색 글씨, 연한 파란색 배경, 화살표 아이콘 추가
            st.markdown(f"""
            <div style="
                margin-left: 0px; 
                padding: 5px 10px; 
                background-color: #E6F0FF; 
                color: #0066CC; 
                font-weight: bold; 
                font-size: 16px;
                border-radius: 5px;
                margin-bottom: 5px;
            ">→ {label}</div>
            """, unsafe_allow_html=True)
        else:
            # 다른 단계는 기본 스타일
            st.markdown(f"""
            <div style="
                padding: 5px 10px;
                margin-bottom: 5px;
            ">{label}</div>
            """, unsafe_allow_html=True)

# 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.step = Step.TOPIC_QUESTION.value
    st.session_state.collected = {}
    st.session_state.generated_drafts = {}
    st.session_state.draft_index = 0
    st.session_state.initialized = False

# 타이핑 인디케이터를 위한 상태
if "is_typing" not in st.session_state:
    st.session_state.is_typing = False

# 챗 UI
st.title("🧠 기술 블로그 초안 생성 챗봇")
st.markdown("---")

# CSS 애니메이션 추가 - 챗봇 작성중 애니메이션
st.markdown("""
<style>
@keyframes blink-typing {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 1; }
}

@keyframes bounce-dots {
    0%, 20% { transform: translateY(0); }
    50% { transform: translateY(-4px); }
    80%, 100% { transform: translateY(0); }
}

.typing-indicator {
    color: #888888;
    font-size: 14px;
    padding: 5px 10px;
    border-radius: 15px;
    background-color: #f1f1f1;
    display: inline-block;
    margin-bottom: 5px;
}

.typing-text {
    font-style: italic;
    animation: blink-typing 1.2s infinite;
}

.dots {
    display: inline-block;
    position: relative;
    margin-left: 5px;
}

.dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: #888888;
    margin: 0 1px;
    animation: bounce-dots 1.5s infinite;
}

.dot:nth-child(2) {
    animation-delay: 0.2s;
}

.dot:nth-child(3) {
    animation-delay: 0.4s;
}
</style>
""", unsafe_allow_html=True)

# 메시지 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 챗봇 타이핑 인디케이터 표시
if st.session_state.is_typing:
    with st.chat_message("assistant"):
        st.markdown('<div class="typing-indicator"><span class="typing-text">챗봇이 작성하고 있어요</span><span class="dots"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span></div>', unsafe_allow_html=True)

# 챗봇 메시지 전송 함수
def bot_say(message):
    st.session_state.messages.append({"role": "assistant", "content": message})
    st.session_state.is_typing = False
    with st.chat_message("assistant"):
        st.markdown(message)

# 사용자 메시지 처리 함수
def user_say():
    user_input = st.chat_input("메시지를 입력하세요")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.is_typing = True
        with st.chat_message("user"):
            st.markdown(user_input)
        st.rerun()

# AI 모델에 요청하고 응답 받는 공통 함수
def process_model_request(prompt):
    try:
        model = get_chat_model()
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        error_msg = f"API 호출 중 오류가 발생했습니다: {str(e)}"
        return error_msg

# 타이핑 상태이고 처리할 메시지가 있는 경우 처리
if st.session_state.is_typing and len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
    user_input = st.session_state.messages[-1]["content"]
    handle_input(user_input)
    st.rerun()

# 첫 질문 표시 (초기화 상태 확인)
if not st.session_state.messages and not st.session_state.initialized:
    st.session_state.initialized = True
    bot_say(PROMPT_TOPIC_QUESTION)

# 사용자 입력 대기
user_say()