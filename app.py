import streamlit as st
import google.generativeai as genai

# 세션 상태 초기화 함수
def init_session():
    for key in ["step", "topic", "keywords", "style", "structure", "headings", "draft"]:
        if key not in st.session_state:
            st.session_state[key] = None
    if "step" not in st.session_state:
        st.session_state.step = 1

# Gemini API 호출 함수
def call_gemini(prompt):
    genai.configure(api_key="YOUR_GOOGLE_API_KEY")  # 여기서 Google API 키를 설정하세요.
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return response.text.strip()

# 프롬프트 함수들
def generate_keywords_prompt(topic):
    return f"""
주제: {topic}

주제와 관련된 중요한 기술 키워드를 5~7개 추천해주세요. 키워드는 명확하고 일반적인 용어로 제시해주세요.
"""

def generate_style_prompt(style):
    return f"""
이 글은 '{style}'을 타겟으로 합니다. 이에 맞게 톤과 깊이를 설정해주세요.
"""

def generate_structure_prompt(topic, structure_type, style):
    return f"""
주제: {topic}
스타일: {style}
글 형식: {structure_type}

위 정보에 따라 글의 서론 한 문단을 Markdown 형식으로 작성해주세요.
"""

def generate_heading_prompt(topic, keywords, structure_type):
    joined = ", ".join(keywords)
    return f"""
주제: {topic}
포함할 키워드: {joined}
글 형식: {structure_type}

이 글의 소제목을 4~6개 추천해주세요. 번호를 붙이지 말고 Markdown 스타일로 작성해주세요.
"""

def generate_draft_prompt(topic, keywords, style, structure, headings):
    heading_text = "\n".join([f"## {h}" for h in headings])
    return f"""
주제: {topic}
스타일: {style}
키워드: {', '.join(keywords)}
글 구조: {structure}

다음 소제목을 기준으로 기술 블로그 초안을 Markdown 형식으로 작성해주세요:

{heading_text}
"""

# Streamlit 앱 시작
st.set_page_config(page_title="기술 블로그 초안 생성기 (Gemini + Streamlit)", layout="wide")
init_session()

st.title("🧠 기술 블로그 초안 생성기 (Gemini + Streamlit)")

step = st.session_state.get("step", 1)

# 1. 주제 입력
if step == 1:
    st.subheader("1️⃣ 주제를 입력해주세요")
    topic = st.text_input("블로그 글 주제는 무엇인가요?", st.session_state.get("topic", ""))
    if topic:
        st.session_state.topic = topic
        if st.button("다음 단계로 ➡️"):
            st.session_state.step = 2

# 2. 키워드 추천 + 선택
elif step == 2:
    st.subheader("2️⃣ 관련 키워드를 선택해주세요")
    prompt = generate_keywords_prompt(st.session_state.topic)
    keyword_response = call_gemini(prompt)
    suggested_keywords = keyword_response.split(", ")
    selected_keywords = st.multiselect("추천 키워드 중 선택해주세요", suggested_keywords)
    manual_keywords = st.text_input("추가로 입력할 키워드가 있다면 작성해주세요 (쉼표로 구분)")
    
    if st.button("확인하고 다음 단계로 ➡️"):
        keywords = selected_keywords + manual_keywords.split(",")
        st.session_state.keywords = [kw.strip() for kw in keywords if kw.strip()]
        st.session_state.step = 3

# 3. 스타일 선택
elif step == 3:
    st.subheader("3️⃣ 예상 독자 스타일을 선택해주세요")
    style_options = ["초심자용", "실무자용", "내부 공유용", "기술 발표용"]
    style = st.radio("타겟 독자를 선택해주세요", style_options)
    if style:
        st.session_state.style = style
        if st.button("확인하고 다음 단계로 ➡️"):
            st.session_state.step = 4

# 4. 글 구조 선택
elif step == 4:
    st.subheader("4️⃣ 글의 기본 구조를 선택해주세요")
    structure_options = {
        "기본 서론-본문-결론": "intro-body-conclusion",
        "문제-해결-결과": "problem-solution-result",
        "코드-설명 반복형": "code-explanation"
    }
    structure_choice = st.selectbox("글 형식을 골라주세요", list(structure_options.keys()))
    confirm_sample = st.checkbox("예시 문단 생성 확인")
    
    if structure_choice and confirm_sample:
        structure_prompt = generate_structure_prompt(
            st.session_state.topic, structure_options[structure_choice], st.session_state.style
        )
        example = call_gemini(structure_prompt)
        st.markdown("**예시 문단**")
        st.markdown(example)

        if st.button("예시 확인했어요 ✅ 다음 단계로 ➡️"):
            st.session_state.structure = structure_options[structure_choice]
            st.session_state.step = 5

# 5. 소제목 구성
elif step == 5:
    st.subheader("5️⃣ 글에 포함할 소제목을 정해주세요")
    heading_prompt = generate_heading_prompt(
        st.session_state.topic,
        st.session_state.keywords,
        st.session_state.structure
    )
    headings = call_gemini(heading_prompt).split("\n")
    editable_headings = [st.text_input(f"소제목 {i+1}", value=h.strip("123456. ")) for i, h in enumerate(headings) if h]
    
    if st.button("소제목 확정 ➡️"):
        st.session_state.headings = editable_headings
        st.session_state.step = 6

# 6. 초안 생성
elif step == 6:
    st.subheader("6️⃣ 글 초안을 생성합니다")
    draft_prompt = generate_draft_prompt(
        topic=st.session_state.topic,
        keywords=st.session_state.keywords,
        style=st.session_state.style,
        structure=st.session_state.structure,
        headings=st.session_state.headings
    )
    draft = call_gemini(draft_prompt)
    st.session_state.draft = draft
    st.markdown("**📝 Markdown 초안:**")
    st.code(draft, language="markdown")

    if st.button("다시 소제목 수정하기 🔁"):
        st.session_state.step = 5

    if st.button("다시 스타일 바꾸기 🔁"):
        st.session_state.step = 3
