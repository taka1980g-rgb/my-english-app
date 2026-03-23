import streamlit as st
import google.generativeai as genai
import io
import re
import PyPDF2
from datetime import datetime
import asyncio
import edge_tts

# === 🎨 デザインカスタマイズ ===
st.markdown("""
    <style>
    div[data-testid="stVerticalBlockBorderWrapper"] { background-color: #F3F8FF !important; border: 2px solid #D0E3FF !important; border-radius: 10px; padding: 15px; }
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

# === 🧹 便利ツール（キャッシュで無駄を徹底削減！） ===
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
        if not s.strip(): continue
        word_count = len(s.split())
        if current_word_count + word_count > max_words and current_block:
            blocks.append(" ".join(current_block))
            current_block = [s]
            current_word_count = word_count
        else:
            current_block.append(s)
            current_word_count += word_count
    if current_block: blocks.append(" ".join(current_block))
    return blocks

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

@st.cache_data
def extract_text_from_pdf(file_bytes):
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    return "".join([page.extract_text() + "\n" for page in reader.pages])

@st.cache_data
def get_cached_dictionary(text):
    dict_ai = genai.GenerativeModel("gemini-2.5-flash-lite")
    dict_prompt = f"以下の英単語または英語フレーズの日本語の意味を、簡潔にわかりやすく教えてください。\n\n対象: {text}"
    return dict_ai.generate_content(dict_prompt).text.strip()

@st.cache_data
def get_transcription(audio_bytes):
    transcriber = genai.GenerativeModel("gemini-2.5-flash")
    res = transcriber.generate_content([{"mime_type": "audio/wav", "data": audio_bytes}, "英語を文字起こししてください。文字のみ出力。"])
    return res.text.strip() if res.parts else ""

st.title("🎧 シャドーイング道場")
st.write("お手本を聞いて、限界まで自力で練習！自信がついたらAIの厳格チェックに挑みましょう。")

if "shadowing_history" not in st.session_state: st.session_state.shadowing_history = []
if "shadowing_script" not in st.session_state: st.session_state.shadowing_script = ""

# ==========================================
# 1. 教材セットアップエリア
# ==========================================
st.header("📂 1. 教材の準備")
setup_tab1, setup_tab2, setup_tab3, setup_tab4 = st.tabs(["🔄 ロールプレイから", "✨ AIにおまかせ生成", "📝 自分で入力", "📁 ファイル読み込み"])

with setup_tab1:
    st.write("🗣️ さっきまでロールプレイで話していた「AIの質問」をまとめて引き継ぎます。")
    if st.button("今日のロールプレイ履歴を読み込む", type="primary"):
        script = ""
        if "messages" in st.session_state:
            for m in st.session_state.messages:
                if m["role"] == "assistant" and "[英語の質問]" in m["content"]:
                    script += m["content"].split("[英語の質問]")[1].strip() + "\n\n"
        if script:
            st.session_state.shadowing_script = script.strip()
            st.session_state.pop("shadowing_chunks", None)
            st.session_state.shadowing_history = []
            st.session_state.pop("shadowing_evaluation", None)
            st.success("読み込み完了！下へ進んでください。")
        else:
            st.warning("履歴が見つかりません。先にロールプレイモードで会話してください。")

with setup_tab2:
    level = st.selectbox("難易度（対象レベル）", ["1: 幼児・超初心者", "2: 小学生・英検5級", "3: 中学生・英検3級", "4: 高校生・英検2級", "5: 上級・英検準1級〜"])
    col1, col2 = st.columns(2)
    with col1: script_length = st.selectbox("文章のボリューム", ["短め（3〜4文）", "標準（5〜7文）", "長め（8〜10文）"])
    with col2: user_name = st.text_input("あなたの名前（AIが呼びかけに使います）", value="Naoyuki")
    sit = st.text_input("シチュエーション", "例: 空港での入国審査")
    
    if st.button("AIにスクリプトを作ってもらう"):
        with st.spinner("台本を作成中..."):
            ai = genai.GenerativeModel("gemini-2.5-flash")
            prompt = f"シャドーイング用の英語スクリプトを作成してください。レベル: {level}\n状況: {sit}\n長さ: {script_length}\n学習者の名前: {user_name}\n【厳守】プレースホルダーは絶対使用不可。出力は英語のセリフのみ（解説不要）。"
            try:
                st.session_state.shadowing_script = ai.generate_content(prompt).text
                st.session_state.pop("shadowing_chunks", None)
                st.session_state.shadowing_history = [] 
                st.session_state.pop("shadowing_evaluation", None) 
                st.success("生成完了！下へ進んでください。")
            except Exception as e:
                st.error(f"生成エラー: {e}")

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

with setup_tab4:
    st.write("📄 **PDFやテキストファイルから英文を読み込みます。**")
    uploaded_file = st.file_uploader("スクリプトや教材ファイル（.txt または .pdf）", type=["txt", "pdf"])
    if uploaded_file:
        st.markdown("---")
        st.write("📥 **どちらの方法で読み込みますか？**")
        col_direct, col_extract = st.columns(2)
        
        with col_direct:
            if st.button("① そのまま台本にする\n(前回保存したファイル等)", use_container_width=True):
                with st.spinner("読み込み中..."):
                    try:
                        raw_text = extract_text_from_pdf(uploaded_file.getvalue()) if uploaded_file.name.endswith('.pdf') else uploaded_file.read().decode('utf-8')
                        if raw_text.strip():
                            st.session_state.shadowing_script = raw_text.strip()
                            st.session_state.pop("shadowing_chunks", None)
                            st.session_state.shadowing_history = []
                            st.session_state.pop("shadowing_evaluation", None)
                            st.session_state.pop("extracted_blocks", None)
                            st.session_state.pop("manual_edit_text", None)
                            st.success("セット完了！下へ進んでください。")
                    except Exception as e:
                        st.error(f"読み込みエラー: {e}")

        with col_extract:
            if st.button("② AIで英文のみ抽出\n(PDF教材などノイズが多い時)", use_container_width=True):
                with st.spinner("ファイルから英文だけを抽出中..."):
                    try:
                        raw_text = extract_text_from_pdf(uploaded_file.getvalue()) if uploaded_file.name.endswith('.pdf') else uploaded_file.read().decode('utf-8')
                        if raw_text.strip():
                            ai = genai.GenerativeModel("gemini-2.5-flash-lite")
                            extracted_text = ai.generate_content(f"以下のテキストから英語の文章のみを抽出して。日本語解説や記号は除外。\n\n{raw_text}").text
                            blocks = [b.strip() for b in extracted_text.split('\n') if b.strip()]
                            st.session_state.extracted_blocks = blocks
                            st.session_state.block_checks = [True] * len(blocks)
                            st.success("抽出完了！下のリストで不要な行のチェックを外してください。")
                    except Exception as e:
                        st.error(f"抽出エラー: {e}")

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
            st.success("編集エリアに送りました！")
            
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

st.markdown("---")

# ==========================================
# 2. チャンク分割と練習エリア
# ==========================================
st.header("🏋️ 2. トレーニング")

if st.session_state.shadowing_script:
    col_title, col_save = st.columns([2, 1])
    with col_title: st.write("📖 **現在のスクリプト（全体・ブロック再生）**")
    with col_save:
        today_str = datetime.now().strftime("%Y-%m-%d")
        st.download_button("💾 この台本を保存する(次回用)", data=st.session_state.shadowing_script, file_name=f"{today_str}_shadowing_script.txt", mime="text/plain", use_container_width=True)
    
    block_display_mode = st.radio("👀 画面表示モード", ["英語を表示", "ブラインド（文字を隠す）"], horizontal=True, key="block_display")
    
    if block_display_mode == "英語を表示":
        edited_script = st.text_area("長すぎる箇所や難しい単語があれば自由に書き換えて、下の「更新」ボタンを押してください。", value=st.session_state.shadowing_script, height=150)
        if st.button("🔄 スクリプトを更新して音声をリセットする"):
            st.session_state.shadowing_script = edited_script.strip()
            st.session_state.pop("shadowing_chunks", None)
            st.session_state.shadowing_history = []
            get_tts_audio.clear() # 更新した時はキャッシュをクリアする
            st.success("スクリプトを更新しました！お手本音声も新しく作られます。")
            st.rerun()
    else:
        st.info("🔒 ブラインドモード起動中（テキスト編集エリアを隠しています。耳だけを頼りにシャドーイングしましょう！）")

    st.write("") 
    script_blocks = split_script_into_blocks(st.session_state.shadowing_script)
    for idx, block in enumerate(script_blocks):
        if block_display_mode == "英語を表示": st.info(block)
        else: st.info("🔒 *(Text Hidden - 耳だけを頼りに！)*")
            
        if st.button(f"🔊 パート {idx + 1} のお手本を聞く", key=f"play_part_{idx}"):
            with st.spinner("高品質な音声を生成中..."):
                speak_text = clean_text_for_tts(block)
                if speak_text:
                    try:
                        audio_bytes = get_tts_audio(speak_text)
                        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                    except Exception as e:
                        st.error(f"音声の生成に失敗しました。詳細: {e}")
    
    st.write("")
    with st.expander("💡 ちょこっと翻訳・辞書ツール（通信料節約）"):
        st.write("練習に進む前に、わからない単語やフレーズがあればここへコピペして調べられます。")
        with st.form("quick_trans_form", clear_on_submit=False):
            q_text = st.text_input("意味が分からない単語やフレーズ:", placeholder="例: looking forward to")
            q_btn = st.form_submit_button("日本語の意味を調べる🔍")
            
        if q_btn and q_text:
            with st.spinner("AIがサクッと調べています..."):
                try:
                    res_text = get_cached_dictionary(q_text)
                    st.success(f"🇯🇵 **意味:**\n{res_text}")
                except Exception as e:
                    st.error(f"検索に失敗しました: {e}")
                    
    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔊 全文のお手本を一気に通しで聞く", use_container_width=True):
            with st.spinner("高品質な音声を生成中..."):
                speak_text = clean_text_for_tts(st.session_state.shadowing_script)
                if speak_text:
                    try:
                        audio_bytes = get_tts_audio(speak_text)
                        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                    except Exception as e:
                        st.error(f"音声の生成に失敗: {e}")

    with col2:
        if st.button("✂️ さらに「1文ずつ」に分割してAI特訓に進む", type="primary", use_container_width=True):
            with st.spinner("AIが和訳と分割を行っています... (※ここで1回だけ通信します)"):
                ai = genai.GenerativeModel("gemini-2.5-flash")
                split_prompt = f"以下の英文を意味のまとまりに分割し、それぞれに日本語訳をつけてください。\n【出力フォーマット】\n英語 || 日本語訳\n\n英文:\n{st.session_state.shadowing_script}"
                try:
                    res = ai.generate_content(split_prompt).text
                    chunks = []
                    for line in res.split('\n'):
                        if '||' in line:
                            en, ja = line.split('||', 1)
                            chunks.append({"en": en.strip(), "ja": ja.strip()})
                    st.session_state.shadowing_chunks = chunks
                except Exception as e:
                    st.error(f"分割に失敗しました。詳細: {e}")

    st.markdown("---")

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
            if speak_text:
                try:
                    audio_bytes = get_tts_audio(speak_text)
                    st.audio(audio_bytes, format="audio/mp3")
                except Exception: pass

            test_audio = st.audio_input("マイクで録音する", key=f"sh_mic_{i}")
            if test_audio:
                if st.button("📤 この発音をAIに判定してもらう", key=f"sh_btn_{i}", type="primary"):
                    with st.spinner("鬼判定中..."):
                        try:
                            user_spoken = get_transcription(test_audio.getvalue())
                            st.write(f"🎤 あなたの発音: **{user_spoken}**")

                            judge_prompt = f"お手本:「{chunk['en']}」\n発音:「{user_spoken}」\n【判定ルール】句読点や大文字小文字の違いは【絶対に無視】してください。純粋に「発音された単語」に違いや抜け漏れがある場合のみ、日本語で1文で厳しく指摘してください。完全に一致していれば合格としてください。"
                            judge_model = genai.GenerativeModel("gemini-2.5-flash")
                            judge_text = judge_model.generate_content(judge_prompt).text.strip()
                            st.success(f"🤖 判定: {judge_text}")
                            
                            st.session_state.shadowing_history.append({"お手本": chunk['en'], "ユーザー発音": user_spoken, "AI判定": judge_text})
                        except Exception as e:
                            st.error(f"判定エラーが発生しました: {e}")

    st.markdown("---")
    
    st.header("🏆 3. 今日の総評")
    st.write("シャドーイング練習お疲れ様でした！最後に今日の頑張りをAIコーチに評価してもらいましょう。")
    
    if st.button("🛑 今日の練習を終了して総評をもらう", use_container_width=True):
        if not st.session_state.shadowing_history:
            st.warning("まだAI判定を受けていないようです。まずは上のチャンクごとにマイクで発音を判定してみましょう！")
        else:
            with st.spinner("AIコーチが今日の頑張りを評価しています..."):
                try:
                    history_text = "".join([f"\n【{idx}回目】\nお手本: {r['お手本']}\n発音: {r['ユーザー発音']}\n判定: {r['AI判定']}\n" for idx, r in enumerate(st.session_state.shadowing_history, 1)])
                    evaluation_prompt = f"あなたは情熱的な発音コーチ。以下の履歴をもとに褒めて総評を出力。\n{history_text}\n\n【本日のシャドーイングスコア】\n- 発音の正確さ: 〇/100点\n- 流暢さ・再現度: 〇/100点\n- 練習への熱意: 〇/100点\n- 総合スコア: 〇/100点\n\n【良かった点・褒めポイント】\n（具体的に箇条書き）\n\n【今後の課題・アドバイス】\n（傾向があれば指摘）"
                    eval_model = genai.GenerativeModel("gemini-2.5-flash")
                    st.session_state.shadowing_evaluation = eval_model.generate_content(evaluation_prompt).text.strip()
                except Exception as e:
                    st.error(f"評価の作成に失敗: {e}")
                    
    if "shadowing_evaluation" in st.session_state:
        st.success("🎉 **AIコーチからの総評**")
        st.markdown(st.session_state.shadowing_evaluation)
