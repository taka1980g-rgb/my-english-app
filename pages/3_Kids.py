import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import io
import re
import json
from datetime import datetime

# === 🎨 キッズ専用・でか文字＆紙芝居デザイン ===
st.markdown("""
    <style>
    /* 全体のフォント設定 */
    html, body, [class*="css"] {
        font-family: 'Hiragino Maru Gothic ProN', 'Comic Sans MS', sans-serif !important;
    }
    /* 紙芝居風の固定枠デザイン */
    .kamishibai-box {
        background-color: #FFFFE0;
        border: 6px solid #FFD700;
        border-radius: 30px;
        padding: 30px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .hint-box {
        background-color: #E0FFFF;
        border: 4px dashed #4ECDC4;
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
    }
    /* ふりがな（ルビ）のでか文字化 */
    ruby { font-size: 38px !important; font-weight: bold; color: #1E90FF; }
    rt { font-size: 16px !important; color: #FF4500; font-weight: bold; }
    
    /* 日本語訳のでか文字化 */
    .ja-text { font-size: 24px !important; color: #666; font-weight: bold; margin-top: 10px;}
    
    /* ボタンを押しやすく密集させる */
    div.stButton > button {
        border-radius: 20px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        padding: 15px !important;
        height: auto !important;
        border: 3px solid #FFF !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
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

# === 🧹 便利ツール ===
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

st.title("🌟 キッズえいご レッスン 🌟")

# === 💾 データの初期化 ===
if "kids_state" not in st.session_state:
    st.session_state.kids_state = "setup" # setup -> playing
if "kids_stamps" not in st.session_state:
    st.session_state.kids_stamps = 0
if "kids_level" not in st.session_state:
    st.session_state.kids_level = 1
if "kids_data" not in st.session_state:
    st.session_state.kids_data = {}
if "child_name" not in st.session_state:
    st.session_state.child_name = "おともだち"
if "final_sit" not in st.session_state:
    st.session_state.final_sit = ""

# ★追加：自動再生とフィードバック制御用のステート
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None
if "kids_feedback" not in st.session_state:
    st.session_state.kids_feedback = ""

# ==========================================
# ⚙️ おうちのひと用 設定＆セーブ・ロード
# ==========================================
with st.expander("🔒 おうちのひとへ（せってい ＆ セーブ・ロード）", expanded=(st.session_state.kids_state == "setup")):
    
    st.markdown("### 📁 つづきから あそぶ（ロード）")
    uploaded_save = st.file_uploader("保存したファイル（.json）を選んでください", type=["json"])
    if uploaded_save:
        if st.button("📥 データをよみこむ", type="primary"):
            try:
                save_data = json.load(uploaded_save)
                st.session_state.child_name = save_data.get("child_name", "おともだち")
                st.session_state.final_sit = save_data.get("final_sit", "")
                st.session_state.kids_stamps = save_data.get("kids_stamps", 0)
                st.session_state.kids_level = save_data.get("kids_level", 1)
                st.session_state.kids_data = save_data.get("kids_data", {})
                st.session_state.last_audio_hash = None
                st.session_state.kids_feedback = ""
                
                history_data = save_data.get("history", [])
                formatted_history = []
                for msg in history_data:
                    formatted_history.append({"role": msg["role"], "parts": msg["parts"]})
                
                model = genai.GenerativeModel("gemini-2.5-flash")
                st.session_state.kids_chat = model.start_chat(history=formatted_history)
                st.session_state.kids_state = "playing"
                st.success("データの読み込みが完了しました！下へ進んでください。")
                st.rerun()
            except Exception as e:
                st.error("ファイルの読み込みに失敗しました。")

    st.markdown("---")
    st.markdown("### ✨ あたらしく あそぶ")
    child_name = st.text_input("👦👧 おこさまの おなまえ（ひらがな・カタカナ）", value=st.session_state.child_name)
    
    sit_options = {
        "🍔 ハンバーガーやさん で おかいもの": "You are a friendly staff at a hamburger shop.",
        "🐶 どうぶつえん で ごあいさつ": "You are a friendly zookeeper showing animals.",
        "🍎 すきな フルーツを えらぼう": "You are a fruit shop owner asking what fruits the child likes.",
        "🛝 こうえん で あそぼう": "You are a friendly child playing at the park.",
        "✍️ パパ・ママが じゆうに 決める": "custom"
    }
    selected_sit_label = st.selectbox("🎬 おはなし（シチュエーション）", list(sit_options.keys()))
    
    if sit_options[selected_sit_label] == "custom":
        custom_sit = st.text_input("シチュエーションを英語または日本語で入力", "例: 魔法の国で妖精とお話しする")
        final_sit = custom_sit
    else:
        final_sit = sit_options[selected_sit_label]

    display_mode = st.radio("👀 えいごの みえかた", ["🗣️ カタカナも（おすすめ！）", "🇯🇵 にほんごも", "🔤 えいごだけ"], horizontal=True)

    if st.button("🚀 この おはなし で あたらしく はじめる！", type="primary"):
        st.session_state.child_name = child_name
        st.session_state.final_sit = final_sit
        st.session_state.kids_stamps = 0
        st.session_state.kids_level = 1
        st.session_state.last_audio_hash = None
        st.session_state.kids_feedback = ""
        st.session_state.kids_state = "playing"
        
        kids_instruction = f"""
        あなたは、日本の子供に英語を教える、超絶優しくて明るい英語の先生です。
        シチュエーション: {st.session_state.final_sit}
        子供の名前: {st.session_state.child_name}

        【厳守する出力フォーマット】必ずXMLタグのみで出力。
        <praise>（子供をひらがなで大げさに褒める言葉）</praise>
        <ai_en>（あなたが子供に投げかける英語の質問。1文のみ）</ai_en>
        <ai_ja>（上の英語のひらがな訳）</ai_ja>
        <ai_ruby>（上の英語に「Word(カタカナ)」でルビを振ったもの。例: What(ホワット) is(イズ) it?(イット)）</ai_ruby>
        <hint_en>（子供が真似して答えるための英語の答え。1文のみ）</hint_en>
        <hint_ja>（上の答えのひらがな訳）</hint_ja>
        <hint_ruby>（上の答えのルビ付き。例: I(アイ) like(ライク) apples.(アップルズ)）</hint_ruby>
        """
        
        with st.spinner("おはなし の じゅんび を しているよ..."):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=kids_instruction)
                st.session_state.kids_chat = model.start_chat(history=[])
                res = st.session_state.kids_chat.send_message(f"ゲームスタート。レベル1の超簡単な質問をしてください。")
                
                st.session_state.kids_data = {
                    "praise": extract_tag(res.text, "praise"),
                    "ai_en": extract_tag(res.text, "ai_en"),
                    "ai_ja": extract_tag(res.text, "ai_ja"),
                    "ai_ruby": extract_tag(res.text, "ai_ruby"),
                    "hint_en": extract_tag(res.text, "hint_en"),
                    "hint_ja": extract_tag(res.text, "hint_ja"),
                    "hint_ruby": extract_tag(res.text, "hint_ruby"),
                }
                st.rerun()
            except Exception as e:
                st.error("エラーが おきたよ。もういちど おしてね！")

    if st.session_state.kids_state == "playing":
        st.markdown("---")
        st.markdown("### 💾 いまの データをセーブする")
        
        history_to_save = []
        if "kids_chat" in st.session_state:
            for msg in st.session_state.kids_chat.history:
                history_to_save.append({"role": msg.role, "parts": [p.text for p in msg.parts]})
                
        save_data = {
            "child_name": st.session_state.child_name,
            "final_sit": st.session_state.final_sit,
            "kids_stamps": st.session_state.kids_stamps,
            "kids_level": st.session_state.kids_level,
            "kids_data": st.session_state.kids_data,
            "history": history_to_save
        }
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        st.download_button(
            "💾 このデータをパソコンに保存する（.json）",
            data=json.dumps(save_data, ensure_ascii=False, indent=2),
            file_name=f"{today_str}_kids_save.json",
            mime="application/json",
            use_container_width=True
        )

# ==========================================
# 🎮 レッスン（あそぶ）エリア【紙芝居方式】
# ==========================================
if st.session_state.kids_state == "playing" and st.session_state.kids_data:
    data = st.session_state.kids_data
    
    col_level, col_stamp = st.columns([1, 2])
    with col_level:
        st.markdown(f"### 🚩 レベル: {st.session_state.kids_level}")
    with col_stamp:
        st.markdown(f"### 👑 ほし: {'⭐' * st.session_state.kids_stamps}")
        
    if data["praise"]:
        st.success(f"🎉 **{data['praise']}**")
        
    st.markdown('<div class="kamishibai-box">', unsafe_allow_html=True)
    st.write("🤖 **えいご の しつもん**")
    
    if display_mode == "🗣️ カタカナも（おすすめ！）":
        st.markdown(apply_ruby_html(data["ai_ruby"]), unsafe_allow_html=True)
        st.markdown(f'<div class="ja-text">🇯🇵 {data["ai_ja"]}</div>', unsafe_allow_html=True)
    elif display_mode == "🇯🇵 にほんごも":
        st.markdown(f"<h2>{data['ai_en']}</h2>", unsafe_allow_html=True)
        st.markdown(f'<div class="ja-text">🇯🇵 {data["ai_ja"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"<h2>{data['ai_en']}</h2>", unsafe_allow_html=True)
        
    speak_text = clean_text_for_tts(data["ai_en"])
    try:
        tts = gTTS(text=speak_text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format="audio/mp3", autoplay=True)
    except Exception:
        pass
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="hint-box">', unsafe_allow_html=True)
    st.write("💡 **こうやって こたえてみよう！**")
    if display_mode == "🗣️ カタカナも（おすすめ！）":
        st.markdown(apply_ruby_html(data["hint_ruby"]), unsafe_allow_html=True)
        st.markdown(f'<div class="ja-text">🇯🇵 {data["hint_ja"]}</div>', unsafe_allow_html=True)
    elif display_mode == "🇯🇵 にほんごも":
        st.markdown(f"<h2>{data['hint_en']}</h2>", unsafe_allow_html=True)
        st.markdown(f'<div class="ja-text">🇯🇵 {data["hint_ja"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"<h2>{data['hint_en']}</h2>", unsafe_allow_html=True)
        
    if st.button("🔊 おてほん を きく", key="btn_hint_audio", use_container_width=True):
        speak_text_hint = clean_text_for_tts(data["hint_en"])
        try:
            tts_h = gTTS(text=speak_text_hint, lang='en')
            fp_h = io.BytesIO()
            tts_h.write_to_fp(fp_h)
            fp_h.seek(0)
            st.audio(fp_h, format="audio/mp3", autoplay=True)
        except Exception:
            pass
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ==========================================
    # 🎤 操作パネル（マイクと各種ボタン）
    # ==========================================
    st.write("🎤 **マイクを おして えいご を いってみてね！**")
    kids_audio = st.audio_input("えいご で はなす", key=f"kids_mic_{st.session_state.kids_stamps}")
    
    # 録音された場合のアクション
    if kids_audio:
        audio_bytes = kids_audio.getvalue()
        current_audio_hash = hash(audio_bytes)
        
        # ★魔法の自動再生機能（新しい録音のときだけ再生する）
        if st.session_state.last_audio_hash != current_audio_hash:
            st.audio(audio_bytes, format="audio/wav", autoplay=True)
            st.session_state.last_audio_hash = current_audio_hash
            st.session_state.kids_feedback = "" # 新しい録音ならフィードバックを消す
            
        if st.session_state.kids_feedback:
            st.info(st.session_state.kids_feedback)
            
        col_ai, col_next = st.columns(2)
        with col_ai:
            if st.button("🤖 AIに はつおんチェックをたのむ\n(やらなくてもOK!)", use_container_width=True):
                with st.spinner("AIが きいているよ..."):
                    try:
                        transcriber = genai.GenerativeModel("gemini-2.5-flash-lite")
                        res = transcriber.generate_content([{"mime_type": "audio/wav", "data": audio_bytes}, "英語を文字起こししてください。文字のみ出力。"])
                        user_spoken = res.text.strip() if res.parts else "（がんばって こえ を だしたよ！）"
                        
                        judge_prompt = f"""
                        お手本:「{data['hint_en']}」
                        子供の発音:「{user_spoken}」
                        【絶対ルール】
                        相手は英語を始めたばかりの6歳の子供です。
                        発音が間違っていても、単語が抜けていても絶対に指摘せず、「〇〇っていえたね！えらい！」と全力で肯定して褒めてください。
                        完璧なら「パーフェクト！」と褒めてください。
                        出力はひらがなとカタカナのみ、1〜2文でお願いします。
                        """
                        judge_model = genai.GenerativeModel("gemini-2.5-flash-lite")
                        judge_res = judge_model.generate_content(judge_prompt)
                        st.session_state.kids_feedback = f"🎤 きみのこえ: **{user_spoken}**\n\n🌟 AIせんせい: **{judge_res.text.strip()}**"
                        st.rerun()
                    except Exception:
                        st.error("うまく ききとれなかったみたい。")
                        
        with col_next:
            if st.button("🌟 ばっちり！\nつぎへ いく！", type="primary", use_container_width=True):
                with st.spinner("つぎの おはなし を よういしているよ..."):
                    try:
                        # どんな音声でもとりあえず文字起こしして次に繋げる
                        transcriber = genai.GenerativeModel("gemini-2.5-flash-lite")
                        res = transcriber.generate_content([{"mime_type": "audio/wav", "data": audio_bytes}, "英語を文字起こししてください。"])
                        user_spoken = res.text.strip() if res.parts else "（がんばってこえをだしたよ！）"
                        
                        st.session_state.kids_stamps += 1
                        st.session_state.kids_feedback = ""
                        st.session_state.last_audio_hash = None
                        
                        is_levelup = False
                        if st.session_state.kids_stamps > 0 and st.session_state.kids_stamps % 5 == 0:
                            st.session_state.kids_level += 1
                            is_levelup = True
                            st.balloons()
                        
                        prompt_msg = f"子供は「{user_spoken}」と言いました。\n"
                        if is_levelup:
                            prompt_msg += f"【重要】星が5個集まり、レベル{st.session_state.kids_level}に上がりました！大げさに褒めちぎり、さっきより少しだけ難しい（使う単語が多い）質問をして、場面を次に進めてください。"
                        else:
                            prompt_msg += f"【重要】めちゃくちゃ褒めて、次の展開の質問を出してください。絶対に直近と同じ質問や回答パターン（Yes, please等）にならないよう、物語を進行させてください。"

                        next_res = st.session_state.kids_chat.send_message(prompt_msg)
                        
                        st.session_state.kids_data = {
                            "praise": extract_tag(next_res.text, "praise"),
                            "ai_en": extract_tag(next_res.text, "ai_en"),
                            "ai_ja": extract_tag(next_res.text, "ai_ja"),
                            "ai_ruby": extract_tag(next_res.text, "ai_ruby"),
                            "hint_en": extract_tag(next_res.text, "hint_en"),
                            "hint_ja": extract_tag(next_res.text, "hint_ja"),
                            "hint_ruby": extract_tag(next_res.text, "hint_ruby"),
                        }
                        st.rerun()
                    except Exception:
                        st.error("エラーがおきたよ。もういっかい おしてみて！")

    st.write("") 
    
    # 録音前でも後でも使える 救済ボタン群
    col_skip, col_down = st.columns(2)
    with col_skip:
        if st.button("⏭️ むずかしい から とばす", use_container_width=True):
            with st.spinner("べつの おはなし を しているよ..."):
                try:
                    st.session_state.kids_feedback = ""
                    st.session_state.last_audio_hash = None
                    next_res = st.session_state.kids_chat.send_message("子供が難しがってパスしました。「だいじょうぶだよ！」と優しく励まして、さっきとは違う展開の質問をしてください。")
                    st.session_state.kids_data = {
                        "praise": extract_tag(next_res.text, "praise"),
                        "ai_en": extract_tag(next_res.text, "ai_en"),
                        "ai_ja": extract_tag(next_res.text, "ai_ja"),
                        "ai_ruby": extract_tag(next_res.text, "ai_ruby"),
                        "hint_en": extract_tag(next_res.text, "hint_en"),
                        "hint_ja": extract_tag(next_res.text, "hint_ja"),
                        "hint_ruby": extract_tag(next_res.text, "hint_ruby"),
                    }
                    st.rerun()
                except Exception:
                    st.error("エラーが おきたよ。")

    with col_down:
        if st.button("🔄 レベルを さげる", use_container_width=True):
            if st.session_state.kids_level > 1:
                st.session_state.kids_level -= 1
                with st.spinner("かんたんな おはなし に しているよ..."):
                    try:
                        st.session_state.kids_feedback = ""
                        st.session_state.last_audio_hash = None
                        next_res = st.session_state.kids_chat.send_message(f"子供が難しがったため、レベルを{st.session_state.kids_level}に下げました。うんと簡単な短い文にして、優しく励ましてください。")
                        st.session_state.kids_data = {
                            "praise": extract_tag(next_res.text, "praise"),
                            "ai_en": extract_tag(next_res.text, "ai_en"),
                            "ai_ja": extract_tag(next_res.text, "ai_ja"),
                            "ai_ruby": extract_tag(next_res.text, "ai_ruby"),
                            "hint_en": extract_tag(next_res.text, "hint_en"),
                            "hint_ja": extract_tag(next_res.text, "hint_ja"),
                            "hint_ruby": extract_tag(next_res.text, "hint_ruby"),
                        }
                        st.rerun()
                    except Exception:
                        st.error("エラーが おきたよ。")
            else:
                st.warning("これいじょう かんたん に できないよ！「とばす」をおしてみてね。")
