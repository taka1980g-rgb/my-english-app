import streamlit as st
import google.generativeai as genai
import PyPDF2
import io
import json
import re
from datetime import datetime
import asyncio
import edge_tts

# === 🎨 画面デザインのカスタマイズ（CSS） ===
st.markdown("""
    <style>
    div[data-testid="stVerticalBlockBorderWrapper"] { background-color: #FFFDE7 !important; border: 2px solid #FFF59D !important; border-radius: 10px; padding: 15px; }
    div[data-testid="stForm"] { background-color: #FFFFFF !important; border: 1px solid #E0E4E8 !important; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# === 🚪 入場パスワードのチェック ===
if not st.session_state.get("password_correct", False):
    st.warning("👈 左上の「＞」を押して、ホーム画面から合言葉を入力してください。")
    st.stop()

if "log_save_count" not in st.session_state: st.session_state.log_save_count = 1

# === 🔑 API設定 ===
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("⚠️ StreamlitのSettingsから「Secrets」を開き、GEMINI_API_KEY を設定してください！")
    st.stop()
genai.configure(api_key=MY_API_KEY.strip())

# === 🧹 便利ツール（キャッシュで無駄を徹底削減！） ===
def clean_text_for_tts(text):
    text = re.sub(r'[*_#~]', '', text)
    text = re.sub(r"(?<!\w)['\"]|['\"](?!\w)", '', text)
    return text.strip()

@st.cache_data
def get_tts_audio(text, voice="en-US-AriaNeural"):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def _generate():
        communicate = edge_tts.Communicate(text, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
    result = loop.run_until_complete(_generate())
    loop.close()
    return result

# 【無駄②解消】PDFのテキスト抽出をキャッシュ化
@st.cache_data
def extract_text_from_pdf(file_bytes):
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    return "".join([page.extract_text() + "\n" for page in reader.pages])

# 【無駄③解消】翻訳と辞書の通信結果をキャッシュ化
@st.cache_data
def get_cached_translation(text, model_name):
    t_ai = genai.GenerativeModel(model_name)
    return t_ai.generate_content(f"以下を日本語に翻訳して:\n{text}").text

@st.cache_data
def get_cached_dictionary(word, model_name):
    d_ai = genai.GenerativeModel(model_name)
    return d_ai.generate_content(f"「{word}」の意味と簡単な例文を1つ教えて。簡潔に。").text

st.title("My English Roleplay AI 🗣️")

with st.sidebar:
    st.header("⚙️ 設定メニュー")
    model_options = {"賢い・やや遅い": "gemini-2.5-flash", "最速・低コスト": "gemini-2.5-flash-lite"}
    selected_model = model_options[st.selectbox("使用中の脳みそ", list(model_options.keys()), index=0)]
    
    st.markdown("---")
    st.write("📂 **設定の読み込み**")
    setting_file = st.file_uploader("保存した設定（.json）をアップロード", type=["json"])
    loaded_settings = json.load(setting_file) if setting_file else {}

    def_level = loaded_settings.get("level", "2: 初心者（日常会話の基礎）")
    level_list = [
        "1: 超初心者（簡単な単語・短い文・ゆっくり）", "2: 初心者（日常会話の基礎）", 
        "3: 中級者（自然な表現・標準的な速度）", "4: 上級者（ビジネスや専門的な語彙）", 
        "5: 専門家（ネイティブレベル・複雑な議論）"
    ]
    level_idx = level_list.index(def_level) if def_level in level_list else 1
    level = st.selectbox("📈 会話のレベル", level_list, index=level_idx)

    user_name = st.text_input("📛 あなたの名前（呼ばれ方）", value=loaded_settings.get("user_name", ""), placeholder="例: masa") or "Anata"
    questioner = st.text_input("👤 相手の役柄（詳細に）", value=loaded_settings.get("questioner", "同年代の気さくな友達"))
    situation = st.text_area("🎬 シチュエーション", value=loaded_settings.get("situation", "週末の予定について話しています。"), height=80)
    focus_words = st.text_input("🎯 練習したい単語・テーマ (任意)", value=loaded_settings.get("focus_words", ""))
    
    doc_text = loaded_settings.get("doc_text", "")
    uploaded_file = st.file_uploader("新しい資料 (PDF/TXT)", type=["pdf", "txt"])
    if uploaded_file:
        if uploaded_file.name.endswith('.pdf'):
            doc_text = extract_text_from_pdf(uploaded_file.getvalue())
        else:
            doc_text = uploaded_file.read().decode('utf-8')
        st.success("資料を読み込みました！")

    st.markdown("---")
    current_settings = {"level": level, "user_name": user_name, "questioner": questioner, "situation": situation, "focus_words": focus_words, "doc_text": doc_text}
    st.download_button("💾 現在の設定を保存（.json）", data=json.dumps(current_settings, ensure_ascii=False, indent=2), file_name="english_settings.json", mime="application/json", use_container_width=True)

    start_button = st.button("▶️ 会話をリセットしてスタート", type="primary", use_container_width=True)
    end_button = st.button("🛑 会話を終了して評価をもらう", use_container_width=True)

    st.markdown("---")
    st.write("📊 **今日の学習記録**")
    if "stats_turns" not in st.session_state:
        st.session_state.stats_turns = 0
        st.session_state.stats_mistakes = 0
    st.write(f"- 発話ターン数: {st.session_state.stats_turns} 回")
    st.write(f"- リピート練習: {st.session_state.stats_mistakes} 回")

system_instruction = f"""
あなたは英会話のロールプレイング相手です。
【相手の役柄】: {questioner}
【ユーザーの名前】: {user_name}
【レベル】: {level}
【状況】: {situation}
【重点テーマ】: {focus_words}
【資料】: {doc_text}

【絶対に守るべき厳格なルール】
1. あなたの出力は、以下の「指定フォーマット」のブロックのみで構成してください。
2. 「はい、承知しました」などの会話のシステム的な前置きは絶対に出力しないでください。
3. 英文中で単語を強調する際は、必ずMarkdownの太字（**単語**）を使用してください。
4. 【重要】指定フォーマット内の括弧（ ）は説明書きです。出力する際は括弧そのものを削除し、中身のテキストだけを出力してください。

【指定フォーマット】※以下のA・B・Cのいずれかのみ
▼ パターンA：ユーザーの英語にミス・不自然さがある場合
[フィードバック]
- （日本語でのミスの指摘と解説）
- 和訳: （すぐ下の[リピート練習]の英文の日本語訳）
[リピート練習]
（ユーザーが復唱するための、正しい英語のセリフのみ。記号は使わない）

▼ パターンB：ユーザーの英語が自然、または開始時
[フィードバック]
- （日本語で短く褒める、または相槌）
[英語の質問]
（役柄としてユーザーに投げかける英語のセリフや質問文のみ）

▼ パターンC：やり直しを頼まれた場合
[フィードバック]
- （日本語で「もう一度言いますね」と短く返事）
[英語の質問]
（直前と全く同じ英語の質問文）
"""

if "last_played_msg_idx" not in st.session_state: st.session_state.last_played_msg_idx = -1

if start_button:
    try:
        model = genai.GenerativeModel(selected_model, system_instruction=system_instruction)
        st.session_state.chat_session = model.start_chat(history=[])
        st.session_state.messages = []
        st.session_state.last_played_msg_idx = -1
        st.session_state.stats_turns = 0
        st.session_state.stats_mistakes = 0
        st.session_state.is_review_mode = False 
        st.session_state.review_list = []
        response = st.session_state.chat_session.send_message("シチュエーションを開始して、最初の質問を英語でしてください。")
        st.session_state.messages.append({"role": "assistant", "content": response.text})
    except Exception as e:
        st.error(f"準備中にエラーが発生しました: {e}")

if "chat_session" in st.session_state:
    for i, message in enumerate(st.session_state.messages):
        if message["role"] == "user" and message["content"].startswith("（"): continue 
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                raw_text = ""
                if "[英語の質問]" in message["content"]: raw_text = message["content"].split("[英語の質問]")[1].strip()
                elif "[リピート練習]" in message["content"]: raw_text = message["content"].split("[リピート練習]")[1].strip()
                if raw_text:
                    try:
                        speak_text = clean_text_for_tts(raw_text)
                        audio_bytes = get_tts_audio(speak_text) # ←キャッシュ化により爆速化
                        auto_play = False
                        if i == len(st.session_state.messages) - 1 and st.session_state.last_played_msg_idx != i:
                            auto_play = True
                            st.session_state.last_played_msg_idx = i
                        st.audio(audio_bytes, format="audio/mp3", autoplay=auto_play)
                    except Exception: pass

    st.markdown("---")
    
    # 【無駄④解消】過去の会話履歴を直近4ラリー（8件）に絞って送る
    def get_trimmed_history():
        raw_history = st.session_state.messages[-8:] if len(st.session_state.messages) > 8 else st.session_state.messages
        formatted = []
        for m in raw_history:
            formatted.append({"role": "model" if m["role"] == "assistant" else "user", "parts": [m["content"]]})
        return formatted

    prompt = None
    display_prompt = None
    last_msg = st.session_state.messages[-1] if len(st.session_state.messages) > 0 else None
    
    is_practice = False
    target_practice_text = ""
    if last_msg and last_msg["role"] == "assistant" and "[リピート練習]" in last_msg["content"]:
        is_practice = True
        target_practice_text = last_msg["content"].split("[リピート練習]")[1].strip()

    if st.session_state.get("is_review_mode", False):
        st.header("📝 復習モード（一問一答）")
        st.write("今日の会話で登場した質問です。もう一度答えたい質問を選んで練習しましょう。")
        if not st.session_state.get("review_list"):
            st.info("復習する質問がありませんでした。")
        else:
            options = [f"{item['en']} （{item['ja']}）" if item['ja'] else item['en'] for item in st.session_state.review_list]
            selected_idx = st.selectbox("復習する質問を選んでください:", range(len(options)), format_func=lambda x: options[x])
            selected_item = st.session_state.review_list[selected_idx]
            selected_q = selected_item['en']
            
            st.info(f"**🇺🇸 質問**: {selected_q}\n\n**🇯🇵 和訳**: {selected_item['ja']}")
            st.write("🗣️ **この質問に英語で答えてみましょう**")
            review_audio = st.audio_input("回答を録音する", key=f"review_mic_{selected_idx}")
            
            if review_audio:
                if st.button("📤 回答を送信して添削してもらう", type="primary", use_container_width=True, key=f"review_btn_{selected_idx}"):
                    with st.spinner("AIが回答を添削中..."):
                        try:
                            transcriber = genai.GenerativeModel(selected_model)
                            res = transcriber.generate_content([{"mime_type": "audio/wav", "data": review_audio.getvalue()}, "英語を文字起こししてください。文字のみ出力。"])
                            user_spoken = res.text.strip() if res.parts else ""
                            st.write(f"🎤 あなたの回答: **{user_spoken}**")
                            
                            feedback_prompt = f"質問: {selected_q}\n生徒の回答: {user_spoken}\n以下のフォーマットで簡潔に日本語で出力。\n【評価】（良かった点）\n【改善点】（文法ミスなど）\n【模範解答】（より自然な英語の回答例を1〜2つ）"
                            teacher_model = genai.GenerativeModel(selected_model)
                            feedback_res = teacher_model.generate_content(feedback_prompt)
                            st.success(f"🤖 **AIコーチからの添削:**\n\n{feedback_res.text.strip()}")
                        except Exception:
                            st.error("エラーが発生しました。")

    elif is_practice:
        st.info("🔄 **リピート練習モード**：マイクで発音してみましょう。")
        practice_audio = st.audio_input("発音を録音する")
        
        if practice_audio:
            if st.button("🤖 AIに発音を判定してもらう", use_container_width=True):
                with st.spinner("AIが発音を判定中..."):
                    try:
                        transcriber = genai.GenerativeModel(selected_model)
                        res = transcriber.generate_content([{"mime_type": "audio/wav", "data": practice_audio.getvalue()}, "英語を文字起こししてください。文字のみ出力。"])
                        user_spoken = res.text.strip() if res.parts else ""
                        st.write(f"🎤 あなたの発音: **{user_spoken}**")
                        
                        judge_prompt = f"お手本:「{target_practice_text}」\n発音:「{user_spoken}」\n【判定ルール】句読点や大文字小文字は無視。発音された単語に抜け漏れや違いがある場合のみ厳しく指摘。完全一致で合格。"
                        judge_model = genai.GenerativeModel(selected_model)
                        judge_res = judge_model.generate_content(judge_prompt)
                        st.success(f"🤖 判定: {judge_res.text.strip()}")
                    except Exception:
                        st.error("聞き取れませんでした。")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ 練習完了！次へ進む", type="primary", use_container_width=True):
                prompt = "（リピート練習完了。会話を続けるための新しい質問を【パターンB】の形式でしてください。）"
                display_prompt = "（✅ 練習を完了し、次へ進みました）"
        with col2:
            if st.button("↩️ 練習せず1つ前の質問に答え直す (Undo)", use_container_width=True):
                if len(st.session_state.messages) >= 3:
                    st.session_state.messages = st.session_state.messages[:-2]
                    st.session_state.stats_mistakes -= 1
                    re_model = genai.GenerativeModel(selected_model, system_instruction=system_instruction)
                    st.session_state.chat_session = re_model.start_chat(history=get_trimmed_history())
                    st.session_state.last_played_msg_idx = -1
                    st.rerun()

    else:
        st.write("🗣️ **あなたのターン**")
        if st.button("🔄 今の質問をもう一度聞く（別の言い方で答え直したい時など）"):
            prompt = "すみません、あなたの今の質問にもう一度別の言い方で答えたいので、全く同じ質問文をもう一度言ってください。新しい質問はしないでください。"
            display_prompt = "（🔄 今の質問をもう一度繰り返してください）"

        audio_value = st.audio_input("マイクを押して回答を録音")
        if audio_value:
            if st.button("📤 この音声を文字起こしして送信する", type="primary", use_container_width=True):
                with st.spinner("文字に変換中..."):
                    try:
                        transcriber = genai.GenerativeModel(selected_model)
                        res = transcriber.generate_content([{"mime_type": "audio/wav", "data": audio_value.getvalue()}, "英語を文字起こししてください。文字のみ出力。"])
                        if res.parts:
                            prompt = res.text.strip()
                            display_prompt = prompt
                            st.session_state.stats_turns += 1
                    except Exception:
                        st.error("聞き取れませんでした。")

        st.markdown("---")
        with st.container(border=True):
            st.write("🛠️ **お助けツール（※会話は進みません）**")
            current_q = last_msg["content"].split("[英語の質問]")[1].strip() if last_msg and "[英語の質問]" in last_msg["content"] else ""

            if current_q:
                st.write("🇯🇵 **① 直前のセリフの日本語訳**")
                if st.button("日本語訳を見る"):
                    with st.spinner("翻訳中..."):
                        translation = get_cached_translation(current_q, selected_model)
                    st.info(f"🇯🇵 {translation}")

            st.write("💡 **② お助け翻訳（言いたいことが英語で出てこない時）**")
            with st.form("translation_form", clear_on_submit=False):
                col1, col2 = st.columns([4, 1])
                with col1: jp_text = st.text_input("日本語で入力:", label_visibility="collapsed", placeholder="例: もう一度ゆっくり言ってください")
                with col2: trans_btn = st.form_submit_button("英訳する🔄")
                    
            if trans_btn and jp_text:
                with st.spinner("AIが英訳を考えています..."):
                    try:
                        translator = genai.GenerativeModel(selected_model)
                        trans_prompt = f"以下の日本語を、英会話のセリフとして自然な英語に翻訳してください。出力は英語のセリフのみとし、解説や前置きは一切不要です。\n\n日本語: {jp_text}"
                        trans_res = translator.generate_content(trans_prompt)
                        st.success(f"✨ こんな風に言ってみましょう！\n\n### {trans_res.text.strip()}")
                    except Exception as e:
                        st.error("翻訳中にエラーが発生しました。")

            with st.form("dictionary_form", clear_on_submit=False):
                st.write("📖 **③ 単語辞書 / 文法**")
                dict_word = st.text_input("調べたい英単語や文法:", label_visibility="collapsed", placeholder="例: evidence, 現在完了形")
                if st.form_submit_button("調べる🔍"):
                    with st.spinner("検索中..."):
                        res = get_cached_dictionary(dict_word, selected_model)
                        st.info(res)

            st.write("🧠 **④ ちょい足しヒント（自力で答えるためのアシスト）**")
            with st.form("hint_form", clear_on_submit=False):
                hint_col1, hint_col2 = st.columns([3, 2])
                with hint_col1: hint_type = st.selectbox("ヒントの種類", ["使うべき単語を3つ", "文の出だし（3語）", "日本語でのアイデア"], label_visibility="collapsed")
                with hint_col2: hint_btn = st.form_submit_button("ヒントをもらう🆘")
                    
                if hint_btn:
                    if current_q:
                        with st.spinner("ヒントを作成中..."):
                            hint_ai = genai.GenerativeModel(selected_model)
                            if hint_type == "使うべき単語を3つ": hint_prompt = f"以下の質問に答えるために役立つ英単語（または熟語）を3つだけ、日本語の意味を添えて教えて。英語の正解は書かないで。\n質問: {current_q}"
                            elif hint_type == "文の出だし（3語）": hint_prompt = f"以下の質問に答えるための、自然な英文の書き出し（最初の3〜5語のみ）を1つ教えて。日本語訳や解説は不要。\n質問: {current_q}"
                            else: hint_prompt = f"以下の質問に対して、どのような内容を答えればよいか、日本語で簡潔に2つのアイデアを提案して。英語の解答例は書かないで。\n質問: {current_q}"
                            st.info(f"💡 **ヒント:**\n{hint_ai.generate_content(hint_prompt).text.strip()}")
                    else:
                        st.warning("ヒントを出せる質問が見つかりませんでした。")

            st.write("🏳️ **⑤ どうしても答えられない時**")
            if st.button("ギブアップ（解説と回答例を見て、リピート練習へ進む）"):
                st.session_state.stats_mistakes += 1
                prompt = """
                今の質問の意図がわかりません。通信量削減のため無駄な前置きは一切省き、以下の構成で出力してください。【新しい質問はせず】私がそのまま復唱できる回答例を提示してください。
                [フィードバック]
                - 直前の質問の英語と日本語訳
                - 質問の意図（1文で）
                - この状況での自然な回答例の解説と、【★重要：その回答例の日本語訳】
                [リピート練習]
                （私がそのまま復唱して答えるための、英語の回答例のセリフのみ。複数の場合は一番標準的なものを1つだけ。絶対に新しい質問はしないこと）
                """
                display_prompt = "（🏳️ ギブアップして、解説と回答例をリクエストしました）"

    if prompt and display_prompt:
        st.session_state.messages.append({"role": "user", "content": display_prompt})
        with st.spinner("AIが返答を考えています..."):
            try:
                trim_model = genai.GenerativeModel(selected_model, system_instruction=system_instruction)
                st.session_state.chat_session = trim_model.start_chat(history=get_trimmed_history()[:-1])
                response = st.session_state.chat_session.send_message(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                if "[リピート練習]" in response.text: st.session_state.stats_mistakes += 1
                st.rerun() 
            except Exception as e:
                st.error("エラーが発生しました。")

if end_button and "chat_session" in st.session_state:
    with st.spinner("成績をまとめています..."):
        summary_prompt = "会話を終了します。通信量削減のため不要な前置きは省いてください。まずはたくさん褒めて、その後本日の評価を「本日のスコア(各項目100点満点)」「良かった点」「今後の課題」の構成で出力してください。"
        try:
            res = st.session_state.chat_session.send_message(summary_prompt)
            st.session_state.messages.append({"role": "user", "content": "（終了して評価をリクエスト）"})
            st.session_state.messages.append({"role": "assistant", "content": res.text})
            
            st.session_state.is_review_mode = True
            review_qs = []
            for m in st.session_state.messages:
                if m["role"] == "assistant" and "[英語の質問]" in m["content"]:
                    q = m["content"].split("[英語の質問]")[1].strip()
                    if q not in review_qs: review_qs.append(q)
            review_qs = review_qs[-50:]
            
            st.session_state.review_list = []
            if review_qs:
                try:
                    transl_prompt = "以下の英文を日本語に翻訳してください。出力は必ず「英語 || 日本語訳」という形式で1行ずつ出力し、余計な説明は一切省いてください。\n\n" + "\n".join(review_qs)
                    t_model = genai.GenerativeModel(selected_model)
                    t_res = t_model.generate_content(transl_prompt).text
                    for line in t_res.split("\n"):
                        if "||" in line:
                            en, ja = line.split("||", 1)
                            st.session_state.review_list.append({"en": en.strip(), "ja": ja.strip()})
                except Exception:
                    pass
                if len(st.session_state.review_list) == 0:
                    st.session_state.review_list = [{"en": q, "ja": ""} for q in review_qs]
            st.rerun()
        except Exception:
            st.error("評価の作成に失敗しました。")
