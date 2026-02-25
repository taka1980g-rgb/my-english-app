import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import PyPDF2
import io

st.title("My English Roleplay AI 🗣️")
st.write("左側のメニューで設定を行い、英会話をスタートしましょう！")

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
    
    start_button = st.button("この設定で会話をスタート")

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
    
    # 資料のテキスト化
    doc_text = ""
    if uploaded_file is not None:
        doc_text = extract_text(uploaded_file)
        st.sidebar.success("資料の読み込みが完了しました！")

    # AIへの強力な指示書（プロンプト）
    system_instruction = f"""
    あなたは優秀なネイティブ英語教師であり、英会話のロールプレイング相手です。
    
    【設定レベル】: {level}
    【シチュエーション】: {situation}
    【参考資料】: {doc_text}
    
    ルール:
    1. ユーザーの【設定レベル】に合わせて、使用する英単語の難易度や文章の長さを厳密に調整してください。
    2. 【参考資料】がある場合は、必ずその資料の内容に基づいた質疑応答を行ってください。
    3. ユーザーが英語で返答したら、文法チェックやより自然な表現を日本語でフィードバックしてください。
    4. 必ず以下の「指定フォーマット」で出力してください。これ以外の書き方は絶対にしないでください。
    
    [フィードバック]
    （ここに日本語での文法チェックや解説。最初のターンの場合は「設定を読み込みました。会話をスタートします」等でOK）
    [英語の質問]
    （ここに次にユーザーに投げかける英語の質問文。※この部分だけがシステムによって音声化されます）
    """
    
    if "chat_session" not in st.session_state or start_button:
        try:
            model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction)
            st.session_state.chat_session = model.start_chat(history=[])
            st.session_state.messages = []
            
            response = st.session_state.chat_session.send_message("シチュエーションを開始して、最初の質問を英語でしてください。")
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AIの準備中にエラーが発生しました: {e}")

    # これまでの会話履歴と音声再生ボタンを画面に表示
    for message in st.session_state.messages:
        if "role" in message and "content" in message:
            with st.chat_message(message["role"]):
                # 画面にはAIのテキストをそのまま表示
                st.markdown(message["content"])
                
                # AIの返答の中に[英語の質問]という区切りがあれば、そこだけを抜き出して音声化する
                if message["role"] == "assistant" and "[英語の質問]" in message["content"]:
                    english_part = message["content"].split("[英語の質問]")[1].strip()
                    if english_part:
                        try:
                            tts = gTTS(text=english_part, lang='en')
                            fp = io.BytesIO()
                            tts.write_to_fp(fp)
                            fp.seek(0)
                            # 音声プレイヤーを表示（ここでは自動再生しない）
                            st.audio(fp, format="audio/mp3")
                        except Exception as e:
                            st.warning("音声の生成に失敗しました。")

    # ユーザーの入力欄と送信処理
    if prompt := st.chat_input("英語で返答を入力してください..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
                # 返答が来たら、最新の英語部分だけを「自動再生」する
                if "[英語の質問]" in response.text:
                    english_part = response.text.split("[英語の質問]")[1].strip()
                    if english_part:
                        tts = gTTS(text=english_part, lang='en')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        fp.seek(0)
                        # autoplay=True で自動的に喋り出す
                        st.audio(fp, format="audio/mp3", autoplay=True)
            except Exception as e:
                st.error(f"返答の作成中にエラーが発生しました: {e}")
else:
    st.info("👈 左側のメニューにAPIキーを入力すると、AIとの会話画面が表示されます。")
