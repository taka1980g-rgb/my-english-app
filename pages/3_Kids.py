
import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import io
import re

# === 🎨 キッズ専用・でか文字ポップデザイン ===
st.markdown("""
    <style>
    /* 全体のフォントを大きく、丸みを帯びたものに */
    html, body, [class*="css"] {
        font-family: 'Hiragino Maru Gothic ProN', 'Comic Sans MS', sans-serif !important;
        font-size: 22px !important;
    }
    h1 { font-size: 36px !important; color: #FF6B6B !important; }
    h2 { font-size: 28px !important; color: #4ECDC4 !important; }
    h3 { font-size: 24px !important; color: #FFA07A !important; }
    
    /* ボタンを大きく、押しやすく */
    .stButton>button {
        border-radius: 20px !important;
        font-size: 24px !important;
        font-weight: bold !important;
        padding: 10px 20px !important;
        border: 4px solid #FFF !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    
    /* ふりがな（ルビ）のデザイン */
    ruby { font-size: 32px; font-weight: bold; color: #1E90FF; }
    rt { font-size: 14px; color: #FF4500; font-weight: bold; }
    
    /* メッセージ枠 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFE0 !important;
        border: 4px dashed #FFD700 !important;
        border-radius: 20px;
        padding: 20px;
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

# 音声用テキストクリーナー
def clean_text_for_tts(text):
    text = re.sub(r'[*_#~]', '', text)
    text = re.sub(r"(?<!\w)['\"]|['\"](?!\w)", '', text)
    return text.strip()

# ルビテキストをHTMLに変換する魔法の関数
# 例: "Apple(アップル)" -> "<ruby>Apple<rt>アップル</rt></ruby>"
def apply_ruby_html(text):
    return re.sub(r'([A-Za-z.,!?\']+)\(([\u30A0-\u30FF\u3040-\u309F]+)\)', r'<ruby>\1<rt>\2</rt></ruby>', text)

# XMLタグ抽出関数
def extract_tag(text, tag):
    pattern = f"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""

st.title("🌟 キッズえいご レッスン 🌟")

# データの初期化
if "kids_stamps" not in st.session_state:
    st.session_state.kids_stamps = 0
if "kids_state" not in st.session_state:
    st.session_state.kids_state = "setup" # setup -> playing
if "kids_data" not in st.session_state:
    st.session_state.kids_data = {}

# ==========================================
# ⚙️ おうちのひと用 設定エリア
# ==========================================
with st.expander("🔒 おうちのひとへ（せってい）", expanded=(st.session_state.kids_state == "setup")):
    st.write("お子様向けのシチュエーションや表示方法を設定してください。")
    child_name = st.text_input("👦👧 おこさまの おなまえ（ひらがな・カタカナ）", value="おともだち")
    
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

    if st.button("🚀 この おはなし で あそぶ！", type="primary"):
        st.session_state.kids_stamps = 0
        st.session_state.kids_state = "playing"
        
        # AIへの絶対ルール（子供向け）
        kids_instruction = f"""
        あなたは、6歳の日本の子供に英語を教える、超絶優しくて明るい英語の先生です。
        以下のシチュエーションでロールプレイを行います。
        シチュエーション: {final_sit}
        子供の名前: {child_name}

        【厳守する出力フォーマット】
        必ず以下のXMLタグを使って出力してください。他の言葉は一切不要です。
        <praise>（子供が発言した場合、ひらがなで大げさに褒める言葉。初回は空でOK）</praise>
        <ai_en>（あなたが子供に投げかける、超簡単な英語の質問。1文のみ）</ai_en>
        <ai_ja>（上の英語のひらがな訳）</ai_ja>
        <ai_ruby>（上の英語に「Word(カタカナ)」の形式でルビを振ったもの。例: What(ホワット) is(イズ) it?(イット)）</ai_ruby>
        <hint_en>（子供がそのまま真似して答えるための、超簡単な英語の答え。1文のみ）</hint_en>
        <hint_ja>（上の答えのひらがな訳）</hint_ja>
        <hint_ruby>（上の答えのルビ付き。例: I(アイ) like(ライク) apples.(アップルズ)）</hint_ruby>
        """
        
        with st.spinner("おはなし の じゅんび を しているよ..."):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=kids_instruction)
                st.session_state.kids_chat = model.start_chat(history=[])
                res = st.session_state.kids_chat.send_message("ゲームをはじめましょう。最初の質問をしてください。")
                
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

# ==========================================
# 🎮 レッスン（あそぶ）エリア
# ==========================================
if st.session_state.kids_state == "playing" and st.session_state.kids_data:
    data = st.session_state.kids_data
    
    # ごほうびスタンプ表示
    st.markdown(f"### 👑 あつめた ほし： {'⭐' * st.session_state.kids_stamps}")
    
    if data["praise"]:
        st.success(f"🎉 **{data['praise']}**")
        
    st.markdown("---")
    
    # 🤖 AIからのしつもん
    st.write("🤖 **えいご の しつもん**")
    with st.container(border=True):
        if display_mode == "🗣️ カタカナも（おすすめ！）":
            st.markdown(apply_ruby_html(data["ai_ruby"]), unsafe_allow_html=True)
            st.caption(f"🇯🇵 {data['ai_ja']}")
        elif display_mode == "🇯🇵 にほんごも":
            st.markdown(f"**{data['ai_en']}**")
            st.caption(f"🇯🇵 {data['ai_ja']}")
        else:
            st.markdown(f"**{data['ai_en']}**")
            
        # しつもんの音声
        speak_text = clean_text_for_tts(data["ai_en"])
        try:
            tts = gTTS(text=speak_text, lang='en')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            st.audio(fp, format="audio/mp3", autoplay=True)
        except Exception:
            pass

    st.write("")
    
    # 💡 こたえのヒント（カンペ）
    st.write("💡 **こうやって こたえてみよう！**")
    with st.container(border=True):
        if display_mode == "🗣️ カタカナも（おすすめ！）":
            st.markdown(apply_ruby_html(data["hint_ruby"]), unsafe_allow_html=True)
            st.caption(f"🇯🇵 {data['hint_ja']}")
        elif display_mode == "🇯🇵 にほんごも":
            st.markdown(f"**{data['hint_en']}**")
            st.caption(f"🇯🇵 {data['hint_ja']}")
        else:
            st.markdown(f"**{data['hint_en']}**")
            
        # ヒントの音声（聞くだけ再生用）
        col_hint_btn, _ = st.columns([1, 1])
        with col_hint_btn:
            if st.button("🔊 おてほん を きく", key="btn_hint_audio"):
                speak_text = clean_text_for_tts(data["hint_en"])
                try:
                    tts = gTTS(text=speak_text, lang='en')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    fp.seek(0)
                    st.audio(fp, format="audio/mp3", autoplay=True)
                except Exception:
                    pass

    st.markdown("---")
    
    # 🎤 マイク入力エリア
    st.write("🎤 **マイクを おして えいご を いってみてね！**")
    kids_audio = st.audio_input("えいご で はなす", key=f"kids_mic_{st.session_state.kids_stamps}")
    
    col_submit, col_skip = st.columns(2)
    
    # 声を出した場合（判定して次へ）
    with col_submit:
        if kids_audio:
            if st.button("🌟 できた！つぎへ いく！", type="primary", use_container_width=True):
                with st.spinner("AIが きいているよ..."):
                    try:
                        # まずは文字起こし（どんな発音でも、とりあえず褒めるための材料にする）
                        transcriber = genai.GenerativeModel("gemini-2.5-flash-lite")
                        res = transcriber.generate_content([{"mime_type": "audio/wav", "data": kids_audio.getvalue()}, "英語を文字起こししてください。"])
                        user_spoken = res.text.strip() if res.parts else "（がんばってこえをだしたよ！）"
                        
                        st.session_state.kids_stamps += 1 # スタンプGET!
                        
                        # AIに送信して次のお話を作ってもらう
                        next_res = st.session_state.kids_chat.send_message(f"子供は「{user_spoken}」と言いました。めちゃくちゃ褒めて、次の展開の質問を1つ出してください。")
                        
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
                        st.error("うまく ききとれなかったみたい。もういっかい やってみてね！")

    # 難しくて飛ばしたい場合
    with col_skip:
        if st.button("⏭️ むずかしい から とばす！", use_container_width=True):
            with st.spinner("べつの おはなし を しているよ..."):
                try:
                    next_res = st.session_state.kids_chat.send_message("子供が難しがってパスしました。「だいじょうぶだよ！」と優しく励まして、さっきとは違う、もっと簡単な質問をしてください。")
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
                    st.error("エラーが おきたよ。パパかママを よんでね！")
