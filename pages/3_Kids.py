import streamlit as st
import google.generativeai as genai
import io
import re
import json
from datetime import datetime
import asyncio
import edge_tts

# === 🎨 キッズ専用・縦型スリム化デザイン ===
st.markdown("""
    <style>
    div[data-testid="block-container"] { max-width: 900px !important; padding-top: 2rem !important; padding-bottom: 2rem !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] { background-color: #FFFFE0 !important; border: 4px solid #FFD700 !important; border-radius: 15px !important; padding: 5px 15px !important; box-shadow: 0 5px 15px rgba(0,0,0,0.05) !important; }
    .english-text-container { font-size: 24px !important; font-weight: normal !important; color: #333333 !important; line-height: 1.6 !important; word-wrap: break-word; text-align: center; margin-bottom: 5px; }
    .english-text-container ruby { font-size: 24px !important; font-weight: normal !important; color: #333333 !important; margin-right: 8px !important; }
    .english-text-container rt { font-size: 12px !important; color: #FF4500 !important; font-weight: bold !important; }
    .ja-text { font-size: 15px !important; color: #666; font-weight: bold; margin-top: 0px; margin-bottom: 0px; text-align: center;}
    div.stButton > button { border-radius: 10px !important; font-size: 16px !important; font-weight: bold !important; padding: 5px !important; min-height: 0px !important; }
    div[data-testid="stAudioInput"] { margin-top: -10px !important; margin-bottom: -15px !important; }
    .levelup-box { text-align: center; padding: 10px; margin-top: 10px; margin-bottom: 10px; }
    .review-text { font-size: 20px !important; margin-bottom: 0px !important;}
    .review-text ruby { font-size: 20px !important; margin-right: 6px !important;}
    .review-text rt { font-size: 10px !important;}
    hr { margin: 10px 0 !important; border-top: 2px dashed #ccc !important;}
    </style>
    """, unsafe_allow_html=True)

# === 🚪 ログインチェック ===
if not st.session_state.get("password_correct", False):
    st.warning("👈 ひだりうえの「＞」をおして、あいことば をいれてね！")
    st.stop()

# === 🔑 API設定 ===
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=MY_API_KEY.strip())
except Exception:
    st.error("⚠️ APIキーが ないみたい！パパかママに きいてみてね。")
    st.stop()

# === 🧹 便利ツール（キャッシュで無駄を削減！） ===
def clean_text_for_tts(text):
    text = re.sub(r'[*_#~]', '', text)
    text = re.sub(r"(?<!\w)['\"]|['\"](?!\w)", '', text)
    return text.strip()

def apply_ruby_html(text):
    return re.sub(r'([A-Za-z.,!?\']+)\(([\u30A0-\u30FF\u3040-\u309F]+)\)', r'<ruby>\1<rt>\2</rt></ruby>', text)

def extract_tag(text, tag):
    pattern = f"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""

def get_hint_length_rule(level):
    if level <= 2: return "1文のみ"
    elif level <= 4: return "2文"
    else: return "3文"

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

# 【無駄①解消】文字起こし結果をキャッシュして二重通信を防ぐ
@st.cache_data
def get_transcription(audio_bytes):
    try:
        transcriber = genai.GenerativeModel("gemini-2.5-flash-lite")
        res = transcriber.generate_content([{"mime_type": "audio/wav", "data": audio_bytes}, "英語を文字起こししてください。文字のみ出力。"])
        return res.text.strip() if res.parts else "（がんばって こえ を だしたよ！）"
    except Exception:
        return "（うまくききとれなかったみたい）"

# === 💾 データの初期化 ===
if "kids_state" not in st.session_state: st.session_state.kids_state = "setup"
if "kids_stamps" not in st.session_state: st.session_state.kids_stamps = 0
if "kids_total_stamps" not in st.session_state: st.session_state.kids_total_stamps = 0
if "kids_level" not in st.session_state: st.session_state.kids_level = 1
if "kids_data" not in st.session_state: st.session_state.kids_data = {}
if "child_name" not in st.session_state: st.session_state.child_name = "おともだち"
if "final_sit" not in st.session_state: st.session_state.final_sit = ""
if "last_audio_hash" not in st.session_state: st.session_state.last_audio_hash = None
if "kids_feedback" not in st.session_state: st.session_state.kids_feedback = ""
if "pending_levelup" not in st.session_state: st.session_state.pending_levelup = False
if "last_user_spoken" not in st.session_state: st.session_state.last_user_spoken = ""
if "kids_display_mode" not in st.session_state: st.session_state.kids_display_mode = "🗣️ カタカナも"
if "kids_history_log" not in st.session_state: st.session_state.kids_history_log = []

sit_options = {
    "🍔 ハンバーガーやさん で おかいもの": "You are a friendly staff at a hamburger shop.",
    "🐶 どうぶつえん で ごあいさつ": "You are a friendly zookeeper showing animals.",
    "🍎 すきな フルーツを えらぼう": "You are a fruit shop owner asking what fruits the child likes.",
    "🛝 こうえん で あそぼう": "You are a friendly child playing at the park.",
    "🧸 おもちゃやさん で おかいもの": "You are a staff at a toy store asking what toy the child wants.",
    "🍦 アイスクリームやさん": "You are an ice cream shop staff asking for flavors.",
    "🛒 スーパーマーケット で おつかい": "You are a cashier at a supermarket.",
    "🏥 びょういん の おしゃべり": "You are a friendly doctor asking how the child is doing.",
    "🏫 がっこう・ようちえん で ごあいさつ": "You are a teacher at a school greeting the child.",
    "🚀 うちゅうりょこう へ しゅっぱつ": "You are a friendly alien meeting the child in space.",
    "✍️ パパ・ママが じゆうに 決める": "custom"
}

# ==========================================
# ⚙️ サイドバー（おうちのひと専用メニュー）
# ==========================================
with st.sidebar:
    st.header("🔒 おうちのひとへ")
    st.write("※あそぶときは、このメニューをとじてね！")
    st.markdown("---")
    
    st.markdown("### 👀 えいごの みえかた")
    st.session_state.kids_display_mode = st.radio(
        "表示モード", 
        ["🗣️ カタカナも", "🇯🇵 にほんごも", "🔤 えいごだけ"], 
        index=["🗣️ カタカナも", "🇯🇵 にほんごも", "🔤 えいごだけ"].index(st.session_state.kids_display_mode),
        label_visibility="collapsed"
    )
    st.markdown("---")

    st.markdown("### ✨ あたらしく あそぶ")
    child_name = st.text_input("👦👧 おなまえ", value=st.session_state.child_name)
    selected_sit_label = st.selectbox("🎬 おはなし", list(sit_options.keys()))
    if sit_options[selected_sit_label] == "custom":
        custom_sit = st.text_input("じゆうにゅうりょく", "例: 魔法の国で妖精とお話しする")
        final_sit_new = custom_sit
    else:
        final_sit_new = sit_options[selected_sit_label]

    if st.button("🚀 はじめる！", type="primary", use_container_width=True):
        st.session_state.child_name = child_name
        st.session_state.final_sit = final_sit_new
        st.session_state.kids_stamps = 0
        st.session_state.kids_total_stamps = 0
        st.session_state.kids_level = 1
        st.session_state.last_audio_hash = None
        st.session_state.kids_feedback = ""
        st.session_state.pending_levelup = False
        st.session_state.kids_history_log = [] 
        st.session_state.kids_state = "playing"
        
        kids_instruction = f"""
        あなたは日本の子供に英語を教える優しい先生です。シチュエーション: {st.session_state.final_sit}、子供の名前: {st.session_state.child_name}
        【厳守フォーマット】XMLタグのみ。
        <ai_en>（あなたが子供に投げかける英語の質問。1文のみ）</ai_en>
        <ai_ja>（上の英語の【日本語の意味】をひらがなで）</ai_ja>
        <ai_ruby>（上の英語に「Word(カタカナ)」でルビを振ったもの）</ai_ruby>
        <hint_en>（子供が真似して答えるための英語の答え）</hint_en>
        <hint_ja>（上の答えの【日本語の意味】をひらがなで）</hint_ja>
        <hint_ruby>（上の答えのルビ付き）</hint_ruby>
        """
        with st.spinner("じゅんびちゅう..."):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=kids_instruction)
                st.session_state.kids_chat = model.start_chat(history=[])
                hint_rule = get_hint_length_rule(st.session_state.kids_level)
                res = st.session_state.kids_chat.send_message(f"ゲームスタート。レベル1の超簡単な質問をしてください。\n子供の答えのヒント（<hint_en>）は【{hint_rule}】で作成してください。")
                st.session_state.kids_data = {
                    "ai_en": extract_tag(res.text, "ai_en"), "ai_ja": extract_tag(res.text, "ai_ja"), "ai_ruby": extract_tag(res.text, "ai_ruby"),
                    "hint_en": extract_tag(res.text, "hint_en"), "hint_ja": extract_tag(res.text, "hint_ja"), "hint_ruby": extract_tag(res.text, "hint_ruby"),
                }
                st.rerun()
            except Exception:
                st.error("エラーがおきました。")

    st.markdown("---")
    st.markdown("### 💾 セーブ ＆ ロード")
    uploaded_save = st.file_uploader("データのよみこみ(.json)", type=["json"])
    if uploaded_save:
        if st.button("📥 データをよみこむ", type="primary", use_container_width=True):
            try:
                save_data = json.load(uploaded_save)
                st.session_state.child_name = save_data.get("child_name", "おともだち")
                st.session_state.final_sit = save_data.get("final_sit", "")
                st.session_state.kids_stamps = save_data.get("kids_stamps", 0)
                st.session_state.kids_total_stamps = save_data.get("kids_total_stamps", 0)
                st.session_state.kids_level = save_data.get("kids_level", 1)
                st.session_state.kids_data = save_data.get("kids_data", {})
                st.session_state.kids_history_log = save_data.get("kids_history_log", [])
                st.session_state.last_audio_hash = None
                st.session_state.kids_feedback = ""
                st.session_state.pending_levelup = False
                history_data = save_data.get("history", [])
                formatted_history = [{"role": msg["role"], "parts": msg["parts"]} for msg in history_data]
                model = genai.GenerativeModel("gemini-2.5-flash")
                st.session_state.kids_chat = model.start_chat(history=formatted_history)
                st.session_state.kids_state = "playing"
                st.success("よみこみ完了！")
                st.rerun()
            except Exception:
                st.error("エラーがおきました。")
                
    if st.session_state.kids_state in ["playing", "finished"]:
        history_to_save = [{"role": msg.role, "parts": [p.text for p in msg.parts]} for msg in st.session_state.kids_chat.history] if "kids_chat" in st.session_state else []
        save_data = {
            "child_name": st.session_state.child_name, "final_sit": st.session_state.final_sit,
            "kids_stamps": st.session_state.kids_stamps, "kids_total_stamps": st.session_state.kids_total_stamps,
            "kids_level": st.session_state.kids_level, "kids_data": st.session_state.kids_data, 
            "kids_history_log": st.session_state.kids_history_log, "history": history_to_save
        }
        today_str = datetime.now().strftime("%Y-%m-%d")
        st.download_button("💾 データをセーブ", data=json.dumps(save_data, ensure_ascii=False, indent=2), file_name=f"{today_str}_kids_save.json", mime="application/json", use_container_width=True)

# ==========================================
# 🌟 メイン画面（セットアップ待ち）
# ==========================================
if st.session_state.kids_state == "setup":
    st.info("👈 ひだりの メニュー（＞ボタン）をひらいて、あたらしく おはなし を はじめてね！")
    st.stop()

# ==========================================
# 🏆 終了画面（今日のまとめ）
# ==========================================
if st.session_state.kids_state == "finished":
    st.balloons()
    st.markdown("<h1 style='text-align:center; color:#FF6B6B;'>🎉 きょうの べんきょう は おわり！</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align:center;'>がんばって 【{st.session_state.kids_total_stamps}かい】も えいご を はなしたね！すごーい！✨</h3>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📖 きょう はなした えいご の まとめ")
    
    if not st.session_state.kids_history_log:
        st.write("まだ おはなし していないみたい！")
    else:
        for i, turn in enumerate(st.session_state.kids_history_log):
            with st.container(border=True):
                st.markdown(f"<div class='review-text'>🤖 Q: {apply_ruby_html(turn['q_ruby'])}</div>", unsafe_allow_html=True)
                st.caption(f"🇯🇵 {turn['q_ja']}")
                st.markdown(f"<div class='review-text' style='color:#1E90FF;'>🗣️ A: {apply_ruby_html(turn['a_ruby'])}</div>", unsafe_allow_html=True)
                st.caption(f"🇯🇵 {turn['a_ja']}")
    
    st.write("")
    if st.button("🏠 はじめから あそぶ", type="primary", use_container_width=True):
        st.session_state.kids_state = "setup"
        st.rerun()
    st.stop()

# ==========================================
# 🎁 レベルアップポップアップ画面
# ==========================================
if st.session_state.get("pending_levelup"):
    st.balloons()
    with st.container():
        st.markdown("<div class='levelup-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; color: #FF6B6B;'>🎉 よく がんばったね！</h2>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align:center;'>ほしが ５つ あつまったよ！</h4>", unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.markdown("<h3 style='text-align:left;'>📖 いま やった おはなし の ふくしゅう</h3>", unsafe_allow_html=True)
        
        recent_history = st.session_state.kids_history_log[-5:] if len(st.session_state.kids_history_log) >= 5 else st.session_state.kids_history_log
        
        col_tog, col_play = st.columns([1, 1], vertical_alignment="center")
        with col_tog:
            show_translation = st.toggle("🇯🇵 にほんごの やく を みる", value=True)
        with col_play:
            if st.button("🔊 ぜんぶ とおして きく", use_container_width=True):
                with st.spinner("おんせいを つくっているよ..."):
                    try:
                        full_text = "".join([f"{item['q_en']} {item['a_en']}. " for item in recent_history])
                        audio_bytes_all = get_tts_audio(clean_text_for_tts(full_text))
                        st.audio(audio_bytes_all, format="audio/mp3", autoplay=True)
                    except Exception:
                        pass
        
        st.write("")
        for i, turn in enumerate(recent_history):
            st.markdown(f"<div class='review-text'>**Q{i+1}:** {apply_ruby_html(turn['q_ruby'])}</div>", unsafe_allow_html=True)
            if show_translation: st.caption(f"🇯🇵 {turn['q_ja']}")
            st.markdown(f"<div class='review-text' style='color:#1E90FF;'>**A{i+1}:** {apply_ruby_html(turn['a_ruby'])}</div>", unsafe_allow_html=True)
            if show_translation: st.caption(f"🇯🇵 {turn['a_ja']}")
            st.markdown("<hr>", unsafe_allow_html=True)

        st.markdown("<h3 style='text-align:center;'>つぎは どうする？</h3>", unsafe_allow_html=True)
        col_up, col_same = st.columns(2)
        with col_up:
            if st.button("⬆️ つぎの レベルに いく！", use_container_width=True):
                with st.spinner("じゅんびちゅう..."):
                    st.session_state.kids_level += 1
                    st.session_state.pending_levelup = False
                    st.session_state.kids_stamps = 0 
                    hint_rule = get_hint_length_rule(st.session_state.kids_level)
                    prompt_msg = f"子供は「{st.session_state.last_user_spoken}」と言いました。\n【重要】レベルが{st.session_state.kids_level}に上がりました。さっきより少しだけ難しい質問をして、場面を次に進めてください。\n子供のヒントは【{hint_rule}】で。"
                    next_res = st.session_state.kids_chat.send_message(prompt_msg)
                    st.session_state.kids_data = {
                        "ai_en": extract_tag(next_res.text, "ai_en"), "ai_ja": extract_tag(next_res.text, "ai_ja"), "ai_ruby": extract_tag(next_res.text, "ai_ruby"),
                        "hint_en": extract_tag(next_res.text, "hint_en"), "hint_ja": extract_tag(next_res.text, "hint_ja"), "hint_ruby": extract_tag(next_res.text, "hint_ruby"),
                    }
                    st.rerun()
        with col_same:
            if st.button("🔄 おなじ レベルを もういっかい！", use_container_width=True):
                with st.spinner("じゅんびちゅう..."):
                    st.session_state.pending_levelup = False
                    st.session_state.kids_stamps = 0 
                    hint_rule = get_hint_length_rule(st.session_state.kids_level)
                    prompt_msg = f"子供は「{st.session_state.last_user_spoken}」と言いました。\n【重要】レベルは維持します。絶対に直近と同じ質問や回答パターンにならないよう、物語を進行させてください。\n子供のヒントは【{hint_rule}】で。"
                    next_res = st.session_state.kids_chat.send_message(prompt_msg)
                    st.session_state.kids_data = {
                        "ai_en": extract_tag(next_res.text, "ai_en"), "ai_ja": extract_tag(next_res.text, "ai_ja"), "ai_ruby": extract_tag(next_res.text, "ai_ruby"),
                        "hint_en": extract_tag(next_res.text, "hint_en"), "hint_ja": extract_tag(next_res.text, "hint_ja"), "hint_ruby": extract_tag(next_res.text, "hint_ruby"),
                    }
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 🎮 レッスン（あそぶ）エリア
# ==========================================
data = st.session_state.kids_data
mode = st.session_state.kids_display_mode

st.markdown(f"<h4 style='text-align: left; color: #FF4500; margin-top:0;'>🚩 レベル: {st.session_state.kids_level} ｜ 👑 ほし: {'⭐' * st.session_state.kids_stamps}</h4>", unsafe_allow_html=True)

with st.container(border=True):
    col_q_title, col_q_audio = st.columns([1.5, 1], vertical_alignment="center")
    with col_q_title: st.write("🤖 **えいご の しつもん**")
    with col_q_audio:
        try:
            audio_bytes = get_tts_audio(clean_text_for_tts(data["ai_en"]))
            st.audio(audio_bytes, format="audio/mp3", autoplay=True)
        except Exception: pass

    if mode == "🗣️ カタカナも":
        st.markdown(f'<div class="english-text-container">{apply_ruby_html(data["ai_ruby"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ja-text">🇯🇵 {data["ai_ja"]}</div>', unsafe_allow_html=True)
    elif mode == "🇯🇵 にほんごも":
        st.markdown(f'<div class="english-text-container">{data["ai_en"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ja-text">🇯🇵 {data["ai_ja"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="english-text-container">{data["ai_en"]}</div>', unsafe_allow_html=True)

    st.markdown("<hr style='border-top: 2px dashed #FFD700;'>", unsafe_allow_html=True)

    st.write("💡 **こうやって こたえてみよう！**")
    if mode == "🗣️ カタカナも":
        st.markdown(f'<div class="english-text-container">{apply_ruby_html(data["hint_ruby"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ja-text">🇯🇵 {data["hint_ja"]}</div>', unsafe_allow_html=True)
    elif mode == "🇯🇵 にほんごも":
        st.markdown(f'<div class="english-text-container">{data["hint_en"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ja-text">🇯🇵 {data["hint_ja"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="english-text-container">{data["hint_en"]}</div>', unsafe_allow_html=True)

# ==========================================
# 🎤 操作パネル
# ==========================================
st.write("🎤 **マイクを おして えいご を いってみてね！**")
col_play_hint, col_mic = st.columns([1, 2], vertical_alignment="bottom")

with col_play_hint:
    if st.button("🔊 おてほん\nを きく", key="btn_hint_audio", use_container_width=True):
        try:
            audio_bytes_h = get_tts_audio(clean_text_for_tts(data["hint_en"]))
            st.audio(audio_bytes_h, format="audio/mp3", autoplay=True)
        except Exception: pass

with col_mic:
    kids_audio = st.audio_input("マイク", key=f"kids_mic_{st.session_state.kids_stamps}", label_visibility="collapsed")
    
if kids_audio:
    current_audio_hash = hash(kids_audio.getvalue())
    if st.session_state.last_audio_hash != current_audio_hash:
        st.audio(kids_audio.getvalue(), format="audio/wav", autoplay=True)
        st.session_state.last_audio_hash = current_audio_hash
        st.session_state.kids_feedback = "" 
        
    if st.session_state.kids_feedback:
        st.info(st.session_state.kids_feedback)

# ==========================================
# 🔘 アクションボタン
# ==========================================
col_b1, col_b2, col_b3, col_b4 = st.columns(4)

with col_b1:
    if st.button("🤖 はつおん\nチェック", use_container_width=True):
        if kids_audio:
            with st.spinner("判定中..."):
                user_spoken = get_transcription(kids_audio.getvalue()) # 無駄①の解消：キャッシュから取得
                judge_prompt = f"お手本:「{data['hint_en']}」\n子供の発音:「{user_spoken}」\n【絶対ルール】相手は6歳の子供。記号や大文字小文字の違いは絶対無視して、英単語が完全一致か判定。完全一致：「パーフェクト！すごい！」不一致：褒めずに「おしい！『〇〇』っていってみてね！」と優しくひらがなで。"
                judge_model = genai.GenerativeModel("gemini-2.5-flash")
                judge_res = judge_model.generate_content(judge_prompt)
                st.session_state.kids_feedback = f"🎤 きみ: **{user_spoken}**\n\n🌟 AI: **{judge_res.text.strip()}**"
                st.rerun()
        else:
            st.warning("マイクでおはなししてね！")

with col_b2:
    if st.button("🌟 つぎへ\nすすむ！", type="primary", use_container_width=True):
        if kids_audio:
            with st.spinner("じゅんびちゅう..."):
                user_spoken = get_transcription(kids_audio.getvalue()) # 無駄①の解消：キャッシュから取得
                
                turn_data = {
                    "q_en": data["ai_en"], "q_ja": data["ai_ja"], "q_ruby": data["ai_ruby"],
                    "a_en": data["hint_en"], "a_ja": data["hint_ja"], "a_ruby": data["hint_ruby"]
                }
                st.session_state.kids_history_log.append(turn_data)
                
                st.session_state.kids_stamps += 1
                st.session_state.kids_total_stamps += 1 
                st.session_state.kids_feedback = ""
                st.session_state.last_audio_hash = None
                
                # 【無駄④の解消】過去の不要な会話履歴をカットして軽くする
                if len(st.session_state.kids_chat.history) > 6:
                    kids_instruction = f"あなたは日本の子供に英語を教える優しい先生です。シチュエーション: {st.session_state.final_sit}、子供の名前: {st.session_state.child_name}\n【厳守フォーマット】XMLタグのみ。\n<ai_en>（英語の質問。1文のみ）</ai_en><ai_ja>（日本語の意味）</ai_ja><ai_ruby>（ルビ）</ai_ruby>\n<hint_en>（英語の答え）</hint_en><hint_ja>（日本語の意味）</hint_ja><hint_ruby>（ルビ）</hint_ruby>"
                    trimmed_history = st.session_state.kids_chat.history[-6:]
                    model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=kids_instruction)
                    st.session_state.kids_chat = model.start_chat(history=trimmed_history)

                if st.session_state.kids_stamps > 0 and st.session_state.kids_stamps % 5 == 0:
                    st.session_state.pending_levelup = True
                    st.session_state.last_user_spoken = user_spoken
                    st.rerun()
                else:
                    hint_rule = get_hint_length_rule(st.session_state.kids_level)
                    prompt_msg = f"子供は「{user_spoken}」と言いました。\n【重要】次の展開の質問を出してください。絶対に直近と同じ質問や回答パターンにならないよう、物語を進行させてください。\n子供のヒント（<hint_en>）は【{hint_rule}】で。"
                    next_res = st.session_state.kids_chat.send_message(prompt_msg)
                    st.session_state.kids_data = {
                        "ai_en": extract_tag(next_res.text, "ai_en"), "ai_ja": extract_tag(next_res.text, "ai_ja"), "ai_ruby": extract_tag(next_res.text, "ai_ruby"),
                        "hint_en": extract_tag(next_res.text, "hint_en"), "hint_ja": extract_tag(next_res.text, "hint_ja"), "hint_ruby": extract_tag(next_res.text, "hint_ruby"),
                    }
                    st.rerun()
        else:
            st.warning("マイクでおはなししてね！")

with col_b3:
    if st.button("⏭️ とばす\n(つぎへ)", use_container_width=True):
        with st.spinner("じゅんびちゅう..."):
            st.session_state.kids_feedback = ""
            st.session_state.last_audio_hash = None
            hint_rule = get_hint_length_rule(st.session_state.kids_level)
            next_res = st.session_state.kids_chat.send_message(f"子供がパスしました。優しく励まして、さっきとは違う展開の質問をしてください。\n子供のヒントは【{hint_rule}】で。")
            st.session_state.kids_data = {
                "ai_en": extract_tag(next_res.text, "ai_en"), "ai_ja": extract_tag(next_res.text, "ai_ja"), "ai_ruby": extract_tag(next_res.text, "ai_ruby"),
                "hint_en": extract_tag(next_res.text, "hint_en"), "hint_ja": extract_tag(next_res.text, "hint_ja"), "hint_ruby": extract_tag(next_res.text, "hint_ruby"),
            }
            st.rerun()

with col_b4:
    if st.button("📉 レベルを\nさげる", use_container_width=True):
        if st.session_state.kids_level > 1:
            st.session_state.kids_level -= 1
            with st.spinner("じゅんびちゅう..."):
                st.session_state.kids_feedback = ""
                st.session_state.last_audio_hash = None
                hint_rule = get_hint_length_rule(st.session_state.kids_level)
                next_res = st.session_state.kids_chat.send_message(f"レベルを{st.session_state.kids_level}に下げました。簡単な文にして優しく励ましてください。\n子供のヒントは【{hint_rule}】で。")
                st.session_state.kids_data = {
                    "ai_en": extract_tag(next_res.text, "ai_en"), "ai_ja": extract_tag(next_res.text, "ai_ja"), "ai_ruby": extract_tag(next_res.text, "ai_ruby"),
                    "hint_en": extract_tag(next_res.text, "hint_en"), "hint_ja": extract_tag(next_res.text, "hint_ja"), "hint_ruby": extract_tag(next_res.text, "hint_ruby"),
                }
                st.rerun()
        else:
            st.warning("これいじょう さげられないよ！")

# ==========================================
# 🎒 メインエリア下部
# ==========================================
st.write("")
with st.expander("🎒 べつの おはなし に かえる（レベルは そのまま）"):
    change_sit_label = st.selectbox("あたらしい おはなし を えらんでね", list(sit_options.keys()), key="change_sit_sb")
    if sit_options[change_sit_label] == "custom":
        change_custom_sit = st.text_input("じゆうにゅうりょく", "例: まほうのくに", key="change_sit_custom")
        change_final_sit = change_custom_sit
    else:
        change_final_sit = sit_options[change_sit_label]
        
    if st.button("🚀 このおはなしに かえる！", use_container_width=True):
        st.session_state.final_sit = change_final_sit
        st.session_state.kids_feedback = ""
        st.session_state.last_audio_hash = None
        kids_instruction = f"あなたは、日本の子供に英語を教える優しい先生です。シチュエーション: {st.session_state.final_sit}、子供の名前: {st.session_state.child_name}\n【厳守フォーマット】XMLタグのみ。\n<ai_en>（英語の質問。1文のみ）</ai_en><ai_ja>（日本語の意味）</ai_ja><ai_ruby>（ルビ）</ai_ruby>\n<hint_en>（英語の答え）</hint_en><hint_ja>（日本語の意味）</hint_ja><hint_ruby>（ルビ）</hint_ruby>"
        with st.spinner("じゅんびちゅう..."):
            model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=kids_instruction)
            st.session_state.kids_chat = model.start_chat(history=[])
            hint_rule = get_hint_length_rule(st.session_state.kids_level)
            res = st.session_state.kids_chat.send_message(f"シチュエーションが変わりました。レベル{st.session_state.kids_level}の質問をしてください。\n子供の答えのヒント（<hint_en>）は【{hint_rule}】で作成。")
            st.session_state.kids_data = {
                "ai_en": extract_tag(res.text, "ai_en"), "ai_ja": extract_tag(res.text, "ai_ja"), "ai_ruby": extract_tag(res.text, "ai_ruby"),
                "hint_en": extract_tag(res.text, "hint_en"), "hint_ja": extract_tag(res.text, "hint_ja"), "hint_ruby": extract_tag(res.text, "hint_ruby"),
            }
            st.rerun()

st.markdown("---")
if st.button("🛑 きょうの べんきょう を おわる", type="secondary", use_container_width=True):
    st.session_state.kids_state = "finished"
    st.rerun()
