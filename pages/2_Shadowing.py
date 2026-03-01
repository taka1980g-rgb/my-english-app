import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import io
import re

# === 🎨 デザインカスタマイズ ===
st.markdown("""
    <style>
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #F3F8FF !important;
        border: 2px solid #D0E3FF !important;
        border-radius: 10px;
        padding: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# === 🚪 ログインチェック ===
if not st.session_state.get("password_correct", False):
    st.warning("👈 左上の「＞」を押して、ホーム画面から合言葉を入力してください。")
    st.stop()

# === 🔑 API設定 ===
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=MY_API_KEY.strip())
except Exception:
    st.error("⚠️ Secretsから GEMINI_API_KEY を設定してください！")
    st.stop()

# === 🧹 テキストクリーナー ===
def clean_text_for_tts(text):
    text = re.sub(r'[*_#~]', '', text)
    text = re.sub(r"(?<!\w)['\"]|['\"](?!\w)", '', text)
    return text.strip()

st.title("🎧 シャドーイング道場")
st.write("お手本を聞いて、限界まで自力で練習！自信がついたらAIの厳格チェックに挑みましょう。")

# ==========================================
# 1. 教材セットアップエリア
# ==========================================
st.header("📂 1. 教材の準備")
setup_tab1, setup_tab2, setup_tab3 = st.tabs(["🔄 ロールプレイから引継ぐ", "✨ AIにおまかせ生成", "📝 自分で英文を入力"])

if "shadowing_script" not in st.session_state:
    st.session_state.shadowing_script = ""

# タブ1：ロールプレイ連携
with setup_tab1:
    st.write("🗣️ さっきまでロールプレイで話していた「AIの質問」をまとめて引き継ぎます。")
    if st.button("今日のロールプレイ履歴を読み込む", type="primary"):
        script = ""
        if "messages" in st.session_state:
            for m in st.session_state.messages:
                if m["role"] == "assistant" and "[英語の質問]" in m["content"]:
                    q = m["content"].split("[英語の質問]")[1].strip()
                    script += q + "\n\n"
        if script:
            st.session_state.shadowing_script = script.strip()
            st.session_state.pop("shadowing_chunks", None) 
            st.success("読み込み完了！下へ進んでください。")
        else:
            st.warning("履歴が見つかりません。先にロールプレイモードで会話してください。")

# タブ2：AI自動生成
with setup_tab2:
    level = st.selectbox("難易度（対象レベル）", [
        "1: 幼児・超初心者（短い挨拶、簡単な単語）",
        "2: 小学生・英検5級（基礎的な自己紹介）",
        "3: 中学生・英検3級（日常的な出来事）",
        "4: 高校生・英検2級（やや長めの文）",
        "5: 上級・英検準1級〜（複雑な構文）"
    ])
    
    col1, col2 = st.columns(2)
    with col1:
        script_length = st.selectbox("文章のボリューム", ["短め（3〜4文）", "標準（5〜7文）", "長め（8〜10文）"])
    with col2:
        user_name = st.text_input("あなたの名前（AIが呼びかけに使います）", value="masa")
        
    sit = st.text_input("シチュエーション", "例: 空港での入国審査")
    
    if st.button("AIにスクリプトを作ってもらう"):
        with st.spinner("台本を作成中..."):
            ai = genai.GenerativeModel("gemini-2.5-flash")
            prompt = f"""
            シャドーイング用の英語スクリプトを作成してください。
            レベル: {level}
            状況: {sit}
            長さ: {script_length}
            学習者の名前: {user_name}

            【厳守事項】
            1. [Your Name] や [City] のようなプレースホルダー（穴埋め表記）は**絶対に**使用しないでください。
            2. 名前を呼ぶ必要がある場合は「{user_name}」を使用してください。
            3. 地名、職業、その他固有名詞が必要な場合は、AI自身が自然な架空の名称を考えて、具体的な単語として出力してください。
            4. 出力は英語のセリフのみとしてください（日本語の解説や前置きは一切不要）。
            """
            st.session_state.shadowing_script = ai.generate_content(prompt).text
            st.session_state.pop("shadowing_chunks", None) 
            st.success("生成完了！下へ進んでください。")

# タブ3：フリー入力
with setup_tab3:
    manual_text = st.text_area("練習したい英文を貼り付けてください", height=150)
    if st.button("この英文を使う"):
        if manual_text.strip():
            st.session_state.shadowing_script = manual_text.strip()
            st.session_state.pop("shadowing_chunks", None)
            st.success("セット完了！下へ進んでください。")
        else:
            st.warning("英文を入力してください。")

st.markdown("---")

# ==========================================
# 2. チャンク分割と練習エリア
# ==========================================
st.header("🏋️ 2. トレーニング")

if st.session_state.shadowing_script:
    st.write("📖 **現在のスクリプト（全文）**")
    st.info(st.session_state.shadowing_script)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔊 全文のお手本を通しで聞く", use_container_width=True):
            with st.spinner("音声を生成中..."):
                speak_text = clean_text_for_tts(st.session_state.shadowing_script)
                try:
                    tts = gTTS(text=speak_text, lang='en')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    fp.seek(0)
                    st.audio(fp, format="audio/mp3", autoplay=True)
                except Exception:
                    st.error("音声の生成に失敗しました。")

    with col2:
        if st.button("✂️ 1文ずつに分割して特訓する", type="primary", use_container_width=True):
            with st.spinner("AIが和訳と分割を行っています... (※ここで1回だけ通信します)"):
                ai = genai.GenerativeModel("gemini-2.5-flash")
                split_prompt = f"""
                以下の英文を、意味のまとまり（または1文ごと）に分割し、それぞれに日本語訳をつけてください。
                【出力フォーマット（厳守）】
                英語 || 日本語訳
                
                英文:
                {st.session_state.shadowing_script}
                """
                try:
                    res = ai.generate_content(split_prompt).text
                    chunks = []
                    for line in res.split('\n'):
                        if '||' in line:
                            en, ja = line.split('||', 1)
                            chunks.append({"en": en.strip(), "ja": ja.strip()})
                    st.session_state.shadowing_chunks = chunks
                except Exception:
                    st.error("分割に失敗しました。もう一度試してください。")

    st.markdown("---")

# 分割されたチャンクの表示と練習UI
if "shadowing_chunks" in st.session_state and st.session_state.shadowing_chunks:
    st.write("🎯 **1文ずつの特訓＆AI判定**")
    display_mode = st.radio("👀 画面表示モード", ["英語 ＋ 和訳", "英語のみ", "ブラインド（文字を隠す）"], horizontal=True)

    for i, chunk in enumerate(st.session_state.shadowing_chunks):
        with st.container(border=True):
            # 1. 表示切替
            if display_mode == "英語 ＋ 和訳":
                st.markdown(f"**🇺🇸 {chunk['en']}**")
                st.caption(f"🇯🇵 {chunk['ja']}")
            elif display_mode == "英語のみ":
                st.markdown(f"**🇺🇸 {chunk['en']}**")
            else:
                st.markdown("🔒 *(Text Hidden - 耳だけを頼りに！)*")

            # 2. お手本音声（通信料ゼロのgTTS）
            speak_text = clean_text_for_tts(chunk['en'])
            try:
                tts = gTTS(text=speak_text, lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                fp.seek(0)
                st.audio(fp, format="audio/mp3")
            except Exception:
                pass

            # 3. テスト録音（ここぞという時だけ送信）
            test_audio = st.audio_input("マイクで録音する", key=f"sh_mic_{i}")
            if test_audio:
                if st.button("📤 この発音をAIに判定してもらう", key=f"sh_btn_{i}", type="primary"):
                    with st.spinner("鬼判定中..."):
                        try:
                            # 文字起こし
                            transcriber = genai.GenerativeModel("gemini-2.5-flash")
                            res = transcriber.generate_content([{"mime_type": "audio/wav", "data": test_audio.getvalue()}, "英語を文字起こししてください。文字のみ出力。"])
                            user_spoken = res.text.strip() if res.parts else ""
                            st.write(f"🎤 あなたの発音: **{user_spoken}**")

                            # ★修正ポイント：記号と大文字小文字を完全に無視させるプロンプト
                            judge_prompt = f"""
                            お手本:「{chunk['en']}」
                            発音:「{user_spoken}」
                            
                            【判定ルール】
                            上記2つを比較し、英単語が一言一句同じか判定してください。
                            ただし、ピリオド(.)、カンマ(,)、感嘆符(!)、疑問符(?)などの「句読点の有無や違い」や、「大文字・小文字の違い」は【絶対に無視】してください。
                            純粋に「発音された単語」に違いや抜け漏れがある場合のみ、日本語で1文で厳しく指摘してください。完全に一致していれば合格としてください。
                            """
                            judge_model = genai.GenerativeModel("gemini-2.5-flash")
                            judge_res = judge_model.generate_content(judge_prompt)
                            st.success(f"🤖 判定: {judge_res.text.strip()}")
                        except Exception:
                            st.error("エラーが発生しました。")
