import streamlit as st
import google.generativeai as genai

# アプリのタイトル
st.title("My English Roleplay AI 🗣️")
st.write("左側のメニューを開いて、APIキーとシチュエーションを設定してください。")

# サイドバー（左側のメニュー）の設定
with st.sidebar:
    st.header("⚙️ 初期設定")
    st.write("Google AI Studioで取得したAPIキーを入力してください。")
    api_key = st.text_input("Gemini APIキー", type="password")
    
    st.markdown("---")
    st.write("練習したい状況や、使いたい資料の文章を入力してください。")
    situation = st.text_area(
        "シチュエーション設定", 
        "例: 私は海外旅行中の観光客です。空港で入国審査を受けています。審査官として質問してください。",
        height=150
    )
    start_button = st.button("この設定で会話をスタート")

# APIキーが入力されたら動くメインのプログラム
if api_key:
    # コピーした時の見えない空白（スペース）を自動で削除する
    clean_api_key = api_key.strip()
    genai.configure(api_key=clean_api_key)
    
    system_instruction = f"""
    あなたは優秀なネイティブ英語教師であり、英会話のロールプレイング相手です。
    現在のシチュエーションと設定資料は以下の通りです。
    【 {situation} 】
    
    以下のルールに必ず従って会話してください：
    1. まずあなたから、シチュエーションに合わせた自然な英語の質問を投げかけて会話をスタートしてください。
    2. ユーザーが英語で返答したら、まずその返答が文法的に正しいか、より自然な表現（修正案）はないかを日本語で優しくフィードバックしてください。
    3. フィードバックが終わったら、会話を続けるための次の質問を英語で1つだけ投げかけてください。
    """
    
    if "chat_session" not in st.session_state or start_button:
        try:
            # ★ここを現在稼働している最新のAIモデル名「gemini-2.5-flash」に修正しました★
            model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction)
            st.session_state.chat_session = model.start_chat(history=[])
            st.session_state.messages = []
            
            response = st.session_state.chat_session.send_message("シチュエーションを開始して、最初の質問を英語でしてください。")
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AIの準備中にエラーが発生しました: {e}")

    # これまでの会話履歴を画面に表示
    for message in st.session_state.messages:
        if "role" in message and "content" in message:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # ユーザーの入力欄と送信した時の動き
    if prompt := st.chat_input("英語で返答を入力してください..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"返答の作成中にエラーが発生しました: {e}")
else:
    st.info("👈 左側のメニューにAPIキーを入力すると、AIとの会話画面が表示されます。")
