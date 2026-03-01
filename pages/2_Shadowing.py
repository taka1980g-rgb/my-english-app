import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import io
import re
import PyPDF2

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

# ★追加：長文を「約1分（約130単語）」ごとの意味段落に綺麗に分割する関数
def split_script_into_blocks(text, max_words=130):
    # ピリオド、！、？の後にスペースがある場所で文を分割
    sentences = re.split(r'(?<=[.!?])\s+', text)
    blocks = []
    current_block = []
    current_word_count = 0
    
    for s in sentences:
        if not s.strip(): 
            continue
        word_count = len(s.split())
        # 次の文を足すと文字数オーバーになる場合は、現在のブロックを保存して新しいブロックへ
        if current_word_count + word_count > max_words and current_block:
            blocks.append(" ".join(current_block))
            current_block = [s]
            current_word_count = word_count
        else:
            current_block.append(s)
            current_word_count += word_count
            
    # 最後のブロックを追加
    if current_block:
        blocks.append(" ".join(current_block))
        
    return blocks

st.title("🎧 シャドーイング道場")
st.write("お手本を聞いて、限界まで自力で練習！自信がついたらAIの厳格チェックに挑みましょう。")

if "shadowing_history" not in st.session_state:
    st.session_state.shadowing_history = []

# ==========================================
# 1. 教材セットアップエリア
# ==========================================
st.header("📂 1. 教材の準備")

setup_tab1, setup_tab2, setup_tab3, setup_tab4 = st.tabs(["🔄 ロールプレイから引継ぐ", "✨ AIにおまかせ生成", "📝 自分で英文を入力", "📁 ファイルを読み込む"])

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
            st.session_state.shadowing_history = []
            st.session_state.pop("shadowing_evaluation", None)
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
            st.session_state.shadowing_history = [] 
            st.session_state.pop("shadowing_evaluation", None) 
            st.success("生成完了！下へ進んでください。")

# タブ3：フリー入力
with setup_tab3:
    manual_text = st.text_area("練習したい英文を貼り付けてください", height=150)
    if st.button("この英文を使う"):
        if manual_text.strip():
            st.session_state.shadowing_script = manual_text.strip()
            st.session_state.pop("shadowing_chunks", None)
            st.session_state.shadowing_history = [] 
            st.session_state.pop("shadowing_evaluation", None) 
            st.success("セット完了！下へ進んでください。")
        else:
            st.warning("英文を入力してください。")

# タブ4：ファイル読み込み
with setup_tab4:
    st.write("📄 **PDFやテキストファイルから英文だけを抽出します。**")
    uploaded_file = st.file_uploader("スクリプトや教材ファイル（.txt または .pdf）", type=["txt", "pdf"])
    
    if st.button("このファイルから英文を抽出する"):
        if uploaded_file:
            with st.spinner("ファイルから英文だけを抽出中..."):
                try:
                    raw_text = ""
                    if uploaded_file.name.endswith('.pdf'):
                        reader = PyPDF2.PdfReader(uploaded_file)
                        raw_text = "".join([page.extract_text() + "\n" for page in reader.pages])
                    else:
                        raw_text = uploaded_file.read().decode('utf-8')
                    
                    if raw_text.strip():
                        ai = genai.GenerativeModel("gemini-2.5-flash-lite")
                        extract_prompt = f"以下のテキストから、英語の文章（セリフやスクリプト）のみを抽出してください。日本語の解説や目次、不要な記号などは完全に除外し、純粋な英語のテキストだけを出力してください。\n\n{raw_text}"
                        extracted_text = ai.generate_content(extract_prompt).text
                        
                        st.session_state.shadowing_script = extracted_text.strip()
                        st.session_state.pop("shadowing_chunks", None)
                        st.session_state.shadowing_history = []
                        st.session_state.pop("shadowing_evaluation", None)
                        st.success("ファイルの読み込みと英文抽出が完了しました！下へ進んでください。")
                    else:
                        st.warning("ファイルからテキストを読み込めませんでした。")
                except Exception as e:
                    st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")
        else:
            st.warning("ファイルをアップロードしてください。")

st.markdown("---")

# ==========================================
# 2. チャンク分割と練習エリア
# ==========================================
st.header("🏋️ 2. トレーニング")

if st.session_state.shadowing_script:
    st.write("📖 **現在のスクリプト（ブロック表示）**")
    
    # ★変更：長文を約1分ごとのブロックに分割して表示
    script_blocks = split_script_into_blocks(st.session_state.shadowing_script)
    
    for idx, block in enumerate(script_blocks):
        st.info(block)
        if st.button(f"🔊 パート {idx + 1} のお手本を聞く", key=f"play_part_{idx}"):
            with st.spinner("音声を生成中..."):
                speak_text = clean_text_for_tts(block)
                try:
                    tts = gTTS(text=speak_text, lang='en')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    fp.seek(0)
                    st.audio(fp, format="audio/mp3", autoplay=True)
                except Exception:
                    st.error("音声の生成に失敗しました。")
    
    st.write("") # スペース確保
    
    # 全文再生ボタンと1文特訓ボタンはそのまま共存
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔊 全文のお手本を一気に通しで聞く", use_container_width=True):
            with st.spinner("音声を生成中...（長文の場合は数秒かかります）"):
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
        if st.button("✂️ さらに「1文ずつ」に分割してAI特訓に進む", type="primary", use_container_width=True):
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

# 分割されたチャンクの表示と練習UI（以降は変更なし）
if "shadowing_chunks" in st.session_state and st.session_state.shadowing_chunks:
    st.write("🎯 **1文ずつの特訓＆AI判定**")
    display_mode = st.radio("👀 画面表示モード", ["英語 ＋ 和訳", "英語のみ", "ブラインド（文字を隠す）"], horizontal=True)

    for i, chunk in enumerate(st.session_state.shadowing_chunks):
        with st.container(border=True):
            if display_mode == "英語 ＋ 和訳":
                st.markdown(f"**🇺🇸 {chunk['en']}**")
                st.caption(f"🇯🇵 {chunk['ja']}")
            elif display_mode == "英語のみ":
                st.markdown(f"**🇺🇸 {chunk['en']}**")
            else:
                st.markdown("🔒 *(Text Hidden - 耳だけを頼りに！)*")

            speak_text = clean_text_for_tts(chunk['en'])
            try:
                tts = gTTS(text=speak_text, lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                fp.seek(0)
                st.audio(fp, format="audio/mp3")
            except Exception:
                pass

            test_audio = st.audio_input("マイクで録音する", key=f"sh_mic_{i}")
            if test_audio:
                if st.button("📤 この発音をAIに判定してもらう", key=f"sh_btn_{i}", type="primary"):
                    with st.spinner("鬼判定中..."):
                        try:
                            transcriber = genai.GenerativeModel("gemini-2.5-flash")
                            res = transcriber.generate_content([{"mime_type": "audio/wav
