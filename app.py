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

# 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.step = Step.TOPIC_QUESTION.value
    st.session_state.collected = {}
    st.session_state.generated_drafts = {}
    st.session_state.draft_index = 0

# 타이핑 인디케이터를 위한 상태
if "is_typing" not in st.session_state:
    st.session_state.is_typing = False
    st.session_state.processed = True

# 챗 UI
st.title("🧠 기술 블로그 초안 생성 챗봇")
st.markdown("---")

# CSS 애니메이션 추가 - 챗봇 작성중 애니메이션
st.markdown("""
<style>
@keyframes bounce-dots {
    0%, 20% { transform: translateY(0); }
    50% { transform: translateY(-4px); }
    80%, 100% { transform: translateY(0); }
}

.typing-indicator {
    color: #888888;
    font-size: 14px;
    padding: 8px 12px;
    border-radius: 18px;
    background-color: #f1f1f1;
    display: inline-flex;
    align-items: center;
    margin-bottom: 5px;
}

.typing-text {
    font-style: italic;
}

.dots {
    display: flex;
    margin-left: 5px;
}

.dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: #888888;
    margin: 0 1px;
    display: inline-block;
    animation: bounce-dots 1.5s infinite;
}

.dot:nth-child(2) {
    animation-delay: 0.2s;
}

.dot:nth-child(3) {
    animation-delay: 0.4s;
}

/* 단계 표시 스타일 */
.step-current {
    margin-left: 0px; 
    padding: 5px 10px; 
    background-color: #E6F0FF; 
    color: #0066CC; 
    font-weight: bold; 
    font-size: 16px;
    border-radius: 5px;
    margin-bottom: 5px;
}

.step-other {
    padding: 5px 10px;
    margin-bottom: 5px; 
    color: #555555;
}
</style>
""", unsafe_allow_html=True)

# 챗봇 메시지 전송 함수
def bot_say(message):
    st.session_state.messages.append({"role": "assistant", "content": message})
    st.session_state.is_typing = False
    st.session_state.processed = True
    # 메시지는 메시지 출력 루프에서 표시됨

# AI 모델에 요청하고 응답 받는 공통 함수
def process_model_request(prompt):
    try:
        # 이미 타이핑 상태이면 재설정하지 않음 
        # (handle_input 내부에서 호출될 때는 이미 타이핑 상태이므로 재실행하지 않음)
        model = get_chat_model()
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        error_msg = f"API 호출 중 오류가 발생했습니다: {str(e)}"
        return error_msg

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
    
    # 현재 단계에 해당하는 prefix 찾기
    current_step = st.session_state.step
    current_prefix = ""
    
    # STYLE_CONFIRM일 때 flow로 표시하는 버그 수정
    if current_step == Step.STYLE_CONFIRM.value:
        current_prefix = "style"
    # FLOW_SUGGEST/FLOW_CONFIRM일 때 flow로 표시
    elif current_step in [Step.FLOW_SUGGEST.value, Step.FLOW_CONFIRM.value]:
        current_prefix = "flow"
    # INTRO_WRITE/INTRO_CONFIRM일 때 intro로 표시
    elif current_step in [Step.INTRO_WRITE.value, Step.INTRO_CONFIRM.value]:
        current_prefix = "intro"
    # SECTION_WRITE/SECTION_CONFIRM/SECTION_EDIT일 때 section으로 표시
    elif current_step in [Step.SECTION_WRITE.value, Step.SECTION_CONFIRM.value, Step.SECTION_EDIT.value]:
        current_prefix = "section"
    # FULL_DRAFT/DONE일 때 full_draft로 표시
    elif current_step in [Step.FULL_DRAFT.value, Step.DONE.value]:
        current_prefix = "full_draft"
    # 그 외에는 기존 로직 사용
    else:
        for prefix, _ in steps:
            if current_step.startswith(prefix):
                current_prefix = prefix
                break
    
    # 각 단계 표시
    for key, label in steps:
        if key == current_prefix:
            st.markdown(f'<div class="step-current">→ {label}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="step-other">{label}</div>', unsafe_allow_html=True)

# 메시지 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 챗봇 타이핑 인디케이터 표시
if st.session_state.is_typing:
    with st.chat_message("assistant"):
        st.markdown('<div class="typing-indicator"><span class="typing-text">챗봇이 작성하고 있어요</span><span class="dots"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span></div>', unsafe_allow_html=True)

# 첫 질문 표시 (아직 메시지가 없는 경우)
if not st.session_state.messages:
    bot_say(PROMPT_TOPIC_QUESTION)

# 사용자 메시지 처리 함수
def user_say():
    user_input = st.chat_input("메시지를 입력하세요")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # 타이핑 인디케이터 표시 전 재실행
        st.session_state.is_typing = True
        st.session_state.processed = False
        st.rerun()

# 타이핑 상태이고 미처리된 메시지가 있는 경우
if st.session_state.is_typing and not st.session_state.processed and len(st.session_state.messages) > 0:
    if st.session_state.messages[-1]["role"] == "user":
        user_input = st.session_state.messages[-1]["content"]
        # 처리 완료 플래그 설정 (중복 처리 방지)
        st.session_state.processed = True
        # 실제 메시지 처리
        handle_input(user_input)

# 사용자 입력 대기
user_say()

# 사용자 입력 처리 핵심 함수
def handle_input(user_input):
    # 단계별 처리 로직
    step = st.session_state.step
    
    # '전체 초안 보기' 요청 처리
    if any(word in user_input.lower() for word in ["전체 초안", "모든 초안", "전체 내용", "결과 보기"]):
        if hasattr(st.session_state, 'full_draft') and st.session_state.full_draft:
            st.session_state.step = Step.DONE.value
            bot_say("네, 전체 초안을 다시 보여드릴게요:")
            with st.expander("📋 전체 초안 (클릭하여 복사하기)", expanded=True):
                st.code(st.session_state.full_draft, language="markdown")
                st.info("위 코드 블록을 클릭하면 전체 내용을 복사할 수 있습니다.")
            return
        else:
            bot_say("아직 전체 초안이 작성되지 않았어요. 모든 단계를 완료하면 전체 초안을 볼 수 있습니다.")
            return
    
    # 도입부 확인 단계
    if step == Step.INTRO_CONFIRM.value:
        handle_intro_confirm(user_input)
        return
        
    # 섹션 확인 단계
    elif step == Step.SECTION_CONFIRM.value:
        handle_section_confirm(user_input)
        return
    
    # 흐름 확인 단계
    elif step == Step.FLOW_CONFIRM.value:
        handle_flow_confirm(user_input)
        return
        
    # 글 흐름 제안 단계
    elif step == Step.FLOW_SUGGEST.value:
        handle_flow_suggestion(user_input)
        return
        
    # 주제 질문 단계
    elif step == Step.TOPIC_QUESTION.value:
        # 주제 저장
        inferred_topic = user_input.strip()
        st.session_state.collected["user_topic"] = inferred_topic
        
        # 주제 확인 요청
        st.session_state.step = Step.TOPIC_CONFIRM.value
        confirm_message = PROMPT_TOPIC_CONFIRM.format(inferred_topic=inferred_topic)
        bot_say(confirm_message)
        return
        
    # 주제 확인 단계
    elif step == Step.TOPIC_CONFIRM.value:
        # 수정 요청이 있는지 확인
        if any(word in user_input.lower() for word in ["수정", "바꿔", "다시", "다른", "변경", "고치", "아니"]):
            bot_say("네, 주제를 다시 말씀해주시겠어요?")
            st.session_state.step = Step.TOPIC_QUESTION.value
            return
            
        # 진행 의사가 있는지 확인
        if any(word in user_input.lower() for word in ["네", "좋아", "괜찮", "진행", "시작", "다음"]):
            prompt = f"""
{REACT_SYSTEM_PROMPT}

주제 "{st.session_state.collected.get('user_topic', '')}"와 관련된 키워드를 5-8개 추천해주세요.
각 키워드는 쉼표로 구분해서 목록으로 표시해주시고, 전문적인 기술 블로그에 어울리는 키워드를 선택해주세요.

예시: "Docker, 컨테이너화, 마이크로서비스, DevOps, CI/CD, Kubernetes"
"""
            # 키워드 추천 받기
            st.session_state.step = Step.KEYWORD_QUESTION.value
            response_text = process_model_request(prompt)
            # 키워드 질문 메시지 표시
            formatted_prompt = PROMPT_KEYWORD_QUESTION.format(
                topic=st.session_state.collected.get('user_topic', ''),
                recommended_keywords=response_text
            )
            bot_say(formatted_prompt)
            return
            
        # 응답이 명확하지 않은 경우
        bot_say("""주제에 대해 어떻게 생각하시나요?
- 진행하시려면 '네', '좋아요', '진행할게요'라고 말씀해주세요.
- 수정이 필요하시다면 '수정', '다시', '바꿔' 등의 말씀을 해주세요.""")
        return
    
    # 키워드 질문 단계
    elif step == Step.KEYWORD_QUESTION.value:
        # 사용자가 선택한 키워드 저장
        selected_keywords = user_input.strip()
        # 키워드 원본 저장
        st.session_state.collected["user_keywords_raw"] = selected_keywords
        
        # 키워드 리스트로 변환하여 저장
        keyword_list = [kw.strip() for kw in selected_keywords.split(',')]
        formatted_keywords = ", ".join([f"**{kw}**" for kw in keyword_list])
        st.session_state.collected["user_keywords"] = keyword_list
        
        # 키워드 확인 요청
        st.session_state.step = Step.KEYWORD_CONFIRM.value
        confirm_message = PROMPT_KEYWORD_CONFIRM.format(selected_keywords=formatted_keywords)
        bot_say(confirm_message)
        return
        
    # 키워드 확인 단계
    elif step == Step.KEYWORD_CONFIRM.value:
        # 수정 요청이 있는지 확인
        if any(word in user_input.lower() for word in ["수정", "바꿔", "다시", "다른", "변경", "고치", "아니"]):
            bot_say("네, 키워드를 다시 선택해주시겠어요?")
            st.session_state.step = Step.KEYWORD_QUESTION.value
            
            # 이전에 추천된 키워드 목록 기반으로 메시지 재구성
            prompt = PROMPT_KEYWORD_QUESTION.format(
                topic=st.session_state.collected.get('user_topic', ''),
                recommended_keywords="이전과 같은 키워드 중에서 선택하시거나 새롭게 말씀해주세요."
            )
            bot_say(prompt)
            return
            
        # 진행 의사가 있는지 확인
        if any(word in user_input.lower() for word in ["네", "좋아", "괜찮", "진행", "시작", "다음"]):
            # 스타일 질문으로 넘어가기
            st.session_state.step = Step.STYLE_QUESTION.value
            bot_say(PROMPT_STYLE_QUESTION)
            return
            
        # 응답이 명확하지 않은 경우
        bot_say("""키워드에 대해 어떻게 생각하시나요?
- 진행하시려면 '네', '좋아요', '진행할게요'라고 말씀해주세요.
- 수정이 필요하시다면 '수정', '다시', '바꿔' 등의 말씀을 해주세요.""")
        return
    
    # 스타일 질문 단계
    elif step == Step.STYLE_QUESTION.value:
        # 스타일 정보 파싱
        user_style = user_input.strip()
        st.session_state.collected["user_style_raw"] = user_style
        
        # 스타일 파싱 시도
        format_style = "일반적인 형식"
        tone = "중립적인 톤"
        audience = "일반 독자"
        
        # 형식 파싱
        format_keywords = ["튜토리얼", "가이드", "리뷰", "분석", "사례", "연구", "개요", "입문서"]
        for keyword in format_keywords:
            if keyword in user_style:
                format_style = f"{keyword} 형식"
                break
                
        # 톤 파싱
        tone_keywords = {"친근": "친근한", "공식": "공식적인", "중립": "중립적인", "전문": "전문적인", "캐주얼": "캐주얼한"}
        for key, value in tone_keywords.items():
            if key in user_style:
                tone = f"{value} 톤"
                break
                
        # 독자 파싱
        audience_keywords = {"초보": "초보자", "입문": "입문자", "중급": "중급 개발자", "전문": "전문가", "시니어": "시니어 개발자"}
        for key, value in audience_keywords.items():
            if key in user_style:
                audience = f"{value} 대상"
                break
        
        # 파싱된 정보 저장
        st.session_state.collected["format_style"] = format_style
        st.session_state.collected["tone"] = tone
        st.session_state.collected["audience"] = audience
        
        # 스타일 확인 요청
        st.session_state.step = Step.STYLE_CONFIRM.value
        confirm_message = PROMPT_STYLE_CONFIRM.format(
            format_style=format_style,
            tone=tone,
            audience=audience
        )
        bot_say(confirm_message)
        return
    
    # 스타일 확인 단계
    elif step == Step.STYLE_CONFIRM.value:
        # 수정 요청이 있는지 확인
        if any(word in user_input.lower() for word in ["수정", "바꿔", "다시", "다른", "변경", "고치", "아니"]):
            bot_say("네, 스타일을 다시 입력해주시겠어요?")
            st.session_state.step = Step.STYLE_QUESTION.value
            return
            
        # 진행 의사가 있는지 확인
        if any(word in user_input.lower() for word in ["네", "좋아", "괜찮", "진행", "시작", "다음"]):
            # 바로 흐름 제안 프롬프트 생성
            prompt = f"""
{REACT_SYSTEM_PROMPT}

주제: {st.session_state.collected.get('user_topic', '')}
키워드: {st.session_state.collected.get('user_keywords_raw', '')}
스타일: {st.session_state.collected.get('user_style_raw', '')}

위 정보를 바탕으로 블로그의 글 흐름을 제안해주세요.
다음 가이드라인을 따라주세요:

1. 서론, 본문(2-3개 섹션), 결론의 기본 흐름을 포함해주세요.
2. 각 섹션은 명확하고 구체적인 제목을 가져야 합니다.
3. 제목만 나열해주세요.
4. 각 항목 앞에 번호를 붙여주세요(1., 2. 등).
5. 각 섹션에 [서론], [본문], [결론] 중 하나를 포함해주세요.
6. 마지막에 "이 흐름은 어떠신가요?"라고 물어봐주세요.

예시 형식:
1. [서론] Docker의 이해와 필요성
2. [본문] Docker 기본 개념과 작동 원리
3. [본문] Docker 실전 활용 사례
4. [본문] Docker와 다른 컨테이너 기술 비교
5. [결론] Docker의 미래와 학습 방향

이 흐름은 어떠신가요?
"""
            # 중요: 먼저 단계를 변경한 후 응답 생성
            st.session_state.step = Step.FLOW_SUGGEST.value
            response_text = process_model_request(prompt)
            st.session_state.collected["suggested_flow"] = response_text
            bot_say(response_text)
            return
            
        # 응답이 명확하지 않은 경우
        bot_say("""스타일에 대해 어떻게 생각하시나요?
- 진행하시려면 '네', '좋아요', '진행할게요'라고 말씀해주세요.
- 수정이 필요하시다면 '수정', '다시', '바꿔' 등의 말씀을 해주세요.""")
        return
        
    # 기타 상황에서는 안내 메시지
    bot_say("어떤 작업을 도와드릴까요?")

# 도입부 확인 단계 처리 함수
def handle_intro_confirm(user_input):
    user_input_lower = user_input.lower()
    
    # 수정 요청이 있는지 확인
    if any(word in user_input_lower for word in ["수정", "바꿔", "다시", "다른", "변경", "고치", "아니"]):
        # 수정 요청 처리
        section_title = st.session_state.current_section
        original_draft = st.session_state.draft_section_content
        
        # 수정 프롬프트 생성
        prompt = PROMPT_REVISION.format(
            section_title=section_title,
            user_request=user_input,
            original_draft=original_draft,
            previous_sections="",  # 첫 섹션이므로 이전 섹션 없음
            topic=st.session_state.collected.get('user_topic', ''),
            keywords=", ".join(st.session_state.collected.get('user_keywords', [])),
            style=f"{st.session_state.collected.get('format_style', '')} / {st.session_state.collected.get('tone', '')} / {st.session_state.collected.get('audience', '')}"
        )
        
        # 수정된 내용 요청
        bot_say("네, 도입부를 수정해볼게요...")
        revised_content = process_model_request(prompt)
        
        # 수정된 내용 저장
        st.session_state.draft_section_content = revised_content
        
        # 수정된 내용 확인 요청
        confirm_message = PROMPT_INTRO_CONFIRM.format(intro_content=revised_content)
        bot_say(confirm_message)
        return
    
    # 진행 의사가 있는지 확인
    if any(word in user_input_lower for word in ["네", "좋아", "괜찮", "진행", "시작", "다음"]):
        # 현재 섹션 내용 저장
        section_title = st.session_state.current_section
        section_content = st.session_state.draft_section_content
        st.session_state.generated_drafts[section_title] = section_content
        
        # 다음 섹션으로 이동
        flow_items = st.session_state.collected.get("finalized_flow", [])
        current_index = flow_items.index(section_title)
        
        # 마지막 섹션이 아니면 다음 섹션으로
        if current_index < len(flow_items) - 1:
            next_section = flow_items[current_index + 1]
            st.session_state.current_section = next_section
            
            # 이전 섹션 내용 수집
            previous_sections = []
            for i in range(current_index + 1):
                prev_title = flow_items[i]
                prev_content = st.session_state.generated_drafts.get(prev_title, "")
                if prev_content:
                    previous_sections.append(f"## {prev_title}\n{prev_content}")
            
            previous_sections_text = "\n\n".join(previous_sections)
            
            # 다음 섹션 작성 프롬프트 생성
            prompt = PROMPT_SECTION_WRITE.format(
                section_title=next_section,
                previous_sections=previous_sections_text,
                topic=st.session_state.collected.get('user_topic', ''),
                keywords=", ".join(st.session_state.collected.get('user_keywords', [])),
                style=f"{st.session_state.collected.get('format_style', '')} / {st.session_state.collected.get('tone', '')} / {st.session_state.collected.get('audience', '')}"
            )
            
            # 섹션 작성 요청
            st.session_state.step = Step.SECTION_WRITE.value
            bot_say(f"이제 '{next_section}' 섹션을 작성해볼게요...")
            
            # API 호출하여 섹션 생성
            section_content = process_model_request(prompt)
            
            # 섹션 내용 저장
            st.session_state.draft_section_content = section_content
            
            # 섹션 확인 요청
            st.session_state.step = Step.SECTION_CONFIRM.value
            confirm_message = PROMPT_SECTION_CONFIRM.format(section_content=section_content)
            bot_say(confirm_message)
            return
        else:
            # 모든 섹션이 완료되었으면 전체 초안 표시
            show_full_draft()
            return
    
    # 응답이 명확하지 않은 경우
    bot_say("""도입부에 대해 어떻게 생각하시나요?
- 진행하시려면 '네', '좋아요', '진행할게요'라고 말씀해주세요.
- 수정이 필요하시다면 '수정', '다시', '바꿔' 등의 말씀을 해주세요.""")

# 섹션 확인 단계 처리 함수
def handle_section_confirm(user_input):
    user_input_lower = user_input.lower()
    
    # 수정 요청이 있는지 확인
    if any(word in user_input_lower for word in ["수정", "바꿔", "다시", "다른", "변경", "고치", "아니"]):
        # 수정 요청 처리
        section_title = st.session_state.current_section
        original_draft = st.session_state.draft_section_content
        
        # 이전 섹션 내용 수집
        flow_items = st.session_state.collected.get("finalized_flow", [])
        current_index = flow_items.index(section_title)
        
        previous_sections = []
        for i in range(current_index):
            prev_title = flow_items[i]
            prev_content = st.session_state.generated_drafts.get(prev_title, "")
            if prev_content:
                previous_sections.append(f"## {prev_title}\n{prev_content}")
        
        previous_sections_text = "\n\n".join(previous_sections)
        
        # 수정 프롬프트 생성
        prompt = PROMPT_REVISION.format(
            section_title=section_title,
            user_request=user_input,
            original_draft=original_draft,
            previous_sections=previous_sections_text,
            topic=st.session_state.collected.get('user_topic', ''),
            keywords=", ".join(st.session_state.collected.get('user_keywords', [])),
            style=f"{st.session_state.collected.get('format_style', '')} / {st.session_state.collected.get('tone', '')} / {st.session_state.collected.get('audience', '')}"
        )
        
        # 수정된 내용 요청
        bot_say("네, 내용을 수정해볼게요...")
        revised_content = process_model_request(prompt)
        
        # 수정된 내용 저장
        st.session_state.draft_section_content = revised_content
        
        # 수정된 내용 확인 요청
        confirm_message = PROMPT_SECTION_CONFIRM.format(section_content=revised_content)
        bot_say(confirm_message)
        return
    
    # 진행 의사가 있는지 확인
    if any(word in user_input_lower for word in ["네", "좋아", "괜찮", "진행", "시작", "다음"]):
        # 현재 섹션 내용 저장
        section_title = st.session_state.current_section
        section_content = st.session_state.draft_section_content
        st.session_state.generated_drafts[section_title] = section_content
        
        # 다음 섹션으로 이동
        flow_items = st.session_state.collected.get("finalized_flow", [])
        current_index = flow_items.index(section_title)
        
        # 마지막 섹션이 아니면 다음 섹션으로
        if current_index < len(flow_items) - 1:
            next_section = flow_items[current_index + 1]
            st.session_state.current_section = next_section
            
            # 이전 섹션 내용 수집
            previous_sections = []
            for i in range(current_index + 1):
                prev_title = flow_items[i]
                prev_content = st.session_state.generated_drafts.get(prev_title, "")
                if prev_content:
                    previous_sections.append(f"## {prev_title}\n{prev_content}")
            
            previous_sections_text = "\n\n".join(previous_sections)
            
            # 다음 섹션 작성 프롬프트 생성
            prompt = PROMPT_SECTION_WRITE.format(
                section_title=next_section,
                previous_sections=previous_sections_text,
                topic=st.session_state.collected.get('user_topic', ''),
                keywords=", ".join(st.session_state.collected.get('user_keywords', [])),
                style=f"{st.session_state.collected.get('format_style', '')} / {st.session_state.collected.get('tone', '')} / {st.session_state.collected.get('audience', '')}"
            )
            
            # 섹션 작성 요청
            st.session_state.step = Step.SECTION_WRITE.value
            bot_say(f"이제 '{next_section}' 섹션을 작성해볼게요...")
            
            # API 호출하여 섹션 생성
            section_content = process_model_request(prompt)
            
            # 섹션 내용 저장
            st.session_state.draft_section_content = section_content
            
            # 섹션 확인 요청
            st.session_state.step = Step.SECTION_CONFIRM.value
            confirm_message = PROMPT_SECTION_CONFIRM.format(section_content=section_content)
            bot_say(confirm_message)
            return
        else:
            # 모든 섹션이 완료되었으면 전체 초안 표시
            show_full_draft()
            return
    
    # 응답이 명확하지 않은 경우
    bot_say("""섹션 내용에 대해 어떻게 생각하시나요?
- 진행하시려면 '네', '좋아요', '진행할게요'라고 말씀해주세요.
- 수정이 필요하시다면 '수정', '다시', '바꿔' 등의 말씀을 해주세요.""")

# 흐름 확인 단계 처리 함수
def handle_flow_confirm(user_input):
    user_input_lower = user_input.lower()
    
    # 수정 요청이 있는지 확인
    if any(word in user_input_lower for word in ["수정", "바꿔", "다시", "다른", "변경", "고치", "아니"]):
        # 흐름 수정을 위한 옵션 제시
        st.session_state.flow_rejection = True
        col1, col2 = st.columns(2)
        with col1:
            if st.button("새 흐름 제안 받기"):
                st.session_state.flow_rejection = False
                # 새로운 흐름 제안을 위한 프롬프트 생성
                prompt = f"""
{REACT_SYSTEM_PROMPT}

주제: {st.session_state.collected.get('user_topic', '')}
키워드: {st.session_state.collected.get('user_keywords_raw', '')}
스타일: {st.session_state.collected.get('user_style_raw', '')}

위 정보를 바탕으로 블로그의 새로운 글 흐름을 제안해주세요. 이전에 제안된 흐름과는 다른 새로운 구성으로 제안해주세요.
다음 가이드라인을 따라주세요:

1. 서론, 본문(2-3개 섹션), 결론의 기본 흐름을 포함해주세요.
2. 각 섹션은 명확하고 구체적인 제목을 가져야 합니다.
3. 제목만 나열해주세요.
4. 각 항목 앞에 번호를 붙여주세요(1., 2. 등).
5. 각 섹션에 [서론], [본문], [결론] 중 하나를 포함해주세요.
6. 마지막에 "이 흐름은 어떠신가요?"라고 물어봐주세요.
"""
                st.session_state.step = Step.FLOW_SUGGEST.value
                response_text = process_model_request(prompt)
                st.session_state.collected["suggested_flow"] = response_text
                bot_say(response_text)
                return

        with col2:
            if st.button("직접 흐름 수정하기"):
                st.session_state.flow_rejection = False
                bot_say("""다음과 같은 형식으로 각 섹션의 흐름을 직접 수정해주세요:

[서론] 제목
[본문] 제목
[본문] 제목
[결론] 제목

각 줄에 하나의 소제목을 입력해주세요.""")
                # 사용자 입력 모드로 설정
                st.session_state.user_flow_input = True
                return
            
        # 사용자가 흐름을 거부했지만 아직 버튼을 누르지 않은 경우 안내 메시지 표시
        if hasattr(st.session_state, 'flow_rejection') and st.session_state.flow_rejection:
            bot_say("위 옵션 중 하나를 선택해주세요.")
            return
    
    # 진행 의사가 있는지 확인
    if any(word in user_input_lower for word in ["네", "좋아", "괜찮", "진행", "시작", "다음"]):
        # 첫 번째 섹션(서론)으로 이동
        flow_items = st.session_state.collected.get("finalized_flow", [])
        
        if flow_items:
            first_section = flow_items[0]
            
            # 도입부 작성 프롬프트 생성
            prompt = PROMPT_INTRO_WRITE.format(
                section_title=first_section,
                topic=st.session_state.collected.get('user_topic', ''),
                keywords=", ".join(st.session_state.collected.get('user_keywords', [])),
                style=f"{st.session_state.collected.get('format_style', '')} / {st.session_state.collected.get('tone', '')} / {st.session_state.collected.get('audience', '')}"
            )
            
            # 단계 변경 및 챗봇에게 도입부 작성 요청
            st.session_state.step = Step.INTRO_WRITE.value
            bot_say(f"좋습니다! 이제 첫 번째 섹션인 '{first_section}'에 대한 도입부를 작성해볼게요...")
            
            # API 호출하여 도입부 생성
            intro_content = process_model_request(prompt)
            
            # 도입부 저장
            st.session_state.current_section = first_section
            st.session_state.draft_section_content = intro_content
            
            # 도입부 확인 요청
            st.session_state.step = Step.INTRO_CONFIRM.value
            confirm_message = PROMPT_INTRO_CONFIRM.format(intro_content=intro_content)
            bot_say(confirm_message)
            return
        else:
            # 흐름 추출 실패 시
            bot_say("죄송합니다. 저장된 흐름을 처리하는 데 문제가 있었습니다. 다시 시도해주세요.")
            st.session_state.step = Step.FLOW_SUGGEST.value
            return
    
    # 응답이 명확하지 않은 경우
    bot_say("""흐름 목록에 대해 어떻게 생각하시나요?
- 진행하시려면 '네', '좋아요', '진행할게요'라고 말씀해주세요.
- 수정이 필요하시다면 '수정', '다시', '바꿔' 등의 말씀을 해주세요.""")

# 글 흐름 제안 단계 처리 함수
def handle_flow_suggestion(user_input):
    user_input_lower = user_input.lower()
    
    # 수정 요청이 있는지 확인
    if any(word in user_input_lower for word in ["수정", "바꿔", "다시", "다른", "변경", "고치", "아니"]):
        # 사용자에게 옵션 제시 (버튼 UI 사용)
        st.session_state.flow_rejection = True
        col1, col2 = st.columns(2)
        with col1:
            if st.button("새 흐름 제안 받기"):
                st.session_state.flow_rejection = False
                # 새로운 흐름 제안을 위한 프롬프트 생성
                prompt = f"""
{REACT_SYSTEM_PROMPT}

주제: {st.session_state.collected.get('user_topic', '')}
키워드: {st.session_state.collected.get('user_keywords_raw', '')}
스타일: {st.session_state.collected.get('user_style_raw', '')}

위 정보를 바탕으로 블로그의 새로운 글 흐름을 제안해주세요. 이전에 제안된 흐름과는 다른 새로운 구성으로 제안해주세요.
다음 가이드라인을 따라주세요:

1. 서론, 본문(2-3개 섹션), 결론의 기본 흐름을 포함해주세요.
2. 각 섹션은 명확하고 구체적인 제목을 가져야 합니다.
3. 제목만 나열해주세요.
4. 각 항목 앞에 번호를 붙여주세요(1., 2. 등).
5. 각 섹션에 [서론], [본문], [결론] 중 하나를 포함해주세요.
6. 마지막에 "이 흐름은 어떠신가요?"라고 물어봐주세요.
"""
                st.session_state.step = Step.FLOW_SUGGEST.value
                response_text = process_model_request(prompt)
                st.session_state.collected["suggested_flow"] = response_text
                bot_say(response_text)
                return

        with col2:
            if st.button("직접 흐름 수정하기"):
                st.session_state.flow_rejection = False
                bot_say("""다음과 같은 형식으로 각 섹션의 흐름을 직접 수정해주세요:

[서론] 제목
[본문] 제목
[본문] 제목
[결론] 제목

각 줄에 하나의 소제목을 입력해주세요.""")
                # 사용자 입력 모드로 설정
                st.session_state.user_flow_input = True
                return
            
        # 사용자가 흐름을 거부했지만 아직 버튼을 누르지 않은 경우 안내 메시지 표시
        if hasattr(st.session_state, 'flow_rejection') and st.session_state.flow_rejection:
            bot_say("위 옵션 중 하나를 선택해주세요.")
            return
    
    # 사용자 직접 입력 모드인 경우
    if hasattr(st.session_state, 'user_flow_input') and st.session_state.user_flow_input:
        # 사용자 입력을 처리하여 흐름 항목으로 변환
        flow_items = user_input.strip().split('\n')
        flow_items = [item.strip() for item in flow_items if item.strip()]
        
        if flow_items:
            # 사용자 입력 모드 해제
            st.session_state.user_flow_input = False
            # 흐름 저장
            st.session_state.collected["finalized_flow"] = flow_items
            # 확인 메시지 생성
            flow_list = "\n".join([f"{i+1}. {item}" for i, item in enumerate(flow_items)])
            confirm_message = PROMPT_FLOW_CONFIRM.format(finalized_flow=flow_list)
            # 단계 변경 및 메시지 표시
            st.session_state.step = Step.FLOW_CONFIRM.value
            bot_say(confirm_message)
            return
        else:
            # 입력이 비어있는 경우
            bot_say("입력이 비어있는 것 같습니다. 각 줄에 하나의 소제목을 입력해주세요.")
            return
    
    # 진행 의사가 있는지 확인 (기본 흐름 수용)
    if any(word in user_input_lower for word in ["네", "좋아", "괜찮", "진행", "시작", "다음", "예", "그래", "맞아"]):
        # 제안된 흐름에서 항목 추출
        suggested_flow = st.session_state.collected.get("suggested_flow", "")
        flow_items = []
        
        for line in suggested_flow.split('\n'):
            # 번호가 있는 줄만 추출
            if any(f"{i}." in line for i in range(1, 10)) and any(tag in line for tag in ["[서론]", "[본문]", "[결론]"]):
                # 번호 제거하고 내용만 저장
                content = line.split('.', 1)[1].strip() if '.' in line else line.strip()
                flow_items.append(content)
        
        # 흐름 저장
        st.session_state.collected["finalized_flow"] = flow_items
        
        # 첫 번째 섹션(서론)으로 이동
        if flow_items:
            first_section = flow_items[0]
            st.session_state.step = Step.INTRO_WRITE.value
            
            # 도입부 작성 프롬프트 생성
            prompt = PROMPT_INTRO_WRITE.format(
                section_title=first_section,
                topic=st.session_state.collected.get('user_topic', ''),
                keywords=", ".join(st.session_state.collected.get('user_keywords', [])),
                style=f"{st.session_state.collected.get('format_style', '')} / {st.session_state.collected.get('tone', '')} / {st.session_state.collected.get('audience', '')}"
            )
            
            # 챗봇에게 도입부 작성 요청
            bot_say(f"좋습니다! 이제 첫 번째 섹션인 '{first_section}'에 대한 도입부를 작성해볼게요...")
            
            # API 호출하여 도입부 생성
            intro_content = process_model_request(prompt)
            
            # 도입부 저장
            st.session_state.current_section = first_section
            st.session_state.draft_section_content = intro_content
            
            # 도입부 확인 요청
            st.session_state.step = Step.INTRO_CONFIRM.value
            confirm_message = PROMPT_INTRO_CONFIRM.format(intro_content=intro_content)
            bot_say(confirm_message)
            return
        else:
            # 흐름 추출 실패 시
            bot_say("죄송합니다. 제안된 흐름을 처리하는 데 문제가 있었습니다. 다시 시도해주세요.")
            return
    
    # 위 조건에 해당하지 않는 경우 안내 메시지 표시
    bot_say("""제안된 흐름에 대해 어떻게 생각하시나요?
- 진행하시려면 '네', '좋아요', '진행할게요'라고 말씀해주세요.
- 수정이 필요하시다면 '수정', '다시', '바꿔' 등의 말씀을 해주세요.""")