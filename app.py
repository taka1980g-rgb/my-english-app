import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import PyPDF2
import io
import re

# === 🎨 画面デザインのカスタマイズ（CSS） ===
st.markdown("""
    <style>
    /* 録音ボタンを大きく・目立たせる */
    [data-testid="stAudioInput"] {
        border: 2px solid #FF4B4B;
        border-radius: 15px;
        padding: 10px;
        background-color: #FFF5F5;
        margin-bottom: 20px;
    }
    .mic-guide {
        font-size: 1.2rem;
        font-weight: bold;
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# === 🚪 入場パスワードのチェック ===
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1234")

if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔒 家族専用 AI英会話")
    pwd = st.text_input("合言葉（パスワード）を入力してください", type="password")
    if pwd == APP_PASSWORD:
        st.session_state["password_correct"] = True
        st.rerun()
    elif pwd != "":
        st.error("パスワードが違います👀")
    st.stop() 

# === 🔑 API設定 ===
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    MY_API_KEY = ""
    st.error("⚠️ Secretsに GEMINI_API_KEY を設定してください！")
    st.stop()

genai.configure(api_key=MY_API_KEY.strip())

st.title("My English Roleplay AI 🗣️")

with st.sidebar:
    st.header("⚙️ 設定メニュー")
    
    st.write("🧠 AIモデル")
    model_options = {
        "賢い": "gemini-2.5-flash",
        "最速": "gemini-2.5-flash-lite"
    }
    selected_display_name = st.selectbox("使用中の脳みそ", list(model_options.keys()), index=0)
    selected_model = model_options[selected_display_name]
            
    st.markdown("---")
    level = st.selectbox("📈 会話のレベル", ["1: 超初心者", "2: 初心者", "3: 中級者", "4: 上級者", "5: 専門家"])

    st.markdown("---")
    input_name = st.text_input("📛 あなたの名前", placeholder="例: masa")
    user_name = input_name if input_name else "Anata"
    
    st.markdown("---")
    st.write("👤 質問者（AIの役割）")
    preset_questioner = st.selectbox("AIの役柄", ["小学校の先生", "同年代の友達", "職場の先輩", "気さくな友達", "学会発表の聴衆", "その他"])
    questioner = st.text_input("役割を入力", "空港の入国審査官") if preset_questioner == "その他" else preset_questioner
    
    st.markdown("---")
    situation = st.text_area("🎬 シチュエーション", "　", height=100)
    
    st.markdown("---")
    uploaded_file = st.file_uploader("PDF/TXTファイル", type=["pdf", "txt"])
    
    st.markdown("---")
    start_button = st.button("▶️ 会話をリセットしてスタート", type="primary", use_container_width=True)
    end_button = st.button("🛑 会話を終了して評価をもらう", use_container_width=True)

def extract_text(file):
    text = ""
    if file.name.endswith('.pdf'):
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages: text += page.extract_text() + "\n"
    elif file.name.endswith('.txt'):
        text = file.read().decode('utf-8')
    return text

doc_text = extract_text(uploaded_file) if uploaded_file else ""

system_instruction = f"""
あなたは{questioner}です。ユーザー{user_name}（レベル:{level}）の英会話相手です。
【ルール】
1. 客観的に、前置きなしで簡潔に答えてください。
2. フィードバックは日本語の箇条書きで。
3. [英語の質問] セクションには英語のセリフと、必要ならカッコ内に日本語訳を書いてください。
シチュエーション: {situation}
資料: {doc_text}
"""

if "last_played_msg_idx" not in st.session_state:
    st.session_state.last_played_msg_idx = -1

if start_button:
    try:
        model = genai.GenerativeModel(selected_model, system_instruction=system_instruction)
        st.session_state.chat_session = model.start_chat(history=[])
        st.session_state.messages = []
        st.session_state.last_played_msg_idx = -1
        response = st.session_state.chat_session.send_message("シチュエーションを開始して、最初の質問を英語でしてください。")
        st.session_state.messages.append({"role": "assistant", "content": response.text})
    except Exception as e:
        st.error(f"エラー: {e}")

if end_button and "chat_session" in st.session_state:
    with st.spinner("AIが成績をまとめています..."):
        response = st.session_state.chat_session.send_message("会話を終了し、日本語で総評をしてください。")
        st.session_state.messages.append({"role": "assistant", "content": response.text})

if "chat_session" in st.session_state:
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "[英語の質問]" in message["content"]:
                # ★改善：カッコ内の日本語を除去して英語だけを読み上げる★
                raw_text = message["content"].split("[英語の質問]")[1].strip()
                clean_english = re.sub(r'\(.*?\)', '', raw_text).strip()
                if clean_english:
                    try:
                        tts = gTTS(text=clean_english, lang='en')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        fp.seek(0)
                        auto_play = (i == len(st.session_state.messages) - 1 and st.session_state.last_played_msg_idx != i)
                        if auto_play: st.session_state.last_played_msg_idx = i
                        st.audio(fp, format="audio/mp3", autoplay=auto_play)
                    except: pass

    st.markdown("---")
    st.markdown('<p class="mic-guide">👇 録音ボタンを押して英語で話してね！</p>', unsafe_allow_html=True)

    prompt = None
    display_prompt = None

    if st.button("🆘 ギブアップ（解説を見る）"):
        prompt = "今の質問の意図、日本語訳、回答例を教えてください。その後、別の質問を英語でしてください。"
        display_prompt = "（🆘 ギブアップしました）"

    audio_value = st.audio_input("マイクを押して録音開始 / 停止")

    if audio_value is not None:
        audio_bytes = audio_value.getvalue()
        if "last_audio_bytes" not in st.session_state or st.session_state.last_audio_bytes != audio_bytes:
            st.session_state.last_audio_bytes = audio_bytes
            with st.spinner("文字に変換中..."):
                try:
                    res = genai.GenerativeModel(selected_model).generate_content([{"mime_type": "audio/wav", "data": audio_bytes}, "聞こえた英語をそのまま文字起こししてください。"])
                    if res.text:
                        prompt = res.text.strip()
                        display_prompt = prompt
                except: st.error("聞き取れませんでした。")

    with st.expander("⌨️ 文字で入力する場合"):
        with st.form("text_input", clear_on_submit=True):
            t_prompt = st.text_input("英語を入力:")
            if st.form_submit_button("送信") and t_prompt:
                prompt = t_prompt
                display_prompt = t_prompt

    if prompt and display_prompt:
        st.session_state.messages.append({"role": "user", "content": display_prompt})
        with st.spinner("AIが返答を考えています..."):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun() 
            except: st.error("エラーが発生しました。")
else:
    st.info("👈 左側のメニューを設定し、スタートボタンを押してください。")
