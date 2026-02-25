import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import PyPDF2
import io

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

# ==========================================================
# 🔑 StreamlitのSecrets（金庫）からAPIキーを自動で読み込む
# ==========================================================
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    MY_API_KEY = ""
    st.error("⚠️ StreamlitのSettingsから「Secrets」を開き、GEMINI_API_KEY を設定してください！")
    st.stop()

# APIキーをセット
genai.configure(api_key=MY_API_KEY.strip())

st.title("My English Roleplay AI 🗣️")

with st.sidebar:
    st.header("⚙️ 設定メニュー")
    
    # ★改善：無駄な通信を削り、モデルを2つに固定化★
    st.write("🧠 AIモデル")
    model_options = {
        "賢い・やや遅い": "gemini-2.5-flash",
        "最速・低コスト": "gemini-2.5-flash-lite"
    }
    # 画面に表示する名前を選ばせる（初期値は0番目のFlash）
    selected_display_name = st.selectbox(
        "使用中の脳みそ", 
        list(model_options.keys()), 
        index=0
    )
    # 選ばれた表示名から、裏側で使う本当のモデル名を引っ張り出す
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
        [
            "小学校の先生",
            "同年代の友達",
            "職場の先輩",
            "気さくな友達",
            "学会発表の聴衆",
            "その他（自由入力）"
        ]
    )
    
    if preset_questioner == "その他（自由入力）":
        questioner = st.text_input("自由に役割を入力してください", "例: 空港の入国審査官")
    else:
        questioner = preset_questioner
    
    st.markdown("---")
    situation = st.text_area(
        "🎬 シチュエーション", 
        "例: 小学校の授業",
        height=100
    )
    
    st.markdown("---")
    st.write("📁 資料を読み込ませる")
    uploaded_file = st.file_uploader("PDF/TXTファイル", type=["pdf", "txt"])
    
    st.markdown("---")
    start_button = st.button("▶️ 会話をリセットしてスタート", type="primary", use_container_width=True)
    end_button = st.button("🛑 会話を終了して評価をもらう", use_container_width=True)

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
あなたは英会話のロールプレイング相手です。

【あなたの役柄（AI自身）】: {questioner}
【ユーザーの名前】: {user_name}
【設定レベル】: {level}
【シチュエーション】: {situation}
【参考資料】: {doc_text}

厳密なルール:
1. あなた自身が【あなたの役柄】です。目の前にいる会話相手が【ユーザーの名前】です。
2. ユーザーの【設定レベル】に合わせて英単語の難易度や文章の長さを調整してください。
3. 通信量削減のため、感情表現や前置きは一切不要です。客観的かつ極めて簡潔に出力してください。
4. フィードバックは、必ずMarkdown形式の箇条書き（- ）を使用し、各項目の後には必ず改行を入れて、1行ずつ独立させて表示してください。横に繋げて書くのは厳禁です。
5. 必ず以下の「指定フォーマット」で出力してください。

[フィードバック]
- （文法チェックや指摘事項1）
- （文法チェックや指摘事項2）

[英語の質問]
（【あなたの役柄】としてユーザーに投げかける英語のセリフや質問文のみ）
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
        st.error(f"AIの準備中にエラーが発生しました: {e}")

if end_button and "chat_session" in st.session_state:
    with st.spinner("AIが成績をまとめています..."):
        try:
            summary_prompt = "ここまでの会話を終了します。通信量削減のため、前置きは省き、私の英語の文法、語彙力、コミュニケーション力について、良かった点と課題を各項目ごとに改行を入れた箇条書きで簡潔に総評してください。"
            response = st.session_state.chat_session.send_message(summary_prompt)
            st.session_state.messages.append({"role": "user", "content": "（会話を終了し、評価をリクエストしました）"})
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error("評価の作成中にエラーが発生しました。")

if "chat_session" in st.session_state:
    for i, message in enumerate(st.session_state.messages):
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
                            
                            auto_play = False
                            if i == len(st.session_state.messages) - 1 and st.session_state.last_played_msg_idx != i:
                                auto_play = True
                                st.session_state.last_played_msg_idx = i
                                
                            st.audio(fp, format="audio/mp3", autoplay=auto_play)
                        except Exception:
                            pass

    st.markdown("---")
    st.write("🗣️ **あなたのターン（わからない時はギブアップもOK！）**")

    prompt = None
    display_prompt = None

    if st.button("🆘 ギブアップ（今の質問の解説と回答例を見て次へ）"):
        prompt = """
        今の質問の意図がわかりません。通信量削減のため、無駄な前置きは一切省き、以下の構成で極めて簡潔に出力してください。必ず各項目のあとに改行を入れ、箇条書きが横に繋がらないようにしてください。その後、会話を続けるための【新しい別の質問】を英語で1つ投げかけてください。フォーマットは必ず [フィードバック] と [英語の質問] を守ってください。
        
        [フィードバック]
        - 直前の質問の英語と日本語訳
        - 質問の意図（1文で）
        - 回答例（英語と日本語、2パターン程度）
        """
        display_prompt = "（🆘 ギブアップして、質問の解説と回答例をリクエストしました）"

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
                    res = transcriber.generate_content([audio_data, "聞こえた英語をそのまま文字起こししてください。文字のみを出力してください。"])
                    
                    if res.parts:
                        prompt = res.text.strip()
                        display_prompt = prompt
                    else:
                        st.warning("音声から文字を抽出できませんでした。")
                except Exception as e:
                    st.error("エラー: もう少しゆっくり、はっきりと話してみてください。")

    st.markdown("---")
    st.write("💡 **お助け翻訳（言いたいことが英語で出てこない時）**")
    with st.form("translation_form", clear_on_submit=False):
        col1, col2 = st.columns([4, 1])
        with col1:
            jp_text = st.text_input("日本語で入力:", label_visibility="collapsed", placeholder="例: もう一度ゆっくり言ってください")
        with col2:
            trans_btn = st.form_submit_button("英訳する🔄")
            
    if trans_btn and jp_text:
        with st.spinner("AIが英訳を考えています..."):
            try:
                # 翻訳専用にAIを単発で呼び出す（本筋の会話履歴には影響させません）
                translator = genai.GenerativeModel(selected_model)
                trans_prompt = f"以下の日本語を、英会話のセリフとして自然な英語に翻訳してください。出力は英語のセリフのみとし、解説や前置きは一切不要です。\n\n日本語: {jp_text}"
                trans_res = translator.generate_content(trans_prompt)
                
                st.success(f"✨ こんな風に言ってみましょう！\n\n### {trans_res.text.strip()}\n\n👆 上のマイクボタンを押して、声に出して読んでみてください。")
            except Exception as e:
                st.error("翻訳中にエラーが発生しました。")

    if prompt and display_prompt:
        st.session_state.messages.append({"role": "user", "content": display_prompt})
        
        with st.spinner("AIが返答を考えています..."):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun() 
            except Exception as e:
                st.error("返答の作成中にエラーが発生しました。")
else:
    st.info("👈 左側のメニューで役割やシチュエーションを設定し、「▶️ 会話をリセットしてスタート」ボタンを押して開始してください。")
