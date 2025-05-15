import streamlit as st
import google.generativeai as genai
import time
import os

# Gemini API 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-pro")

# 세션 초기화
def init_session():
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # 대화 이력 저장
    if "user_inputs" not in st.session_state:
        st.session_state.user_inputs = {}

# 챗봇 메시지 출력
def bot(message):
    st.session_state.chat_history.append(("assistant", message))
    with st.chat_message("assistant"):
        st.markdown(message)

# 사용자 메시지 출력
def user(message):
    st.session_state.chat_history.append(("user", message))
    with st.chat_message("user"):
        st.markdown(message)

# Gemini 호출 래퍼
def ask_gemini(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ 오류 발생: {e}"

# 자연어 긍정/부정 판단
def interpret_intent(text):
    prompt = f"""
사용자의 응답: "{text}"
아래 질문에 대해 긍정적인지 아닌지 판단해주세요:
"""
    resp = model.generate_content(prompt)
    # 모델 응답이 긍정인지 확인
    return "긍정" if "예" in resp.text or "네" in resp.text else "부정"

# 블로그 초안용 ReAct 프롬프트 생성
def generate_full_prompt():
    data = st.session_state.user_inputs
    topic = data.get("topic", "")
    keywords = data.get("keywords", [])
    style = data.get("style", "")
    structure = data.get("structure", "")
    subtitles = data.get("subtitles", [])
    return f"""
당신은 기술 블로그 작성 도우미 챗봇입니다.
지금까지 받은 정보를 확인하고, Markdown 형식으로 블로그 초안을 작성해주세요.

- 주제: {topic}
- 키워드: {', '.join(keywords)}
- 스타일: {style}
- 구조: {structure}
- 소제목:
  {'\n  '.join(subtitles)}

각 소제목을 `##`로 표시하고, 간단한 코드 예시를 포함해도 좋습니다. 마지막에 "이 내용이 만족스럽나요?"라고 물어보세요.
"""

# 앱 시작
st.set_page_config(page_title="기술 블로그 작성 챗봇", layout="centered")
st.title("📝 기술 블로그 초안 생성기 (Gemini + Streamlit)")
init_session()

# 입력 처리
user_input = st.chat_input("대화창에 답변을 입력해주세요...")
# 이전 대화 렌더링
for role, msg in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(msg)

step = st.session_state.step
inputs = st.session_state.user_inputs

# 1단계: 주제 입력
if step == 1:
    if not st.session_state.chat_history:
        bot("안녕하세요! 기술 블로그 작성을 도와드릴게요. 어떤 주제로 시작하고 싶으신가요?")
    if user_input:
        user(user_input)
        inputs['topic'] = user_input
        bot(f"주제를 **{user_input}**(으)로 이해했어요. 이게 맞나요? 맞다면 편하게 '네', 아니면 다시 말씀해주세요.")
        st.session_state.step = 1.1

elif step == 1.1:
    if user_input:
        user(user_input)
        intent = interpret_intent(user_input)
        if intent == "긍정":
            bot("알겠어요! 이 주제와 관련된 주요 키워드를 추천해 드릴게요. 잠시만 기다려주세요... 📋")
            time.sleep(1)
            prompt = f"""
주제: '{inputs['topic']}'

이 주제에 어울리는 기술 키워드를 5~7개 추천해주세요. Markdown 리스트로 보여주세요.
"""
            response = ask_gemini(prompt)
            kws = [k.strip('- ') for k in response.split('\n') if k.strip()]
            inputs['recommended_keywords'] = kws
            bot("추천 키워드는 다음과 같아요:\n" + "\n".join(f"- {k}" for k in kws) + "\n어떤 키워드를 사용하시겠어요? 자유롭게 말씀해주세요.")
            st.session_state.step = 2
        else:
            bot("알겠습니다. 주제를 다시 입력해주시면 도와드릴게요.")
            st.session_state.step = 1

# 2단계: 키워드 입력 및 확인
elif step == 2:
    if user_input:
        user(user_input)
        prompt = f"""
사용자가 입력한 키워드: '{user_input}'

이 문장에서 개별 키워드를 추출하여 Markdown 리스트로 정리해주세요.
"""
        response = ask_gemini(prompt)
        kws = [k.strip('- ') for k in response.split('\n') if k.strip()]
        inputs['keywords'] = kws
        bot(f"제가 파악한 키워드는: {', '.join(kws)} 이에요. 더 추가하거나 수정할 부분이 있나요? 괜찮다면 '네'라고 말씀해주세요.")
        st.session_state.step = 2.1

elif step == 2.1:
    if user_input:
        user(user_input)
        intent = interpret_intent(user_input)
        if intent == "긍정":
            bot("좋아요! 다음은 글의 스타일을 정해볼게요. 어떤 독자층을 위해 쓸까요? 예: 초심자, 실무자, 발표용 등")
            st.session_state.step = 3
        else:
            bot("그럼 키워드를 다시 입력해주세요. 원하는 키워드를 자유롭게 말씀해주세요.")
            st.session_state.step = 2

# 3단계: 스타일 선택 및 확인
elif step == 3:
    if user_input:
        user(user_input)
        inputs['style'] = user_input
        bot(f"'{user_input}' 스타일로 작성하는 걸로 이해했어요. 적절한가요? 이대로 진행하시려면 '네'라고 알려주세요.")
        st.session_state.step = 3.1
    elif not any("스타일" in m for _, m in st.session_state.chat_history if _ == 'assistant'):
        bot("어떤 스타일로 글을 원하시나요? 예: 초심자 대상, 실무자 대상, 기술 발표용 등.")

elif step == 3.1:
    if user_input:
        user(user_input)
        intent = interpret_intent(user_input)
        if intent == "긍정":
            bot("완벽해요! 이제 글 구조를 정하고, 예시 서론을 보여드릴게요. 원하는 구조를 말씀해주세요 📖")
            st.session_state.step = 4
        else:
            bot("알겠습니다. 스타일을 다시 입력해주세요.")
            st.session_state.step = 3

# 4단계: 구조 선택 및 예시
elif step == 4:
    if user_input:
        user(user_input)
        inputs['structure'] = user_input
        prompt = f"""
구조 유형: '{user_input}'

이 구조에 맞춰 서론 문단을 Markdown 형식 예시로 작성해주세요.
"""
        example = ask_gemini(prompt)
        bot("예시 서론입니다:\n" + example + "\n이런 흐름으로 진행해볼까요? 괜찮으면 '네'라고 알려주세요.")
        st.session_state.step = 4.1

elif step == 4.1:
    if user_input:
        user(user_input)
        intent = interpret_intent(user_input)
        if intent == "긍정":
            bot("좋습니다! 이 구조에 맞춰 소제목을 추천해드릴게요. 잠시만요... 📝")
            prompt = f"""
주제: {inputs['topic']}
키워드: {', '.join(inputs['keywords'])}
구조: {inputs['structure']}

4~6개의 소제목을 Markdown 리스트로 추천해주세요.
"""
            resp = ask_gemini(prompt)
            subs = [s.strip('- ') for s in resp.split('\n') if s.strip()]
            inputs['subtitles'] = subs
            bot("추천 소제목입니다:\n" + "\n".join(f"- {s}" for s in subs) + "\n수정하거나 추가하고 싶은 제목을 알려주세요.")
            st.session_state.step = 5
        else:
            bot("다른 구조를 말씀해주시면 반영할게요.")
            st.session_state.step = 4

# 5단계: 소제목 구성 및 확인
elif step == 5:
    if user_input:
        user(user_input)
        prompt = f"""
사용자가 제시한 소제목: '{user_input}'

각 줄을 소제목으로 추출하여 Markdown 리스트로 정리해주세요.
"""
        resp = ask_gemini(prompt)
        subs = [s.strip('- ') for s in resp.split('\n') if s.strip()]
        inputs['subtitles'] = subs
        bot("확인한 소제목은 다음과 같아요:\n" + "\n".join(f"- {s}" for s in subs) + "\n이 구성이 마음에 드시나요? '네'라고 알려주세요.")
        st.session_state.step = 5.1

elif step == 5.1:
    if user_input:
        user(user_input)
        intent = interpret_intent(user_input)
        if intent == "긍정":
            bot("마지막으로 전체 초안을 Markdown 형식으로 작성해드릴게요. 잠시만 기다려주세요... ✨")
            st.session_state.step = 6
        else:
            bot("원하는 소제목을 다시 알려주세요.")
            st.session_state.step = 5

# 6단계: 초안 작성
elif step == 6:
    bot("초안 작성 중입니다...🖊️ 기다려주세요!")
    prompt = generate_full_prompt()
    draft = ask_gemini(prompt)
    inputs['draft'] = draft
    bot(draft)
    bot("이 초안이 만족스러우신가요? 수정할 부분이나 플랫폼 포맷 요청이 있으면 알려주세요!")
    st.session_state.step = 6.1

# 사이드바: 전체 초기화
with st.sidebar:
    if st.button("🔄 전체 초기화"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.experimental_rerun()
