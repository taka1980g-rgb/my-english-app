import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import PyPDF2
import io
import re  # 正規表現（カッコ除去用）を追加

# === 🎨 デザインの追加（見た目だけを変える安全なコード） ===
st.markdown("""
    <style>
    /* 録音ボタンを目立たせる */
    [data-testid="stAudioInput"] {
        border: 2px solid #FF4B4B;
        border-radius: 15px;
        padding: 10px;
        background-color: #FFF5F5;
        margin-bottom: 20px;
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
    st.error("⚠️ Secretsを設定してください！")
    st.stop()

genai.configure(api_key=MY_API_KEY.strip())

st.title("My English Roleplay AI 🗣️")

with st.sidebar:
    st.header("⚙️ 設定メニュー")
    
    st.write("🧠 AIモデル")
    model_options = {
        "Gemini 2.5 Flash (高速・汎用)": "gemini-2.5-flash",
        "Gemini 2.5 Flash-Lite (最速・低コスト)": "gemini-2.5-flash-lite"
    }
    selected_display_name = st.selectbox("使用中の脳みそ", list(model_options.keys()), index=0)
    selected_model = model_options[selected_display_name]
            
    st.markdown("---")
    level = st.selectbox(
        "📈 会話のレベル", 
        [
            "1: 超初心者（簡単な単語・短い文・ゆっくり）", 
            "2: 初心者（日常会話の基礎）", 
            "3: 中級者（自然な表現・標準的な速度）", 
            "4: 上級者（ビジネスや専門的な語彙）", 
            "5: 専門家（ネイティブレベル・複雑な議論）"
        ]
    )

    st.markdown("---")
    input_name = st.text_input("📛 あなたの名前（呼ばれ方）", placeholder="例: masa")
    user_name = input_name if input_name else "Anata"
    
    st.markdown("---")
    st.write("👤 質問者（AIの役割）")
    preset_questioner = st.selectbox(
        "AIの役柄を選んでください",
        ["小学校の先生", "同年代の友達", "職場の先輩", "気さくな友達", "学会発表の聴衆", "その他（自由入力）"]
    )
    
    if preset_questioner == "その他（自由入力）":
        questioner = st.text_input("自由に役割を入力してください", "例: 空港の入国審査官")
    else:
        questioner = preset_questioner
    
    st.markdown("---")
    situation = st.text_area("🎬 シチュエーション", "例: 好きな食べ物について話しましょう。", height=100)
    
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
あなたは英会話のロールプレイング相手です。
【あなたの役柄】: {questioner}
【ユーザーの名前】: {user_name}
【設定レベル】: {level}
【シチュエーション】: {situation}
【参考資料】: {doc_text}

厳密なルール:
1. 感情表現や前置きは不要。簡潔に出力してください。
2. フィードバックはMarkdown形式の箇条書き（- ）で。
3. 必ず [フィードバック] と [英語の質問]（カッコ内に日本語訳）の形式で出力してください。
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
        response = st.session_state.chat_session.send_message("これまでの会話を終了し、簡潔に総評してください。")
        st.session_state.messages.append({"role": "assistant", "content": response.text})

if "chat_session" in st.session_state:
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "[英語の質問]" in message["content"]:
                english_part = message["content"].split("[英語の質問]")[1].strip()
                if english_part:
                    # ★改善：カッコ内の日本語を除去して英語だけを読み上げる★
                    clean_english = re.sub(r'\(.*?\)', '', english_part).strip()
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
    st.write("🗣️ **あなたのターン（わからない時はギブアップもOK！）**")

    prompt = None
    display_prompt = None

    if st.button("🆘 ギブアップ（解説を見る）"):
        prompt = "今の質問の意図、日本語訳、回答例を教えてください。その後、別の質問を英語でしてください。"
        display_prompt = "（🆘 ギブアップして、解説をリクエストしました）"

    audio_value = st.audio_input("マイクを押して録音開始 / 停止")

    if audio_value is not None:
        audio_bytes = audio_value.getvalue()
        if "last_audio_bytes" not in st.session_state or st.session_state.last_audio_bytes != audio_bytes:
            st.session_state.last_audio_bytes = audio_bytes
            with st.spinner("変換中..."):
                try:
                    transcriber = genai.GenerativeModel(selected_model)
                    res = transcriber.generate_content([{"mime_type": "audio/wav", "data": audio_bytes}, "聞こえた英語をそのまま文字起こししてください。"])
                    if res.text:
                        prompt = res.text.strip()
                        display_prompt = prompt
                except Exception as e:
                    st.error("エラー: もう少しはっきりと話してみてください。")

    with st.form("text_input_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            text_prompt = st.text_input("文字で入力:", label_visibility="collapsed", placeholder="英語で入力...")
        with col2:
            submit_btn = st.form_submit_button("送信📤")
        if submit_btn and text_prompt:
            prompt = text_prompt
            display_prompt = text_prompt

    if prompt and display_prompt:
        st.session_state.messages.append({"role": "user", "content": display_prompt})
        with st.spinner("AIが返答を考えています..."):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun() 
            except:
                st.error("エラーが発生しました。")
else:
    st.info("👈 左側のメニューを設定し、スタートボタンを押してください。")
