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
    pwd = st.text_input("合言葉を入力してください", type="password")
    if pwd == APP_PASSWORD:
        st.session_state["password_correct"] = True
        st.rerun()
    st.stop() 

# === 🔑 API設定 ===
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("APIキーが設定されていません")
    st.stop()

genai.configure(api_key=MY_API_KEY.strip())

st.title("My English Roleplay AI 🗣️")

# === ⚙️ サイドバー設定 ===
with st.sidebar:
    st.header("⚙️ 設定メニュー")
    model_options = {
        "Gemini 2.5 Flash (高速・汎用)": "gemini-2.5-flash",
        "Gemini 2.5 Flash-Lite (最速・低コスト)": "gemini-2.5-flash-lite"
    }
    selected_display_name = st.selectbox("使用中の脳みそ", list(model_options.keys()), index=0)
    selected_model = model_options[selected_display_name]
    level = st.selectbox("📈 会話のレベル", ["1: 超初心者", "2: 初心者", "3: 中級者", "4: 上級者", "5: 専門家"])
    input_name = st.text_input("📛 あなたの名前", placeholder="例: masa")
    user_name = input_name if input_name else "Anata"
    preset_questioner = st.selectbox("AIの役柄", ["小学校の先生", "同年代の友達", "職場の先輩", "気さくな友達", "その他"])
    questioner = st.text_input("役割を入力", "空港の入国審査官") if preset_questioner == "その他" else preset_questioner
    situation = st.text_area("🎬 シチュエーション", "例: 好きな食べ物について話しましょう。", height=100)
    uploaded_file = st.file_uploader("📁 資料読み込み", type=["pdf", "txt"])
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

# システム命令（指示をより厳密に）
system_instruction = f"""
あなたは{questioner}です。ユーザー{user_name}のレベル{level}に合わせて英会話してください。
シチュエーションは{situation}です。
必ず [フィードバック]（日本語）と [英語の質問]（英語＋カッコ内に日本語訳）の形式で出力してください。
"""

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_played_msg_idx" not in st.session_state:
    st.session_state.last_played_msg_idx = -1

# 会話開始
if start_button:
    st.session_state.chat_session = genai.GenerativeModel(selected_model, system_instruction=system_instruction).start_chat(history=[])
    st.session_state.messages = []
    st.session_state.last_played_msg_idx = -1
    response = st.session_state.chat_session.send_message("シチュエーションを開始して、最初の質問を英語でしてください。")
    st.session_state.messages.append({"role": "assistant", "content": response.text})

# 会話終了
if end_button and "chat_session" in st.session_state:
    response = st.session_state.chat_session.send_message("これまでの会話を終了し、良かった点と改善点を日本語で総評してください。")
    st.session_state.messages.append({"role": "assistant", "content": response.text})

# チャット表示
if "chat_session" in st.session_state:
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "[英語の質問]" in message["content"]:
                # ★改善：カッコ内の日本語を除去して英語だけを読み上げる★
                raw_english = message["content"].split("[英語の質問]")[1].strip()
                clean_english = re.sub(r'\(.*?\)', '', raw_english).strip() # カッコ内を削除
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
    audio_value = st.audio_input("録音ボタン（マイク）")

    # ★改善：録音データを即座に処理する★
    if audio_value:
        audio_bytes = audio_value.getvalue()
        if "last_audio_bytes" not in st.session_state or st.session_state.last_audio_bytes != audio_bytes:
            st.session_state.last_audio_bytes = audio_bytes
            with st.spinner("AIが聞き取っています..."):
                try:
                    # 音声を文字起こし
                    trans_model = genai.GenerativeModel(selected_model)
                    res = trans_model.generate_content([{"mime_type": "audio/wav", "data": audio_bytes}, "聞こえた英語をそのまま文字起こししてください。"])
                    user_text = res.text.strip()
                    if user_text:
                        # ユーザーの発言を記録
                        st.session_state.messages.append({"role": "user", "content": user_text})
                        # AIの返答を取得
                        ai_res = st.session_state.chat_session.send_message(user_text)
                        st.session_state.messages.append({"role": "assistant", "content": ai_res.text})
                        st.rerun() # ここで画面を更新して即座に反映
                except: st.error("うまく聞き取れませんでした。もう一度お願いします。")

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
