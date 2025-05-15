import streamlit as st
import google.generativeai as genai
import time
import os

# Gemini API 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-pro")

# 세션 초기화
def init_session():
    defaults = {"step": 1, "chat_history": [], "user_inputs": {}}
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

# 메시지 기록
def bot(message):
    st.session_state.chat_history.append(("assistant", message))
    with st.chat_message("assistant"):
        st.markdown(message)

def user(message):
    st.session_state.chat_history.append(("user", message))
    with st.chat_message("user"):
        st.markdown(message)

# 모델 호출
def ask_gemini(prompt):
    try:
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        return f"❌ 오류 발생: {e}"

# 의도 파악
def interpret_intent(text):
    prompt = f"""
사용자의 응답: "{text}"

이 텍스트가 애초의 질문에 대해 긍정적인지 판단해주세요. '예' 또는 '아니오'로만 대답해주세요.
"""
    return ask_gemini(prompt)

# 앱 시작
st.set_page_config(page_title="기술 블로그 작성 챗봇", layout="centered")
st.title("📝 기술 블로그 초안 생성기")
init_session()

# 입력 처리
def main():
    user_input = st.chat_input("답변을 입력하세요...")
    # 이전 대화 렌더링
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg)
    step = st.session_state.step
    inputs = st.session_state.user_inputs

    # 1단계: 주제 입력 및 파싱
    if step == 1:
        if not st.session_state.chat_history:
            bot("안녕하세요! 어떤 주제로 기술 블로그를 작성하고 싶으신가요?")
        if user_input:
            user(user_input)
            # GPT로 주제 정제
            parse_prompt = f"""
사용자가 이렇게 입력했습니다: "{user_input}"

위 텍스트를 기술 블로그 제목에 어울리는 명확한 형태로 한 문장으로 추출해주세요.
"""
            topic_clean = ask_gemini(parse_prompt)
            inputs['topic'] = topic_clean
            bot(f"주제를 **'{topic_clean}'**(으)로 이해했어요. 이게 맞나요? 맞으면 '네', 아니면 다시 입력해주세요.")
            st.session_state.step = 1.1

    elif step == 1.1:
        if user_input:
            user(user_input)
            intent = interpret_intent(user_input)
            if '예' in intent:
                bot("좋습니다! 이 주제와 관련된 핵심 키워드를 추천해드릴게요...")
                time.sleep(1)
                kw_prompt = f"""
주제: '{inputs['topic']}'

관련된 기술 키워드를 5~7개 Markdown 리스트로 추천해주세요.
"""
                kw_resp = ask_gemini(kw_prompt)
                kws = [k.strip('- ') for k in kw_resp.split('\n') if k.strip()]
                inputs['recommended_keywords'] = kws
                bot("추천 키워드입니다:\n" + '\n'.join(f"- {k}" for k in kws) + "\n사용할 키워드를 자유롭게 입력해주세요.")
                st.session_state.step = 2
            else:
                bot("알겠습니다. 다시 주제를 입력해주세요.")
                st.session_state.step = 1

    # 이후 단계 로직 동일하게 ReAct 및 자연어 파싱 적용...

    # 사이드바: 초기화
    with st.sidebar:
        if st.button("🔄 전체 초기화"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.experimental_rerun()

if __name__ == '__main__':
    main()
