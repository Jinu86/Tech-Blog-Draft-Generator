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
    STRUCTURE_SUGGEST = "structure_suggest"
    STRUCTURE_CONFIRM = "structure_confirm"
    SUBTITLE_CONFIRM = "subtitle_confirm"
    DRAFT_GENERATE = "draft_generate"
    DRAFT_CONFIRM = "draft_confirm"
    FULL_DRAFT = "full_draft"
    DONE = "done"

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

기술 블로그 작성 시 다음 지침을 따르세요:
1. 기술적 정확성: 모든 기술 정보와 개념 설명은 정확해야 합니다.
2. 코드 예제: 실제 작동하는 코드 예제를 포함하고, 각 부분에 대한 설명을 추가하세요.
3. 비교 분석: 다른 기술이나 접근법과 비교하여 장단점을 제시하세요.
4. 실제 사용 사례: 실무에서 어떻게 활용될 수 있는지 구체적인 예시를 포함하세요.
5. 일관성: 이전에 작성된 섹션의 내용과 일관성을 유지하세요.
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
예: "튜토리얼 형식, 친근한 톤, 초보자 대상"
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
✍️ 섹션 "**{section_title}**"에 대해 다음과 같은 초안을 작성해봤어요:

```
{generated_content}
```

⚙️ 괜찮으신가요?
내용을 바꾸고 싶거나, 더 추가하고 싶은 내용이 있다면 알려주세요!
"""

# 섹션 위치에 따른 맞춤형 프롬프트
PROMPT_INTRO_SECTION = """
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

PROMPT_BODY_SECTION = """
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

PROMPT_CONCLUSION_SECTION = """
이 글의 결론 부분인 "{section_title}"에 대한 초안을 작성해주세요.

다음 요소를 포함해주세요:
1. 글에서 다룬 핵심 내용 요약
2. 주요 시사점 또는 교훈
3. 독자가 다음으로 탐색할 수 있는 관련 주제 제안
4. 독자의 행동을 유도하는 마무리

이전 섹션 내용을 참고하여 일관성을 유지하세요:
{previous_sections}

주제: {topic}
키워드: {keywords}
스타일: {style}
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

# 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.step = Step.TOPIC_QUESTION.value
    st.session_state.collected = {}
    st.session_state.generated_drafts = {}
    st.session_state.draft_index = 0

# 사이드바 진행 단계 표시
with st.sidebar:
    st.markdown("### 🧭 진행 단계")
    steps = [
        ("topic", "1. 주제 입력"),
        ("keyword", "2. 키워드 선택"),
        ("style", "3. 스타일 설정"),
        ("structure", "4. 구조 제안"),
        ("subtitle", "5. 소제목 구성"),
        ("draft", "6. 초안 작성"),
        ("full_draft", "7. 전체 초안 확인")
    ]
    current_step = st.session_state.step
    for key, label in steps:
        if current_step.startswith(key):
            st.markdown(f"- **✅ {label}**")
        else:
            st.markdown(f"- {label}")

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

# AI 모델에 요청하고 응답 받는 공통 함수
def process_model_request(prompt):
    try:
        model = get_chat_model()
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        error_msg = f"API 호출 중 오류가 발생했습니다: {str(e)}"
        return error_msg

# 사용자 긍정 응답 확인 함수
def is_positive_response(user_input):
    # 입력이 없거나 매우 짧은 경우
    if not user_input or len(user_input) < 2:
        return None
    
    user_input_lower = user_input.lower()
    
    # 명확한 긍정 표현 (정확한 매칭)
    clear_positive = ["네", "예", "넵", "넹", "좋아요", "좋습니다", "괜찮아요", "괜찮습니다", "맞아요", "맞습니다"]
    for phrase in clear_positive:
        if phrase == user_input_lower or phrase + "." == user_input_lower or phrase + "!" == user_input_lower:
            return True
    
    # 부정 표현이 있는지 확인 (부정이 우선)
    negative_patterns = ["아니", "안 ", "않", "별로", "싫", "다시", "수정", "바꿔", "변경", "그렇지 않", "틀려", "다른"]
    for pattern in negative_patterns:
        if pattern in user_input_lower:
            return False
    
    # 긍정 표현이 있는지 확인 (단어 포함)
    positive_words = ["네", "예", "좋아", "좋은", "좋게", "좋다", "괜찮", "맞", "그렇", "동의", 
                      "진행", "계속", "넵", "웅", "응", "그래", "알겠", "오케이", "오키", "ok", "ㅇㅇ", "ㅇㅋ"]
    
    # 긍정 표현 점수 계산
    positive_score = 0
    for word in positive_words:
        if word in user_input_lower:
            positive_score += 1
    
    # 입력이 짧고 긍정 표현이 1개 이상 있으면 긍정으로 판단
    if len(user_input_lower) < 15 and positive_score > 0:
        return True
    
    # 입력이 길고 긍정 표현이 2개 이상 있으면 긍정으로 판단
    if len(user_input_lower) >= 15 and positive_score >= 2:
        return True
    
    # 문장 시작이 긍정 표현인 경우
    for word in ["네", "예", "좋아요", "괜찮아요", "맞아요"]:
        if user_input_lower.startswith(word):
            return True
    
    # 명확한 긍정/부정 표현이 없는 경우 None 반환
    return None

# 사용자 응답 처리 함수 (명확하지 않은 응답 처리)
def handle_confirmation(user_input, positive_action, negative_action, unclear_message=None):
    response = is_positive_response(user_input)
    
    if response is True:
        positive_action()
    elif response is False:
        negative_action()
    else:
        # 응답이 명확하지 않은 경우
        if unclear_message is None:
            unclear_message = "음, 제가 이해한 주제가 맞는지 잘 모르겠어요. 이 주제로 진행해도 괜찮을까요? 아니면 다른 주제를 원하시나요?"
        bot_say(unclear_message)
        # 현재 상태 유지 (다시 물어봄)

# 단계별 처리 로직
def handle_input(user_input):
    step = st.session_state.step

    # 주제 질문 단계
    if step == Step.TOPIC_QUESTION.value:
        st.session_state.step = Step.TOPIC_CONFIRM.value
        st.session_state.collected["user_topic"] = user_input

        prompt = f"""
{REACT_SYSTEM_PROMPT}

사용자 입력: "{user_input}"

위 입력을 기반으로 기술 블로그 주제를 추론하고, 다음 사항을 고려하여 응답해주세요:

1. 주제가 너무 광범위한 경우 (예: "React", "Python" 등):
   - 구체적인 주제나 관점을 제안해주세요
   - 예: "React의 컴포넌트 설계 패턴", "Python의 비동기 프로그래밍" 등

2. 주제가 구체적인 경우:
   - 이해한 내용을 정리하고 추가 정보가 필요한지 확인해주세요
   - 예: "React의 컴포넌트 설계에 대해 다루고 싶으신 것으로 이해했습니다. 컴포넌트의 어떤 측면에 초점을 맞추고 싶으신가요?"

3. 주제가 불명확한 경우:
   - 더 자세한 정보를 요청해주세요
   - 예: "어떤 기술이나 주제에 대해 다루고 싶으신지 좀 더 구체적으로 말씀해주시겠어요?"

응답 형식:
1. 이해한 내용 정리
2. 필요한 경우 구체화 요청 또는 추가 정보 요청
3. 사용자의 의도를 명확히 하기 위한 질문
"""
        inferred_text = process_model_request(prompt)
        bot_say(inferred_text)

    # 주제 확인 단계
    elif step == Step.TOPIC_CONFIRM.value:
        # 주제가 구체화가 필요한 경우
        if any(word in user_input.lower() for word in ["구체", "어떤", "?", "더", "자세"]):
            st.session_state.step = Step.TOPIC_QUESTION.value
            bot_say("네, 주제를 더 구체적으로 말씀해주시면 좋겠습니다.")
            return

        # 주제가 명확한 경우
        topic = st.session_state.collected.get("user_topic", "")
        prompt = f"""
{REACT_SYSTEM_PROMPT}

주제: "{topic}"

위 주제와 관련된 기술 블로그에 적합한 키워드를 추천해주세요.
다음 가이드라인을 따라주세요:

1. 총 8-10개의 키워드를 추천해주세요.
2. 키워드는 다음 카테고리를 포함하도록 해주세요:
   - 핵심 기술/개념 (2-3개)
   - 관련 도구/프레임워크 (2-3개)
   - 적용 사례/활용 분야 (2개)
   - 트렌드/이슈 (1-2개)
3. 각 키워드는 쉼표로 구분하고, 키워드만 나열해주세요.
4. 너무 일반적이거나 광범위한 키워드는 피해주세요.

예시 형식: "Docker, Kubernetes, 컨테이너 오케스트레이션, 마이크로서비스, CI/CD, DevOps, 클라우드 네이티브, 스케일링"
"""
        recommended_keywords = process_model_request(prompt)
        
        # 키워드를 정돈된 형식으로 변환
        keywords_list = [kw.strip() for kw in recommended_keywords.replace('"', '').split(',')]
        formatted_keywords = '\n'.join([f"- {kw}" for kw in keywords_list])
        
        # 키워드 추천 템플릿 사용
        message = PROMPT_KEYWORD_QUESTION.format(
            topic=topic,
            recommended_keywords=formatted_keywords
        )
        
        bot_say(message)
        st.session_state.step = Step.KEYWORD_QUESTION.value

    # 키워드 질문 단계
    elif step == Step.KEYWORD_QUESTION.value:
        st.session_state.collected["user_keywords_raw"] = user_input
        st.session_state.step = Step.KEYWORD_CONFIRM.value
        
        prompt = f"""
{REACT_SYSTEM_PROMPT}

주제: "{st.session_state.collected.get('user_topic', '')}"
사용자가 선택한 키워드: "{user_input}"

위 내용을 바탕으로 다음 작업을 수행해주세요:
1. 사용자가 선택한 키워드를 정리하여 깔끔한 목록으로 만들어주세요.
2. 쉼표나 기타 구분자로 나뉜 키워드를 각각 별도의 항목으로 처리해주세요.
3. 중복된 키워드는 제거해주세요.
4. 키워드 목록을 불릿 포인트(-)로 정리해주세요.
5. 마지막에 "이 키워드로 진행해도 될까요?"라고 물어봐주세요.

예시 출력 형식:
🧐 제가 이해한 최종 키워드는 다음과 같습니다:  
- 키워드1
- 키워드2
- 키워드3

⚙️ 이 키워드로 진행해도 될까요?
수정하거나 추가하고 싶은 키워드가 있다면 알려주세요!
"""
        
        response_text = process_model_request(prompt)
        bot_say(response_text)

    # 키워드 확인 단계
    elif step == Step.KEYWORD_CONFIRM.value:
        # 수정 요청이 있는지 확인
        if any(word in user_input.lower() for word in ["수정", "바꿔", "다시", "다른", "변경", "고치", "아니"]):
            bot_say("네, 키워드를 다시 선택해주시겠어요?")
            st.session_state.step = Step.KEYWORD_QUESTION.value
            return
            
        # 진행 의사가 있는지 확인
        if any(word in user_input.lower() for word in ["네", "좋아", "괜찮", "진행", "시작", "다음"]):
            bot_say("""이제 블로그의 스타일을 정해볼까요?

아래는 참고할 수 있는 예시입니다:

- 형식: 튜토리얼, 기술 리뷰, 문제 해결 사례
- 문체: 친근한, 공식적인, 중립적
- 독자 대상: 초보자, 중급 개발자, 전문가

예시에서 골라도 좋고, 자유롭게 원하는 스타일로 작성해주시겠어요?
예: "튜토리얼 형식, 친근한 톤, 초보자 대상" """)
            st.session_state.step = Step.STYLE_QUESTION.value
            return
            
        # 응답이 명확하지 않은 경우
        bot_say("""선택하신 키워드에 대해 어떻게 생각하시나요?
- 진행하시려면 '네', '좋아요', '진행할게요'라고 말씀해주세요.
- 수정이 필요하시다면 '수정', '다시', '바꿔' 등의 말씀을 해주세요.""")

    # 스타일 질문 단계
    elif step == Step.STYLE_QUESTION.value:
        st.session_state.collected["user_style_raw"] = user_input
        st.session_state.step = Step.STYLE_CONFIRM.value
        
        prompt = f"""
{REACT_SYSTEM_PROMPT}

사용자가 입력한 스타일: {user_input}

위 내용을 바탕으로 다음 작업을 수행해주세요:
1. 형식, 톤, 독자대상을 정리해주세요.
2. 각 항목을 명확하게 구분해주세요.
3. 마지막에 "이 스타일로 진행해도 될까요?"라고 물어봐주세요.

예시 출력 형식:
🧐 제가 이해한 스타일은 다음과 같습니다:

- 형식: **튜토리얼**
- 문체: **친근한**
- 대상 독자: **초보자**

⚙️ 이 스타일로 진행해도 될까요?
수정이 필요하시다면 말씀해주세요.
"""
        response_text = process_model_request(prompt)
        bot_say(response_text)

    # 스타일 확인 단계
    elif step == Step.STYLE_CONFIRM.value:
        # 수정 요청이 있는지 확인
        if any(word in user_input.lower() for word in ["수정", "바꿔", "다시", "다른", "변경", "고치", "아니"]):
            bot_say("네, 스타일을 다시 입력해주시겠어요?")
            st.session_state.step = Step.STYLE_QUESTION.value
            return
            
        # 진행 의사가 있는지 확인
        if any(word in user_input.lower() for word in ["네", "좋아", "괜찮", "진행", "시작", "다음"]):
            # 바로 구조 제안 프롬프트 생성
            prompt = f"""
{REACT_SYSTEM_PROMPT}

주제: {st.session_state.collected.get('user_topic', '')}
키워드: {st.session_state.collected.get('user_keywords_raw', '')}
스타일: {st.session_state.collected.get('user_style_raw', '')}

위 정보를 바탕으로 블로그의 전체 구조를 제안해주세요.
다음 가이드라인을 따라주세요:

1. 서론, 본문(2-3개 섹션), 결론의 기본 구조를 포함해주세요.
2. 각 섹션은 명확하고 구체적인 제목을 가져야 합니다.
3. 제목만 나열해주세요.
4. 마지막에 "이 구조는 어떠신가요?"라고 물어봐주세요.

예시 형식:
1. [서론] Docker의 이해와 필요성
2. [본문] Docker 기본 개념과 작동 원리
3. [본문] Docker 실전 활용 사례
4. [본문] Docker와 다른 컨테이너 기술 비교
5. [결론] Docker의 미래와 학습 방향

이 구조는 어떠신가요?
"""
            response_text = process_model_request(prompt)
            st.session_state.collected["suggested_structure"] = response_text
            st.session_state.step = Step.STRUCTURE_CONFIRM.value
            bot_say(response_text)
            return
            
        # 응답이 명확하지 않은 경우
        bot_say("""스타일에 대해 어떻게 생각하시나요?
- 진행하시려면 '네', '좋아요', '진행할게요'라고 말씀해주세요.
- 수정이 필요하시다면 '수정', '다시', '바꿔' 등의 말씀을 해주세요.""")

    # 구조 제안 단계
    elif step == Step.STRUCTURE_SUGGEST.value:
        # 이 단계는 이제 사용되지 않음 (스타일 확인 단계에서 바로 처리)
        pass

    # 구조 확인 단계
    elif step == Step.STRUCTURE_CONFIRM.value:
        # 사용자의 응답을 분석
        user_input_lower = user_input.lower()
        
        # 수정 요청이 있는지 확인
        if any(word in user_input_lower for word in ["수정", "바꿔", "다시", "다른", "변경", "고치", "아니"]):
            # 새로운 구조 제안을 위한 프롬프트 생성
            prompt = f"""
{REACT_SYSTEM_PROMPT}

주제: {st.session_state.collected.get('user_topic', '')}
키워드: {st.session_state.collected.get('user_keywords_raw', '')}
스타일: {st.session_state.collected.get('user_style_raw', '')}

위 정보를 바탕으로 블로그의 새로운 구조를 제안해주세요.
다음 가이드라인을 따라주세요:

1. 서론, 본문(2-3개 섹션), 결론의 기본 구조를 포함해주세요.
2. 각 섹션은 명확하고 구체적인 제목을 가져야 합니다.
3. 제목만 나열해주세요.
4. 마지막에 "이 구조는 어떠신가요?"라고 물어봐주세요.

예시 형식:
1. [서론] Docker의 이해와 필요성
2. [본문] Docker 기본 개념과 작동 원리
3. [본문] Docker 실전 활용 사례
4. [본문] Docker와 다른 컨테이너 기술 비교
5. [결론] Docker의 미래와 학습 방향

이 구조는 어떠신가요?
"""
            response_text = process_model_request(prompt)
            st.session_state.collected["suggested_structure"] = response_text
            bot_say(response_text)
            return
            
        # 진행 의사가 있는지 확인
        if any(word in user_input_lower for word in ["네", "좋아", "괜찮", "진행", "시작", "다음"]):
            suggested_structure = st.session_state.collected.get("suggested_structure", "")
            topic = st.session_state.collected.get('user_topic', '')
            style = st.session_state.collected.get('user_style_raw', '')
            
            bot_say(f"""좋습니다! '{topic}'에 대한 블로그를 {style} 스타일로 작성하기 위한 소제목을 정해볼까요?

제안된 구조를 바탕으로 각 섹션의 소제목을 작성해주세요.
예시 형식:
1. [서론] Docker의 이해와 필요성
2. [본문] Docker 기본 개념과 작동 원리
3. [본문] Docker 실전 활용 사례
4. [본문] Docker와 다른 컨테이너 기술 비교
5. [결론] Docker의 미래와 학습 방향

위와 같은 형식으로 각 섹션의 소제목을 작성해주시겠어요?
순서를 바꾸거나 섹션을 추가/삭제하셔도 됩니다.""")
            st.session_state.step = Step.SUBTITLE_CONFIRM.value

    # 소제목 확인 단계
    elif step == Step.SUBTITLE_CONFIRM.value:
        if not user_input:
            # 처음 이 단계에 진입했을 때
            suggested_structure = st.session_state.collected.get("suggested_structure", "")
            topic = st.session_state.collected.get('user_topic', '')
            style = st.session_state.collected.get('user_style_raw', '')
            
            bot_say(f"""'{topic}'에 대한 블로그를 {style} 스타일로 작성하기 위한 소제목을 정해볼까요?

제안된 구조를 바탕으로 각 섹션의 소제목을 작성해주세요.
예시 형식:
1. [서론] Docker의 이해와 필요성
2. [본문] Docker 기본 개념과 작동 원리
3. [본문] Docker 실전 활용 사례
4. [본문] Docker와 다른 컨테이너 기술 비교
5. [결론] Docker의 미래와 학습 방향

위와 같은 형식으로 각 섹션의 소제목을 작성해주시겠어요?
순서를 바꾸거나 섹션을 추가/삭제하셔도 됩니다.
소제목 추천이 필요하시다면 '추천해줘' 또는 '어떤것들이 있어?'라고 말씀해주세요.""")
            return

        # 추천 요청인지 확인 (이 부분을 먼저 체크)
        if any(word in user_input.lower() for word in ["추천", "어떤것", "뭐가", "보여", "예시", "예를"]):
            topic = st.session_state.collected.get('user_topic', '')
            style = st.session_state.collected.get('user_style_raw', '')
            keywords = st.session_state.collected.get('user_keywords_raw', '')
            
            # 추천 소제목 생성
            prompt = f"""
{REACT_SYSTEM_PROMPT}

주제: {topic}
키워드: {keywords}
스타일: {style}

위 정보를 바탕으로 블로그의 소제목을 추천해주세요.
다음 가이드라인을 따라주세요:

1. 서론, 본문(2-3개 섹션), 결론의 기본 구조를 포함해주세요.
2. 각 섹션은 명확하고 구체적인 제목을 가져야 합니다.
3. 제목만 나열해주세요.
4. 각 섹션에 [서론], [본문], [결론] 중 하나를 포함해주세요.

예시 형식:
1. [서론] Docker의 이해와 필요성
2. [본문] Docker 기본 개념과 작동 원리
3. [본문] Docker 실전 활용 사례
4. [본문] Docker와 다른 컨테이너 기술 비교
5. [결론] Docker의 미래와 학습 방향
"""
            recommended_subtitles = process_model_request(prompt)
            
            bot_say(f"""'{topic}'에 대한 블로그를 {style} 스타일로 작성하기 위한 소제목을 추천해드릴게요:

{recommended_subtitles}

이 중에서 마음에 드는 소제목을 선택하거나 수정해서 사용하셔도 됩니다.
소제목을 작성하시겠어요?""")
            return

        # 사용자가 소제목을 입력한 경우 (추천 요청이 아닌 경우에만 실행)
        subtitles = [s.strip() for s in user_input.split("\n") if s.strip()]
        
        # 소제목 형식 검증
        if not all(any(marker in s for marker in ["[서론]", "[본문]", "[결론]"]) for s in subtitles):
            bot_say("""소제목 형식이 올바르지 않습니다. 각 섹션에 [서론], [본문], [결론] 중 하나를 포함해주세요.

예시:
1. [서론] Docker의 이해와 필요성
2. [본문] Docker 기본 개념과 작동 원리
3. [본문] Docker 실전 활용 사례
4. [본문] Docker와 다른 컨테이너 기술 비교
5. [결론] Docker의 미래와 학습 방향

다시 작성해주시겠어요?""")
            return

        # 소제목 확인 메시지
        formatted_subtitles = "\n".join([f"{i+1}. {s}" for i, s in enumerate(subtitles)])
        topic = st.session_state.collected.get('user_topic', '')
        style = st.session_state.collected.get('user_style_raw', '')
        
        bot_say(f"""🧐 '{topic}'에 대한 블로그를 {style} 스타일로 작성하기 위한 소제목을 다음과 같이 이해했습니다:

{formatted_subtitles}

⚙️ 이 소제목으로 진행해도 될까요?
수정이 필요하다면 다시 작성해주세요.""")
        
        st.session_state.collected["finalized_subtitles"] = subtitles
        st.session_state.step = Step.SUBTITLE_CONFIRM.value

    # 소제목 확인 응답 처리
    elif step == Step.SUBTITLE_CONFIRM.value and user_input:
        # 수정 요청이 있는지 확인
        if any(word in user_input.lower() for word in ["수정", "바꿔", "다시", "다른", "변경", "고치", "아니"]):
            bot_say("네, 소제목을 다시 작성해주시겠어요?")
            st.session_state.step = Step.SUBTITLE_CONFIRM.value
            return
            
        # 진행 의사가 있는지 확인
        if any(word in user_input.lower() for word in ["네", "좋아", "괜찮", "진행", "시작", "다음"]):
            st.session_state.step = Step.DRAFT_GENERATE.value
            st.session_state.draft_index = 0
            topic = st.session_state.collected.get('user_topic', '')
            bot_say(f"좋습니다! '{topic}'에 대한 블로그 초안을 작성해드릴게요. 첫 번째 섹션부터 시작할까요?")
            handle_input("")  # 자동으로 첫 섹션 초안 생성 시작
            return
            
        # 응답이 명확하지 않은 경우
        bot_say("""소제목에 대해 어떻게 생각하시나요?
- 진행하시려면 '네', '좋아요', '진행할게요'라고 말씀해주세요.
- 수정이 필요하시다면 '수정', '다시', '바꿔' 등의 말씀을 해주세요.""")

    # 초안 생성 단계
    elif step == Step.DRAFT_GENERATE.value:
        subtitles = st.session_state.collected.get("finalized_subtitles", [])
        index = st.session_state.draft_index

        if index >= len(subtitles):
            st.session_state.step = Step.FULL_DRAFT.value
            handle_input("")  # 전체 초안 표시 자동 호출
            return

        current_section = subtitles[index]
        
        # 이전 섹션 내용 수집
        previous_sections = ""
        if index > 0:
            for i in range(index):
                prev_title = subtitles[i]
                prev_content = st.session_state.generated_drafts.get(prev_title, "")
                previous_sections += f"## {prev_title}\n{prev_content}\n\n"
        
        # 섹션 위치에 따른 프롬프트 선택
        section_prompt = ""
        if index == 0:
            # 첫 번째 섹션은 서론으로 간주
            section_prompt = PROMPT_INTRO_SECTION.format(
                section_title=current_section,
                topic=st.session_state.collected.get('user_topic', ''),
                keywords=st.session_state.collected.get('user_keywords_raw', ''),
                style=st.session_state.collected.get('user_style_raw', '')
            )
        elif index == len(subtitles) - 1:
            # 마지막 섹션은 결론으로 간주
            section_prompt = PROMPT_CONCLUSION_SECTION.format(
                section_title=current_section,
                previous_sections=previous_sections,
                topic=st.session_state.collected.get('user_topic', ''),
                keywords=st.session_state.collected.get('user_keywords_raw', ''),
                style=st.session_state.collected.get('user_style_raw', '')
            )
        else:
            # 중간 섹션은 본문으로 간주
            section_prompt = PROMPT_BODY_SECTION.format(
                section_title=current_section,
                previous_sections=previous_sections,
                topic=st.session_state.collected.get('user_topic', ''),
                keywords=st.session_state.collected.get('user_keywords_raw', ''),
                style=st.session_state.collected.get('user_style_raw', '')
            )
        
        # 시스템 프롬프트와 섹션 프롬프트 결합
        prompt = f"{REACT_SYSTEM_PROMPT}\n\n{section_prompt}"
        
        response_text = process_model_request(prompt)
        st.session_state.generated_drafts[current_section] = response_text
        st.session_state.step = Step.DRAFT_CONFIRM.value
        bot_say(f"✍️ 섹션 \"**{current_section}**\"의 초안입니다:\n\n{response_text}\n\n이 내용 괜찮으신가요? 수정하거나 다시 작성하고 싶으면 말씀해주세요.")

    # 초안 확인 단계
    elif step == Step.DRAFT_CONFIRM.value:
        response = is_positive_response(user_input)
        
        if response is True:
            st.session_state.draft_index += 1
            st.session_state.step = Step.DRAFT_GENERATE.value
            handle_input("")  # 다음 섹션 자동 호출
        elif response is None:
            # 응답이 명확하지 않은 경우
            bot_say("작성한 초안이 마음에 드시나요? 수정이 필요하시면 어떤 부분을 수정하면 좋을지 알려주세요.")
        else:
            current_section = list(st.session_state.generated_drafts.keys())[st.session_state.draft_index]
            original_draft = st.session_state.generated_drafts[current_section]
            
            # 이전 섹션 내용 수집
            subtitles = st.session_state.collected.get("finalized_subtitles", [])
            index = st.session_state.draft_index
            previous_sections = ""
            if index > 0:
                for i in range(index):
                    prev_title = subtitles[i]
                    prev_content = st.session_state.generated_drafts.get(prev_title, "")
                    previous_sections += f"## {prev_title}\n{prev_content}\n\n"
            
            # 자연어 피드백 분석을 위한 프롬프트 추가
            feedback_analysis_prompt = f"""
            사용자의 피드백을 분석하여 수정 요청을 이해해주세요.
            
            사용자 피드백: "{user_input}"
            
            이 피드백에서 사용자가 원하는 수정 사항을 파악하세요:
            1. 특정 부분만 수정을 원하는지 ("여기만", "이 부분만", "이 문단은" 등의 표현 확인)
            2. 전체적인 수정을 원하는지
            3. 추가 정보나 예시를 원하는지
            4. 기술적 정확성에 대한 수정을 원하는지
            5. 문체나 스타일 변경을 원하는지
            
            사용자의 의도를 최대한 자연스럽게 반영하여 수정해주세요.
            """
            
            # 수정 요청 프롬프트 생성
            revision_prompt = PROMPT_REVISION.format(
                section_title=current_section,
                user_request=user_input,
                original_draft=original_draft,
                previous_sections=previous_sections,
                topic=st.session_state.collected.get('user_topic', ''),
                keywords=st.session_state.collected.get('user_keywords_raw', ''),
                style=st.session_state.collected.get('user_style_raw', '')
            )
            
            # 시스템 프롬프트와 수정 프롬프트 결합
            prompt = f"{REACT_SYSTEM_PROMPT}\n\n{feedback_analysis_prompt}\n\n{revision_prompt}"
            
            response_text = process_model_request(prompt)
            st.session_state.generated_drafts[current_section] = response_text
            bot_say(f"🔁 다시 작성한 초안입니다:\n\n{response_text}\n\n이제 괜찮으신가요?")

    # 전체 초안 표시 단계
    elif step == Step.FULL_DRAFT.value:
        subtitles = st.session_state.collected.get("finalized_subtitles", [])
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
        bot_say(f"✅ 모든 초안 작성을 완료했어요! 아래는 전체 초안입니다:")
        
        # 복사 가능한 코드 블록으로 전체 초안 표시
        with st.expander("📋 전체 초안 (클릭하여 복사하기)", expanded=True):
            st.code(full_draft, language="markdown")
            st.info("위 코드 블록을 클릭하면 전체 내용을 복사할 수 있습니다.")
        
        bot_say("필요한 경우 수정하거나 복사해서 사용하세요. '전체 초안 보기'라고 입력하시면 언제든지 다시 볼 수 있습니다.")

    # DONE 단계에서 추가 요청 처리
    elif step == Step.DONE.value:
        # 전체 초안 보기 요청 처리
        view_draft_patterns = ["전체", "초안", "보기", "보여", "다시", "확인"]
        is_view_draft_request = sum(pattern in user_input for pattern in view_draft_patterns) >= 2
        
        # 새로 시작 요청 처리
        restart_patterns = ["새로", "다시", "처음", "시작", "새 글", "새글", "새 초안", "새초안"]
        is_restart_request = sum(pattern in user_input for pattern in restart_patterns) >= 2
        
        # 도움말 요청 처리
        help_patterns = ["도움", "도와", "명령", "어떻게", "사용법", "기능", "할 수 있"]
        is_help_request = sum(pattern in user_input for pattern in help_patterns) >= 1
        
        if is_view_draft_request:
            if "full_draft" in st.session_state:
                bot_say("전체 초안을 다시 표시합니다:")
                with st.expander("📋 전체 초안 (클릭하여 복사하기)", expanded=True):
                    st.code(st.session_state.full_draft, language="markdown")
                    st.info("위 코드 블록을 클릭하면 전체 내용을 복사할 수 있습니다.")
        elif is_restart_request:
            bot_say("새로운 블로그 초안을 작성하시려면 페이지를 새로고침해주세요.")
        elif is_help_request:
            help_message = """
            📚 **사용 가능한 명령어**
            
            현재 다음과 같은 명령어를 사용할 수 있습니다:
            
            - **전체 초안 보기**: 작성된 전체 초안을 다시 표시합니다.
            - **새로 시작하기**: 새로운 블로그 초안 작성을 시작합니다. (페이지 새로고침 필요)
            
            초안 작성이 완료된 상태입니다. 필요한 경우 위의 명령어를 사용하세요.
            """
            bot_say(help_message)
        else:
            bot_say("초안 작성이 완료되었습니다. '전체 초안 보기'라고 입력하시면 전체 초안을 다시 볼 수 있습니다. 새로운 초안을 작성하시려면 페이지를 새로고침해주세요.")

# 첫 질문 표시
if not st.session_state.messages:
    bot_say(PROMPT_TOPIC_QUESTION)

# 사용자 입력 대기
user_say()