import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import PyPDF2
import io
import time
import re

st.title("My English Roleplay AI 🗣️")
st.write("左側のメニューで設定を行い、英会話をスタートしましょう！")

# === 新機能：APIの利用回数（1分間）をカウントする準備 ===
if "api_calls" not in st.session_state:
    st.session_state.api_calls = []

# 過去60秒以内の通信記録だけを残す（古い履歴は消す）
current_time = time.time()
st.session_state.api_calls = [t for t in st.session_state.api_calls if current_time - t < 60]

# 1分間の制限（15回）
MAX_CALLS = 15
used_calls = len(st.session_state.api_calls)
remain_calls = MAX_CALLS - used_calls

# 左側のメニュー（サイドバー）
with st.sidebar:
    st.header("⚙️ 初期設定")
    api_key = st.text_input("Gemini APIキー", type="password")
    
    st.markdown("---")
    level = st.selectbox(
        "📈 会話のレベルを選択", 
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
        "🎬 シチュエーション設定", 
        "例: 私は海外旅行中の観光客です。空港で入国審査を受けています。審査官として質問してください。",
        height=100
    )
    
    st.markdown("---")
    st.write("📁 資料を読み込ませる（オプション）")
    uploaded_file = st.file_uploader("PDFまたはTXTファイルを選択", type=["pdf", "txt"])
    
    start_button = st.button("▶️ この設定で会話をスタート")
    
    st.markdown("---")
    st.header("🛑 会話の終了")
    end_button = st.button("会話を終了して最終評価をもらう")
    
    # === 新機能：体力ゲージの表示 ===
    st.markdown("---")
    st.subheader("🔋 1分間の無料AIパワー")
    # ゲージの長さを計算（0〜1の範囲に収める）
    ratio = max(0.0, min(1.0, remain_calls / MAX_CALLS))
    st.progress(ratio)
    
    if remain_calls <= 3 and used_calls > 0:
        # 一番古い通信が60秒経過して消えるまでの残り秒数を計算
        wait_sec = int(60 - (current_time - st.session_state.api_calls[0]))
        st.warning(f"⚠️ 少し休憩しましょう！あと {max(0, wait_sec)}秒 で回復します☕")
    else:
        st.write(f"残り通信回数: {remain_calls} / {MAX_CALLS} 回")

# アップロードされたファイルから文字を抽出する関数
def extract_text(file):
    text = ""
    if file.name.endswith('.pdf'):
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    elif file.name.endswith('.txt'):
        text = file.read().decode('utf-8')
    return text

# メインのプログラム
if api_key:
    clean_api_key = api_key.strip()
    genai.configure(api_key=clean_api_key)
    
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
            model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction)
            st.session_state.chat_session = model.start_chat(history=[])
            st.session_state.messages = []
            
            st.session_state.api_calls.append(time.time()) # 通信を記録
            response = st.session_state.chat_session.send_message("シチュエーションを開始して、最初の質問を英語でしてください。")
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AIの準備中にエラーが発生しました: {e}")

    # 終了ボタンが押された時の処理
    if end_button and "chat_session" in st.session_state:
        with st.spinner("AIが成績をまとめています..."):
            try:
                st.session_state.api_calls.append(time.time()) # 通信を記録
                summary_prompt = "ここまでの会話を終了します。私の英語の文法、語彙力、コミュニケーション力について、良かった点と今後の課題を日本語で総評してください。"
                response = st.session_state.chat_session.send_message(summary_prompt)
                st.session_state.messages.append({"role": "user", "content": "（会話を終了し、評価をリクエストしました）"})
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.success("会話を終了しました！最終評価をご確認ください。")
            except Exception as e:
                st.error("評価の作成中にエラーが発生しました。")

    # これまでの会話履歴と音声再生ボタンを表示
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

    st.markdown("---")
    st.subheader("👇 あなたのターンです 🗣️")
    st.info("マイクを押して話し始め、話し終わったら【もう一度マイクを押す】と送信されます。")
    
    prompt = None
    audio_value = st.audio_input("ここから音声を録音")

    if audio_value is not None:
        audio_bytes = audio_value.getvalue()
        if "last_audio_bytes" not in st.session_state or st.session_state.last_audio_bytes != audio_bytes:
            st.session_state.last_audio_bytes = audio_bytes
            with st.spinner("音声を文字に変換しています..."):
                try:
                    mime_type = audio_value.type if hasattr(audio_value, 'type') else "audio/wav"
                    audio_data = {"mime_type": mime_type, "data": audio_bytes}
                    
                    transcriber = genai.GenerativeModel('gemini-2.5-flash')
                    st.session_state.api_calls.append(time.time()) # 通信を記録
                    res = transcriber.generate_content([audio_data, "聞こえた英語をそのまま文字起こししてください。文字のみを出力してください。"])
                    
                    if res.parts:
                        prompt = res.text.strip()
                    else:
                        st.warning("音声から文字を抽出できませんでした。")
                except Exception as e:
                    if "429" in str(e):
                        match = re.search(r'retry in ([\d\.]+)s', str(e))
                        wait_t = int(float(match.group(1))) + 1 if match else 30
                        st.error(f"⚠️ 少し早口すぎたようです！無料枠の休憩タイムです。あと {wait_t}秒 お待ちください ☕")
                    else:
                        st.error(f"AIが音声を処理できませんでした: {e}")

    text_prompt = st.chat_input("または、キーボードで文字を入力...")
    if text_prompt:
        prompt = text_prompt

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                st.session_state.api_calls.append(time.time()) # 通信を記録
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
                if "[英語の質問]" in response.text:
                    english_part = response.text.split("[英語の質問]")[1].strip()
                    if english_part:
                        tts = gTTS(text=english_part, lang='en')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        fp.seek(0)
                        st.audio(fp, format="audio/mp3", autoplay=True)
            except Exception as e:
                if "429" in str(e):
                    match = re.search(r'retry in ([\d\.]+)s', str(e))
                    wait_t = int(float(match.group(1))) + 1 if match else 30
                    st.error(f"⚠️ 少し早口すぎたようです！無料枠の休憩タイムです。あと {wait_t}秒 お待ちください ☕")
                else:
                    st.error(f"返答の作成中にエラーが発生しました: {e}")
else:
    st.info("👈 左側のメニューにAPIキーを入力すると、AIとの会話画面が表示されます。")
