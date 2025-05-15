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

수정 시 다음 사항을 유의하세요:
1. 사용자의 요청사항을 정확히 반영
2. 기술적 정확성 유지
3. 글의 전체적인 일관성 유지
4. 코드 예제가 있다면 정확하게 수정
5. 기존 초안의 좋은 부분은 유지

주제: {topic}
키워드: {keywords}
스타일: {style}
"""

# Gemini 모델 불러오기
def get_chat_model():
    return genai.GenerativeModel("gemini-pro")

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

위 입력을 기반으로 기술 블로그 주제를 추론해 한 문장으로 요약하고, 다음 질문 형식으로 출력:

예시:
🧠 사용자의 입력을 바탕으로 제가 이해한 주제는 다음과 같습니다: "Postman 사용법"
⚙️ 이 주제로 블로그를 작성하시는 게 맞을까요?
"""
        inferred_text = process_model_request(prompt)
        bot_say(inferred_text)

    # 주제 확인 단계
    elif step == Step.TOPIC_CONFIRM.value:
        if "네" in user_input:
            bot_say("좋아요! 이제 관련 키워드를 추천드릴게요.")
            st.session_state.step = Step.KEYWORD_QUESTION.value
        else:
            bot_say("주제를 다시 말씀해주세요.")
            st.session_state.step = Step.TOPIC_QUESTION.value

    # 키워드 질문 단계
    elif step == Step.KEYWORD_QUESTION.value:
        st.session_state.collected["user_keywords_raw"] = user_input
        st.session_state.step = Step.KEYWORD_CONFIRM.value
        prompt = f"사용자가 입력한 키워드 후보: {user_input}\n위 내용을 정리하여 GPT가 키워드 리스트로 정제하고, 확인 질문 포함한 메시지 생성"
        response_text = process_model_request(prompt)
        bot_say(response_text)

    # 키워드 확인 단계
    elif step == Step.KEYWORD_CONFIRM.value:
        if "네" in user_input:
            bot_say("스타일을 정해볼게요. 문체와 대상 독자를 알려주세요.")
            st.session_state.step = Step.STYLE_QUESTION.value
        else:
            bot_say("다시 키워드를 입력해주세요.")
            st.session_state.step = Step.KEYWORD_QUESTION.value

    # 스타일 질문 단계
    elif step == Step.STYLE_QUESTION.value:
        st.session_state.collected["user_style_raw"] = user_input
        st.session_state.step = Step.STYLE_CONFIRM.value
        prompt = f"사용자가 입력한 스타일: {user_input}\n형식, 톤, 독자대상을 정리하여 확인 메시지 생성"
        response_text = process_model_request(prompt)
        bot_say(response_text)

    # 스타일 확인 단계
    elif step == Step.STYLE_CONFIRM.value:
        if "네" in user_input:
            bot_say("좋아요! 이제 글의 구조를 제안드릴게요.")
            st.session_state.step = Step.STRUCTURE_SUGGEST.value
        else:
            bot_say("스타일을 다시 입력해주세요.")
            st.session_state.step = Step.STYLE_QUESTION.value

    # 구조 제안 단계
    elif step == Step.STRUCTURE_SUGGEST.value:
        prompt = f"주제와 키워드, 스타일을 바탕으로 블로그의 전체 구조를 제안해주세요. 각 섹션은 제목만 출력해주세요."
        response_text = process_model_request(prompt)
        st.session_state.collected["suggested_structure"] = response_text
        st.session_state.step = Step.STRUCTURE_CONFIRM.value
        bot_say(response_text + "\n\n이 구조로 괜찮을까요?")

    # 구조 확인 단계
    elif step == Step.STRUCTURE_CONFIRM.value:
        if "네" in user_input:
            bot_say("좋습니다. 이제 각 소제목을 확정하겠습니다.")
            st.session_state.step = Step.SUBTITLE_CONFIRM.value
        else:
            bot_say("원하시는 구조를 다시 말씀해주세요.")
            st.session_state.step = Step.STRUCTURE_SUGGEST.value

    # 소제목 확인 단계
    elif step == Step.SUBTITLE_CONFIRM.value:
        st.session_state.collected["finalized_subtitles"] = [s.strip() for s in user_input.split("\n") if s.strip()]
        st.session_state.step = Step.DRAFT_GENERATE.value
        st.session_state.draft_index = 0
        bot_say("이제 각 섹션별로 초안을 작성해드릴게요!")
        handle_input("")  # 자동으로 첫 섹션 초안 생성 시작

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
        if "네" in user_input:
            st.session_state.draft_index += 1
            st.session_state.step = Step.DRAFT_GENERATE.value
            handle_input("")  # 다음 섹션 자동 호출
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
            prompt = f"{REACT_SYSTEM_PROMPT}\n\n{revision_prompt}"
            
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
        
        # 전체 초안 표시
        st.session_state.step = Step.DONE.value
        bot_say(f"✅ 모든 초안 작성을 완료했어요! 아래는 전체 초안입니다:\n\n{full_draft}\n\n필요한 경우 수정하거나 복사해서 사용하세요.")

# 첫 질문 표시
if not st.session_state.messages:
    bot_say(PROMPT_TOPIC_QUESTION)

# 사용자 입력 대기
user_say()