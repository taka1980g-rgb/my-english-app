import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import PyPDF2
import io
import re

# === 🎨 画面デザインのカスタマイズ（CSS） ===
st.markdown("""
    <style>
    [data-testid="stAudioInput"] {
        border: 3px solid #FF4B4B;
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

# === 🚪 入場パスワード ===
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1234")
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False
if not st.session_state["password_correct"]:
    st.title("🔒 家族専用 AI英会話")
    pwd = st.text_input("合言葉（パスワード）を入力してください", type="password")
    if pwd == APP_PASSWORD:
        st.session_state["password_correct"] = True
        st.rerun()
    st.stop() 

# === 🔑 API設定 ===
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"].strip())
except:
    st.error("APIキーが見つかりません。")
    st.stop()

# === 🧠 状態の初期化 ===
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None
if "last_played_msg_idx" not in st.session_state:
    st.session_state.last_played_msg_idx = -1

st.title("My English Roleplay AI 🗣️")

# === ⚙️ サイドバー ===
with st.sidebar:
    st.header("⚙️ 設定メニュー")
    model_options = {"Gemini 2.5 Flash (高速)": "gemini-2.5-flash", "Gemini 2.5 Flash-Lite (最速)": "gemini-2.5-flash-lite"}
    selected_model = model_options[st.selectbox("AIモデル", list(model_options.keys()))]
    level = st.selectbox("📈 会話のレベル", ["1: 超初心者", "2: 初心者", "3: 中級者", "4: 上級者", "5: 専門家"])
    input_name = st.text_input("📛 あなたの名前", "masa")
    user_name = input_name if input_name else "Anata"
    preset_questioner = st.selectbox("AIの役柄", ["小学校の先生", "同年代の友達", "職場の先輩", "気さくな友達", "その他"])
    questioner = st.text_input("役割を入力", "空港の入国審査官") if preset_questioner == "その他" else preset_questioner
    situation = st.text_area("🎬 シチュエーション", "例: 好きな食べ物について教えてください。", height=100)
    uploaded_file = st.file_uploader("PDF/TXTファイル", type=["pdf", "txt"])
    st.markdown("---")
    start_button = st.button("▶️ 会話をリセットしてスタート", type="primary", use_container_width=True)
    end_button = st.button("🛑 会話を終了して評価をもらう", use_container_width=True)

# テキスト抽出
def extract_text(file):
    text = ""
    if file.name.endswith('.pdf'):
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages: text += page.extract_text() + "\n"
    elif file.name.endswith('.txt'):
        text = file.read().decode('utf-8')
    return text
doc_text = extract_text(uploaded_file) if uploaded_file else ""

system_instruction = f"あなたは{questioner}です。ユーザー{user_name}（レベル:{level}）の英会話相手です。シチュエーションは{situation}です。資料：{doc_text}。必ず [フィードバック] と [英語の質問] の形式で簡潔に答えてください。"

# 会話の初期化
if start_button:
    st.session_state.chat_session = genai.GenerativeModel(selected_model, system_instruction=system_instruction).start_chat(history=[])
    st.session_state.messages = []
    st.session_state.last_played_msg_idx = -1
    st.session_state.last_processed_audio = None # オーディオ履歴もリセット
    response = st.session_state.chat_session.send_message("シチュエーションを開始して、最初の質問を英語でしてください。")
    st.session_state.messages.append({"role": "assistant", "content": response.text})

# メッセージ表示と読み上げ
if "chat_session" in st.session_state:
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "[英語の質問]" in message["content"]:
                raw_text = message["content"].split("[英語の質問]")[1].strip()
                clean_english = re.sub(r'\(.*?\)', '', raw_text).strip()
                if clean_english:
                    try:
                        tts = gTTS(text=clean_english, lang='en')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        fp.seek(0)
                        is_last = (i == len(st.session_state.messages) - 1)
                        if is_last and st.session_state.last_played_msg_idx != i:
                            st.session_state.last_played_msg_idx = i
                            st.audio(fp, format="audio/mp3", autoplay=True)
                        else:
                            st.audio(fp, format="audio/mp3", autoplay=False)
                    except: pass

    st.markdown("---")
    st.markdown('<p class="mic-guide">👇 録音ボタンを押して英語で話してね！</p>', unsafe_allow_html=True)
    
    # 🆘 ギブアップボタン
    if st.button("🆘 ギブアップ（解説を見る）"):
        res = st.session_state.chat_session.send_message("今の質問の意図、日本語訳、回答例を教えてください。その後、別の質問を英語でしてください。")
        st.session_state.messages.append({"role": "user", "content": "（🆘 ギブアップしました）"})
        st.session_state.messages.append({"role": "assistant", "content": res.text})
        st.rerun()

    # 🎙️ 音声入力
    audio_value = st.audio_input("録音")

    # ★ズレ防止の核心部★
    if audio_value is not None:
        current_audio_data = audio_value.getvalue()
        # 「まだ処理していない新しい音声データ」がある場合のみ実行
        if st.session_state.last_processed_audio != current_audio_data:
            with st.spinner("AIが聞き取っています..."):
                try:
                    # 音声を文字起こし
                    trans_model = genai.GenerativeModel(selected_model)
                    trans_res = trans_model.generate_content([{"mime_type": "audio/wav", "data": current_audio_data}, "聞こえた英語をそのまま文字起こししてください。"])
                    user_text = trans_res.text.strip()
                    
                    if user_text:
                        # 1. 処理済みリストにこのデータを保存（二重処理を防止）
                        st.session_state.last_processed_audio = current_audio_data
                        # 2. メッセージを追加
                        st.session_state.messages.append({"role": "user", "content": user_text})
                        # 3. AIに返答させる
                        ai_res = st.session_state.chat_session.send_message(user_text)
                        st.session_state.messages.append({"role": "assistant", "content": ai_res.text})
                        # 4. 即座にリロード
                        st.rerun()
                except:
                    st.error("うまく聞き取れませんでした。")

    # ⌨️ テキスト入力
    with st.expander("⌨️ 文字で入力したい場合はこちら"):
        with st.form("text_input", clear_on_submit=True):
            t_prompt = st.text_input("英語を入力:")
            if st.form_submit_button("送信") and t_prompt:
                st.session_state.messages.append({"role": "user", "content": t_prompt})
                ai_res = st.session_state.chat_session.send_message(t_prompt)
                st.session_state.messages.append({"role": "assistant", "content": ai_res.text})
                st.rerun()
else:
    st.info("👈 左側のメニューを設定し、スタートボタンを押してください。")
