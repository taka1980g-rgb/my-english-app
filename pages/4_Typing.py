import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import json
import re

# === 🎨 デザイン設定（PC横画面最適化） ===
st.set_page_config(layout="wide")

st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        max-width: 1200px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #F0F8FF !important;
        border: 2px solid #87CEFA !important;
        border-radius: 12px;
        padding: 10px;
    }
    .stTextInput { margin-bottom: -10px; }
    </style>
    """, unsafe_allow_html=True)

# === 🚪 パスワードチェック ===
if not st.session_state.get("password_correct", False):
    st.warning("👈 左上の「＞」を押して、ホーム画面から合言葉を入力してください。")
    st.stop()

# === 🔑 API設定 ===
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=MY_API_KEY.strip())
except Exception:
    st.error("⚠️ Secretsに GEMINI_API_KEY を設定してください！")
    st.stop()

st.title("⌨️ えいごタイピングであそぼう！")

# === 💾 状態管理 ===
if "typing_words" not in st.session_state:
    st.session_state.typing_words = []

if "input_rows" not in st.session_state:
    st.session_state.input_rows = [{"en": "", "ja": ""} for _ in range(5)]

# ==========================================
# 1. 問題作成エリア
# ==========================================
with st.expander("📝 もんだいを つくる / えらぶ", expanded=not bool(st.session_state.typing_words)):
    tab1, tab2 = st.tabs(["✨ AIにおまかせ", "✍️ 自分で入力"])
    
    with tab1:
        col_t, col_n = st.columns([2, 1])
        theme = col_t.selectbox("テーマ", ["どうぶつ", "たべもの", "かず", "いろ", "じゆうに入力"])
        word_count = col_n.slider("問題数", 3, 10, 5)
        
        if theme == "じゆうに入力":
            theme = st.text_input("すきなテーマ（例：うみのいきもの）")
            
        if st.button("🚀 AIでもんだいをつくる！", type="primary", use_container_width=True):
            with st.spinner("AIが作成中..."):
                try:
                    prompt = f"子供向け英語タイピング用。テーマ『{theme}』の英単語と日本語訳を{word_count}個、小文字JSON形式で。例: [{{'en':'dog','ja':'いぬ'}}]"
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    res = model.generate_content(prompt)
                    json_match = re.search(r'\[.*\]', res.text, re.DOTALL)
                    if json_match:
                        st.session_state.typing_words = json.loads(json_match.group(0))
                        st.rerun()
                except Exception as e:
                    st.error(f"エラー: {e}")
                    
    with tab2:
        st.write("💡 英単語を入れると、AIが日本語を埋めてくれるよ！")
        
        for i, row in enumerate(st.session_state.input_rows):
            c1, c2 = st.columns(2)
            st.session_state.input_rows[i]["en"] = c1.text_input(f"英語 {i+1}", value=row["en"], key=f"en_input_{i}").lower()
            st.session_state.input_rows[i]["ja"] = c2.text_input(f"日本語 {i+1}", value=row["ja"], key=f"ja_input_{i}")

        col_add, col_ai, col_play = st.columns([1, 2, 2])
        
        if col_add.button("➕ 枠を増やす"):
            st.session_state.input_rows.append({"en": "", "ja": ""})
            st.rerun()

        if col_ai.button("🤖 日本語をAIにおまかせ"):
            targets = [r["en"] for r in st.session_state.input_rows if r["en"] and not r["ja"]]
            if targets:
                with st.spinner("翻訳中..."):
                    try:
                        # 指示を強化し、モデルもflashに変更
                        prompt = f"""
                        以下の英単語リストの簡単な日本語訳（ひらがな多め）をJSON配列のみで返してください。マークダウンの記号や余計な説明は絶対に含めないでください。
                        ターゲット: [{', '.join(targets)}] 
                        出力例: [{{"en":"dog","ja":"いぬ"}}, {{"en":"apple","ja":"りんご"}}]
                        """
                        model = genai.GenerativeModel("gemini-2.5-flash")
                        res = model.generate_content(prompt)
                        
                        # まずはJSON配列っぽい部分を探す
                        json_match = re.search(r'\[.*\]', res.text, re.DOTALL)
                        
                        if json_match:
                            try:
                                translated = json.loads(json_match.group(0))
                                for t in translated:
                                    for r in st.session_state.input_rows:
                                        if r["en"] == t["en"]:
                                            r["ja"] = t["ja"]
                                st.rerun()
                            except json.JSONDecodeError as je:
                                # JSONの形式がおかしい場合のエラー
                                st.error(f"⚠️ データの読み込みに失敗しました (JSONDecodeError): {je}")
                                st.info(f"【デバッグ】AIの生データ:\n{res.text}")
                        else:
                            # そもそも配列の形（[...]）で返ってこなかった場合のエラー
                            st.error("⚠️ AIが正しい形式（JSON配列）で返答しませんでした。")
                            st.info(f"【デバッグ】AIの生データ:\n{res.text}")
                            
                    except Exception as e:
                        # 通信エラーやAPIキーエラーなど、根本的なシステムエラー
                        st.error(f"⚠️ AI通信エラーが発生しました: {e}")
            else:
                st.warning("英語を入力してね！")

        if col_play.button("🚀 このもんだいであそぶ！", type="primary", use_container_width=True):
            valid_words = [r for r in st.session_state.input_rows if r["en"]]
            if valid_words:
                st.session_state.typing_words = valid_words
                st.rerun()
            else:
                st.error("単語をいれてね！")

# ==========================================
# 2. タイピングゲームエリア
# ==========================================
if st.session_state.typing_words:
    st.markdown("---")
    words_json = json.dumps(st.session_state.typing_words)
    
    html_code = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
    <style>
        body {{ font-family: sans-serif; display: flex; flex-direction: column; align-items: center; margin: 0; background: #fff; overflow: hidden; }}
        #prog-bg {{ width: 90%; background: #eee; height: 12px; border-radius: 6px; margin: 10px 0; overflow: hidden; }}
        #prog-bar {{ height: 100%; width: 0%; background: #4CAF50; transition: 0.3s; }}
        #game {{ width: 95%; max-width: 1000px; height: 320px; background: #fcfcfc; border: 4px solid #87CEFA; border-radius: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; }}
        #en {{ font-size: 7rem; font-weight: bold; color: #333; margin: 0; letter-spacing: 4px; }}
        #ja {{ font-size: 2.5rem; color: #666; margin-top: 0px; font-weight: bold; }}
        #msg {{ font-size: 2rem; color: #FF69B4; font-weight: bold; height: 40px; }}
        .typed {{ color: #ddd; }}
        .current {{ color: #FFA500; text-decoration: underline; }}
        .shake {{ animation: shake 0.3s; background: #fff5f5 !important; }}
        @keyframes shake {{ 0%, 100% {{ transform: translateX(0); }} 25% {{ transform: translateX(-8px); }} 50% {{ transform: translateX(8px); }} 75% {{ transform: translateX(-8px); }} }}
        #input-box {{ position: absolute; opacity: 0; pointer-events: none; }}
    </style>
    </head>
    <body>
        <div id="prog-bg"><div id="prog-bar"></div></div>
        <div id="game" onclick="document.getElementById('input-box').focus()">
            <div id="en"></div>
            <div id="ja"></div>
            <div id="msg"></div>
            <input type="text" id="input-box" autocomplete="off">
        </div>
    <script>
        const words = {words_json};
        let idx = 0, typed = "";
        const enDiv = document.getElementById("en"), jaDiv = document.getElementById("ja"), 
              msgDiv = document.getElementById("msg"), bar = document.getElementById("prog-bar"),
              box = document.getElementById("input-box"), game = document.getElementById("game");

        function speak(t) {{ window.speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(t); u.lang = 'en-US'; u.rate = 0.8; window.speechSynthesis.speak(u); }}

        function init() {{
            if (idx >= words.length) {{ 
                enDiv.innerText = "Clear!"; jaDiv.innerText = "すごーい！"; msgDiv.innerText = "🎉✨"; bar.style.width="100%"; return; 
            }}
            typed = "";
            jaDiv.innerText = words[idx].ja;
            msgDiv.innerText = "";
            render();
            bar.style.width = (idx / words.length * 100) + "%";
            setTimeout(() => speak(words[idx].en), 200);
            box.focus();
        }}

        function render() {{
            const target = words[idx].en.toLowerCase();
            let h = "";
            for (let i=0; i<target.length; i++) {{
                if (i < typed.length) h += `<span class="typed">${{target[i]}}</span>`;
                else if (i === typed.length) h += `<span class="current">${{target[i]}}</span>`;
                else h += `<span>${{target[i]}}</span>`;
            }}
            enDiv.innerHTML = h;
        }}

        box.addEventListener("input", (e) => {{
            const inputChar = e.target.value.toLowerCase().slice(-1);
            e.target.value = "";
            const target = words[idx].en.toLowerCase();
            if (inputChar === target[typed.length]) {{
                typed += inputChar;
                game.classList.remove("shake");
                if (typed === target) {{
                    idx++;
                    msgDiv.innerText = "Good Job!";
                    setTimeout(init, 600);
                }} else render();
            }} else {{
                game.classList.remove("shake"); void game.offsetWidth; game.classList.add("shake");
            }}
        }});
        init();
        document.addEventListener("click", () => box.focus());
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=400)
    
    if st.button("↩️ もんだいを作りなおす"):
        st.session_state.typing_words = []
        st.rerun()
