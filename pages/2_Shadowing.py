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

def split_script_into_blocks(text, max_words=130):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    blocks = []
    current_block = []
    current_word_count = 0
    
    for s in sentences:
        if not s.strip(): 
            continue
        word_count = len(s.split())
        if current_word_count + word_count > max_words and current_block:
            blocks.append(" ".join(current_block))
            current_block = [s]
            current_word_count = word_count
        else:
            current_block.append(s)
            current_word_count += word_count
            
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

setup_tab1, setup_tab2, setup_tab3, setup_tab4 = st.tabs(["🔄 ロールプレイから", "✨ AIにおまかせ生成", "📝 自分で入力", "📁 ファイル読み込み"])

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
        user_name = st.text_input("あなたの名前（AIが呼びかけに使います）", value="Naoyuki")
        
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

# タブ4：高度なファイル読み込み
with setup_tab4:
    st.write("📄 **PDFやテキストファイルから英文だけを抽出し、好きな部分だけをスクリプトにします。**")
    uploaded_file = st.file_uploader("スクリプトや教材ファイル（.txt または .pdf）", type=["txt", "pdf"])
    
    if st.button("① このファイルから英文を抽出する"):
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
                        extract_prompt = f"以下のテキストから、英語の文章（セリフやスクリプト）のみを抽出してください。日本語の解説や目次、不要な記号などは完全に除外し、純粋な英語のテキストだけを出力してください。改行は元の文章のまとまりを維持してください。\n\n{raw_text}"
                        extracted_text = ai.generate_content(extract_prompt).text
                        
                        blocks = [b.strip() for b in extracted_text.split('\n') if b.strip()]
                        st.session_state.extracted_blocks = blocks
                        st.session_state.block_checks = [True] * len(blocks)
                        st.success("抽出完了！下のリストで不要な行のチェックを外してください。")
                    else:
                        st.warning("ファイルからテキストを読み込めませんでした。")
                except Exception as e:
                    st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")
        else:
            st.warning("ファイルをアップロードしてください。")

    # 取捨選択エリア
    if st.session_state.get("extracted_blocks"):
        st.markdown("### ✂️ ② 取捨選択（不要なものはチェックを外す）")
        
        col_all, col_none = st.columns(2)
        if col_all.button("☑️ すべて選択"):
            st.session_state.block_checks = [True] * len(st.session_state.extracted_blocks)
            st.rerun()
        if col_none.button("⬜️ すべて解除"):
            st.session_state.block_checks = [False] * len(st.session_state.extracted_blocks)
            st.rerun()
            
        for idx, block in enumerate(st.session_state.extracted_blocks):
            st.session_state.block_checks[idx] = st.checkbox(block, value=st.session_state.block_checks[idx], key=f"chk_{idx}")
            
        if st.button("⬇️ ③ チェックした英文を編集エリアへ送る", type="primary"):
            selected = [b for i, b in enumerate(st.session_state.extracted_blocks) if st.session_state.block_checks[i]]
            st.session_state.manual_edit_text = "\n\n".join(selected)
            st.success("編集エリアに送りました！下で最終調整してください。")
            
    # 最終調整エリア
    if "manual_edit_text" in st.session_state:
        st.markdown("### 📝 ④ 最終調整")
        final_text = st.text_area("ここで自由に文字を修正・削除できます", value=st.session_state.manual_edit_text, height=200)
        
        if st.button("🚀 このテキストで練習開始！"):
            if final_text.strip():
                st.session_state.shadowing_script = final_text.strip()
                st.session_state.pop("shadowing_chunks", None)
                st.session_state.shadowing_history = []
                st.session_state.pop("shadowing_evaluation", None)
                st.session_state.pop("extracted_blocks", None)
                st.session_state.pop("manual_edit_text", None)
                st.success("セット完了！下へ進んでください。")
                st.rerun()
            else:
                st.warning("英文を入力してください。")

st.markdown("---")

# ==========================================
# 2. チャンク分割と練習エリア
# ==========================================
st.header("🏋️ 2. トレーニング")

if st.session_state.shadowing_script:
    
    st.write("📖 **現在のスクリプト（全体・ブロック再生）**")
    
    block_display_mode = st.radio("👀 画面表示モード", ["英語を表示", "ブラインド（文字を隠す）"], horizontal=True, key="block_display")
    
    if block_display_mode == "英語を表示":
        edited_script = st.text_area("長すぎる箇所や難しい単語があれば自由に書き換えて、下の「更新」ボタンを押してください。", value=st.session_state.shadowing_script, height=150)
        if st.button("🔄 スクリプトを更新して音声をリセットする"):
            st.session_state.shadowing_script = edited_script.strip()
            st.session_state.pop("shadowing_chunks", None)
            st.session_state.shadowing_history = []
            st.success("スクリプトを更新しました！お手本音声も新しく作られます。")
            st.rerun()
    else:
        st.info("🔒 ブラインドモード起動中（テキスト編集エリアを隠しています。耳だけを頼りにシャドーイングしましょう！）")

    st.write("") 
    
    # ブロック分割表示
    script_blocks = split_script_into_blocks(st.session_state.shadowing_script)
    for idx, block in enumerate(script_blocks):
        if block_display_mode == "英語を表示":
            st.info(block)
        else:
            st.info("🔒 *(Text Hidden - 耳だけを頼りに！)*")
            
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
    
    st.write("")
    
    # ★追加機能：ちょこっと翻訳・辞書ツール
    with st.expander("💡 ちょこっと翻訳・辞書ツール（通信料節約）"):
        st.write("練習に進む前に、わからない単語やフレーズがあればここへコピペして調べられます。")
        with st.form("quick_trans_form", clear_on_submit=False):
            q_text = st.text_input("意味が分からない単語やフレーズ:", placeholder="例: looking forward to")
            q_btn = st.form_submit_button("日本語の意味を調べる🔍")
            
        if q_btn and q_text:
            with st.spinner("AIがサクッと調べています..."):
                try:
                    # 通信料の安いLiteモデルを使用
                    dict_ai = genai.GenerativeModel("gemini-2.5-flash-lite")
                    dict_prompt = f"以下の英単語または英語フレーズの日本語の意味を、簡潔にわかりやすく教えてください。\n\n対象: {q_text}"
                    dict_res = dict_ai.generate_content(dict_prompt)
                    st.success(f"🇯🇵 **意味:**\n{dict_res.text.strip()}")
                except Exception as e:
                    st.error("検索に失敗しました。")
                    
    st.write("")
    
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

# 分割されたチャンクの表示と練習UI
if "shadowing_chunks" in st.session_state and st.session_state.shadowing_chunks:
    st.write("🎯 **1文ずつの特訓＆AI判定**")
    display_mode = st.radio("👀 画面表示モード", ["英語 ＋ 和訳", "英語のみ", "ブラインド（文字を隠す）"], horizontal=True, key="chunk_display")

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
                            res = transcriber.generate_content([{"mime_type": "audio/wav", "data": test_audio.getvalue()}, "英語を文字起こししてください。文字のみ出力。"])
                            user_spoken = res.text.strip() if res.parts else ""
                            st.write(f"🎤 あなたの発音: **{user_spoken}**")

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
                            judge_text = judge_res.text.strip()
                            st.success(f"🤖 判定: {judge_text}")
                            
                            st.session_state.shadowing_history.append({
                                "お手本": chunk['en'],
                                "ユーザー発音": user_spoken,
                                "AI判定": judge_text
                            })
                            
                        except Exception:
                            st.error("エラーが発生しました。")

    st.markdown("---")
    
    # ==========================================
    # 3. 総評エリア
    # ==========================================
    st.header("🏆 3. 今日の総評")
    st.write("シャドーイング練習お疲れ様でした！最後に今日の頑張りをAIコーチに評価してもらいましょう。")
    
    if st.button("🛑 今日の練習を終了して総評をもらう", use_container_width=True):
        if not st.session_state.shadowing_history:
            st.warning("まだAI判定を受けていないようです。まずは上のチャンクごとにマイクで発音を判定してみましょう！")
        else:
            with st.spinner("AIコーチが今日の頑張りを評価しています..."):
                try:
                    history_text = ""
                    for idx, record in enumerate(st.session_state.shadowing_history, 1):
                        history_text += f"\n【{idx}回目】\n"
                        history_text += f"お手本: {record['お手本']}\n"
                        history_text += f"発音: {record['ユーザー発音']}\n"
                        history_text += f"判定: {record['AI判定']}\n"
                        
                    evaluation_prompt = f"""
                    あなたは情熱的で優しい英語の発音コーチです。
                    生徒が今日のシャドーイング練習を終えました。以下の「AI判定履歴」をもとに、今日の頑張りをたくさん褒めて、総評を出力してください。
                    
                    【生徒の練習履歴】
                    {history_text}
                    
                    以下のフォーマットで出力してください。前置きは不要です。
                    
                    【本日のシャドーイングスコア】
                    - 発音の正確さ: 〇/100点
                    - 流暢さ・再現度: 〇/100点
                    - 練習への熱意: 〇/100点
                    - 総合スコア: 〇/100点
                    
                    【良かった点・褒めポイント】
                    - （具体的に良かった点を箇条書きでたくさん褒める）
                    
                    【今後の課題・アドバイス】
                    - （発音の傾向や苦手な単語があれば優しく指摘し、ポジティブにアドバイス）
                    """
                    
                    eval_model = genai.GenerativeModel("gemini-2.5-flash")
                    eval_res = eval_model.generate_content(evaluation_prompt)
                    
                    st.session_state.shadowing_evaluation = eval_res.text.strip()
                except Exception as e:
                    st.error(f"評価の作成に失敗しました。{e}")
                    
    if "shadowing_evaluation" in st.session_state:
        st.success("🎉 **AIコーチからの総評**")
        st.markdown(st.session_state.shadowing_evaluation)
