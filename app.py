import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import PyPDF2
import io
import time
import re

# ==========================================================
# 🔑 ここに取得したAPIキーを貼り付けてください（" " の中にコピペ）
# ==========================================================
MY_API_KEY = "AIzaSyDJeJIYgFQ9pE6uMTjE1U5D2STMTX5uPjs"

st.title("My English Roleplay AI 🗣️")

# APIキーが入力されていない場合の警告
if MY_API_KEY == "ここにAPIキーを貼り付けてください" or MY_API_KEY == "":
    st.error("⚠️ プログラムの12行目にある「MY_API_KEY」に、実際のAPIキーを貼り付けて保存してください！")
    st.stop()

if "api_calls" not in st.session_state:
    st.session_state.api_calls = []

current_time = time.time()
st.session_state.api_calls = [t for t in st.session_state.api_calls if current_time - t < 60]

MAX_CALLS = 15
used_calls = len(st.session_state.api_calls)
remain_calls = MAX_CALLS - used_calls

with st.sidebar:
    st.header("⚙️ 設定メニュー")
    
    selected_model = "gemini-1.5-flash"
    try:
        genai.configure(api_key=MY_API_KEY.strip())
        models_info = genai.list_models()
        available_models = [m.name.replace("models/", "") for m in models_info if 'generateContent' in m.supported_generation_methods]
        
        if available_models:
            st.write("🧠 AIモデル")
            default_idx = 0
            for i, m_name in enumerate(available_models):
                if "1.5-pro" in m_name:
                    default_idx = i
                    break
            selected_model = st.selectbox("使用中の脳みそ", available_models, index=default_idx)
    except Exception:
        pass
            
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
    situation = st.text_area(
        "🎬 シチュエーション", 
        "例: 私は海外旅行中の観光客です。空港で入国審査を受けています。審査官として質問してください。",
        height=100
    )
    
    st.markdown("---")
    st.write("📁 資料を読み込ませる")
    uploaded_file = st.file_uploader("PDF/TXTファイル", type=["pdf", "txt"])
    
    start_button = st.button("▶️ 会話をリセットしてスタート")
    
    st.markdown("---")
    end_button = st.button("🛑 会話を終了して評価をもらう")
    
    st.markdown("---")
    st.subheader("🔋 無料AIパワー (1分間)")
    ratio = max(0.0, min(1.0, remain_calls / MAX_CALLS))
    st.progress(ratio)
    
    if remain_calls <= 3 and used_calls > 0:
        wait_sec = int(60 - (current_time - st.session_state.api_calls[0]))
        st.warning(f"休憩タイム: あと {max(0, wait_sec)}秒☕")
    else:
        st.write(f"残り通信回数: {remain_calls} / {MAX_CALLS} 回")

def extract_text(file):
    text = ""
    if file.name.endswith('.pdf'):
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    elif file.name.endswith('.txt'):
        text = file.read().decode('utf-8')
    return text

doc_text = ""
if uploaded_file is not None:
    doc_text = extract_text(uploaded_file)

system_instruction = f"""
あなたは優秀なネイティブ英語教師であり、英会話のロールプレイング相手です。

【設定レベル】: {level}
【シチュエーション】: {situation}
【参考資料】: {doc_text}

ルール:
1. ユーザーの【設定レベル】に合わせて、使用する英単語の難易度や文章の長さを厳密に調整してください。
2. ユーザーが英語で返答したら、文法チェックや自然な表現を日本語でフィードバックしてください。
3. 必ず以下の「指定フォーマット」で出力してください。

[フィードバック]
（ここに日本語での文法チェックや解説）
[英語の質問]
（ここに次にユーザーに投げかける英語の質問文）
"""

if "chat_session" not in st.session_state or start_button:
    try:
        model = genai.GenerativeModel(selected_model, system_instruction=system_instruction)
        st.session_state.chat_session = model.start_chat(history=[])
        st.session_state.messages = []
        
        st.session_state.api_calls.append(time.time())
        response = st.session_state.chat_session.send_message("シチュエーションを開始して、最初の質問を英語でしてください。")
        st.session_state.messages.append({"role": "assistant", "content": response.text})
    except Exception as e:
        st.error(f"AIの準備中にエラーが発生しました: {e}")

if end_button and "chat_session" in st.session_state:
    with st.spinner("AIが成績をまとめています..."):
        try:
            st.session_state.api_calls.append(time.time())
            summary_prompt = "ここまでの会話を終了します。私の英語の文法、語彙力、コミュニケーション力について、良かった点と今後の課題を日本語で総評してください。"
            response = st.session_state.chat_session.send_message(summary_prompt)
            st.session_state.messages.append({"role": "user", "content": "（会話を終了し、評価をリクエストしました）"})
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error("評価の作成中にエラーが発生しました。")

# === チャット履歴の表示 ===
for message in st.session_state.messages:
    if "role" in message and "content" in message:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if message["role"] == "assistant" and "[英語の質問]" in message["content"]:
                english_part = message["content"].split("[英語の質問]")[1].strip()
                if english_part:
                    try:
                        tts = gTTS(text=english_part, lang='en')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        fp.seek(0)
                        st.audio(fp, format="audio/mp3")
                    except Exception:
                        pass

# === ここから：マイクと文字入力を「AIのすぐ下」にまとめて表示 ===
st.markdown("---")
st.write("🗣️ **あなたのターン（音声か文字で返答してください）**")

# 音声入力（マイク）
prompt = None
audio_value = st.audio_input("マイクを押して録音開始 / 停止")

if audio_value is not None:
    audio_bytes = audio_value.getvalue()
    if "last_audio_bytes" not in st.session_state or st.session_state.last_audio_bytes != audio_bytes:
        st.session_state.last_audio_bytes = audio_bytes
        with st.spinner("音声を文字に変換しています..."):
            try:
                mime_type = audio_value.type if hasattr(audio_value, 'type') else "audio/wav"
                audio_data = {"mime_type": mime_type, "data": audio_bytes}
                
                transcriber = genai.GenerativeModel(selected_model)
                st.session_state.api_calls.append(time.time())
                res = transcriber.generate_content([audio_data, "聞こえた英語をそのまま文字起こししてください。文字のみを出力してください。"])
                
                if res.parts:
                    prompt = res.text.strip()
                else:
                    st.warning("音声から文字を抽出できませんでした。")
            except Exception as e:
                st.error("エラー: もう少しゆっくり、はっきりと話してみてください。")

# 文字入力（テキスト）
with st.form("text_input_form", clear_on_submit=True):
    col1, col2 = st.columns([4, 1])
    with col1:
        text_prompt = st.text_input("文字で入力する場合:", label_visibility="collapsed", placeholder="英語で入力...")
    with col2:
        submit_btn = st.form_submit_button("送信📤")
        
    if submit_btn and text_prompt:
        prompt = text_prompt

# 送信処理
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.spinner("AIが返答を考えています..."):
        try:
            st.session_state.api_calls.append(time.time())
            response = st.session_state.chat_session.send_message(prompt)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun() # 画面を更新して新しいメッセージを表示
        except Exception as e:
            if "429" in str(e):
                st.error("⚠️ 無料枠の休憩タイムです。少し待ってから送信してください☕")
            else:
                st.error("返答の作成中にエラーが発生しました。")
