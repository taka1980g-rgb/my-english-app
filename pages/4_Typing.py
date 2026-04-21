import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import json
import re

# === 🎨 画面デザインのカスタマイズ（CSS） ===
st.markdown("""
    <style>
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #F0F8FF !important;
        border: 2px solid #87CEFA !important;
        border-radius: 10px;
        padding: 15px;
    }
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1000px !important;
    }
    /* 追加するボタンの余白調整 */
    div.stButton > button {
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# === 🚪 入場パスワードのチェック ===
if not st.session_state.get("password_correct", False):
    st.warning("👈 左上の「＞」を押して、ホーム画面から合言葉を入力してください。")
    st.stop()

# === 🔑 API設定 ===
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=MY_API_KEY.strip())
except Exception:
    st.error("⚠️ StreamlitのSettingsから「Secrets」を開き、GEMINI_API_KEY を設定してください！")
    st.stop()

st.title("⌨️ えいごタイピングであそぼう！")

# === 💾 状態管理 ===
if "typing_words" not in st.session_state:
    st.session_state.typing_words = []
# カスタム入力枠の数を管理
if "custom_word_count" not in st.session_state:
    st.session_state.custom_word_count = 5

# ==========================================
# 1. 問題作成エリア
# ==========================================
with st.expander("📝 もんだいを つくる / えらぶ", expanded=True):
    tab1, tab2 = st.tabs(["✨ AIにおまかせ", "✍️ 自分で入力"])
    
    with tab1:
        theme = st.selectbox("テーマをえらんでね", ["どうぶつ (animals)", "たべもの (food)", "かず (numbers)", "いろ (colors)", "じゆうに入力"])
        custom_theme = ""
        if theme == "じゆうに入力":
            custom_theme = st.text_input("すきなテーマをいれてね（例：のりもの、スポーツ）")
            
        word_count = st.slider("もんだいの数", 3, 10, 5, key="ai_word_count")
        
        if st.button("🚀 AIでもんだいをつくる！", type="primary"):
            target_theme = custom_theme if theme == "じゆうに入力" else theme
            with st.spinner("AIがもんだいをつくっているよ..."):
                try:
                    prompt = f"""
                    子供向けの英語タイピングアプリ用に、以下のテーマに関連する英単語を{word_count}個作成してください。
                    テーマ: {target_theme}
                    
                    【厳守事項】
                    - 全て小文字で出力すること。
                    - JSON形式の配列のみを出力すること。余計な文字列は一切含めない。
                    - フォーマット: [{{"en": "apple", "ja": "りんご"}}, ...]
                    """
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    res = model.generate_content(prompt)
                    
                    json_str = re.search(r'\[.*\]', res.text, re.DOTALL)
                    if json_str:
                        st.session_state.typing_words = json.loads(json_str.group(0))
                        st.success("もんだいが できたよ！下のゲーム画面であそんでね。")
                    else:
                        st.error("AIがうまく作れませんでした。もう一度試してね。")
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
                    
    with tab2:
        st.write("📝 **英単語を入力してね。日本語がわからない時は、後でAIに任せることもできるよ！**")
        
        # 入力枠を生成するためのリストを作成
        custom_inputs = []
        
        for i in range(st.session_state.custom_word_count):
            col_en, col_ja = st.columns(2)
            with col_en:
                en_val = st.text_input(f"単語 {i+1} (英語)", key=f"en_{i}", placeholder="例: apple")
            with col_ja:
                ja_val = st.text_input(f"意味 {i+1} (日本語)", key=f"ja_{i}", placeholder="例: りんご")
            custom_inputs.append({"en": en_val, "ja": ja_val})
            
        # 枠を追加するボタン
        if st.button("➕ 単語の枠を増やす"):
            st.session_state.custom_word_count += 1
            st.rerun()

        st.markdown("---")
        
        col_ai, col_start = st.columns(2)
        with col_ai:
            if st.button("🤖 空白の日本語をAIに翻訳してもらう", use_container_width=True):
                # 英語が入力されていて、日本語が空のものを抽出
                words_to_translate = [item["en"] for item in custom_inputs if item["en"].strip() and not item["ja"].strip()]
                
                if not words_to_translate:
                    st.info("翻訳が必要な単語はありませんでした。")
                else:
                    with st.spinner("AIが日本語を調べています..."):
                        try:
                            prompt = f"""
                            以下の英単語リストの日本語の意味を教えてください。
                            子供向けのアプリで使うため、簡単で一般的な意味を「ひらがな」または「一般的な漢字+ふりがななし」で出力してください。
                            出力形式は必ず以下のJSON配列にしてください。余計なテキストは含めないでください。
                            例: [{{"en": "apple", "ja": "りんご"}}, {{"en": "dog", "ja": "いぬ"}}]
                            
                            単語リスト: {', '.join(words_to_translate)}
                            """
                            model = genai.GenerativeModel("gemini-2.5-flash-lite")
                            res = model.generate_content(prompt)
                            
                            json_str = re.search(r'\[.*\]', res.text, re.DOTALL)
                            if json_str:
                                translated_data = json.loads(json_str.group(0))
                                # 翻訳結果をセッションステート（入力枠）に反映
                                trans_dict = {item["en"].lower(): item["ja"] for item in translated_data}
                                
                                for i in range(st.session_state.custom_word_count):
                                    current_en = st.session_state[f"en_{i}"].strip().lower()
                                    if current_en in trans_dict and not st.session_state[f"ja_{i}"].strip():
                                        # st.session_stateの値を直接更新してUIに反映させる
                                        st.session_state[f"ja_{i}"] = trans_dict[current_en]
                                st.success("日本語を補完しました！")
                                st.rerun() # 画面を再描画して値を反映
                            else:
                                st.error("翻訳に失敗しました。")
                        except Exception as e:
                            st.error(f"エラーが発生しました: {e}")

        with col_start:
            if st.button("🚀 このもんだいであそぶ！", type="primary", use_container_width=True):
                words = []
                for i in range(st.session_state.custom_word_count):
                    en = st.session_state[f"en_{i}"].strip()
                    ja = st.session_state[f"ja_{i}"].strip()
                    # 英語が入力されている行のみをリストに追加（強制的に小文字化）
                    if en:
                        words.append({"en": en.lower(), "ja": ja if ja else "(意味なし)"})
                
                if words:
                    st.session_state.typing_words = words
                    st.success("もんだいが セットされたよ！下の画面であそんでね。")
                else:
                    st.warning("英単語を少なくとも1つ入力してね。")

# ==========================================
# 2. タイピングゲームエリア（軽量HTML/JS）
# ==========================================
if st.session_state.typing_words:
    st.markdown("---")
    
    words_json = json.dumps(st.session_state.typing_words)
    
    html_code = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif;
            background-color: #ffffff;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 10px;
            box-sizing: border-box;
            user-select: none;
            overflow: hidden;
        }}
        #progress-container {{
            width: 100%;
            max-width: 800px;
            background-color: #e0e0e0;
            border-radius: 10px;
            margin-bottom: 15px;
            height: 15px;
            overflow: hidden;
        }}
        #progress-bar {{
            height: 100%;
            width: 0%;
            background-color: #4CAF50;
            transition: width 0.3s ease;
        }}
        #game-area {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            max-width: 800px;
            height: 380px;
            background: #f9f9f9;
            border-radius: 15px;
            border: 3px solid #ddd;
            cursor: pointer;
            position: relative;
        }}
        #word-en {{
            font-size: 5rem;
            font-weight: bold;
            color: #333;
            letter-spacing: 3px;
            margin: 0;
            line-height: 1.2;
        }}
        .typed {{ color: #ccc; }}
        .current {{ color: #ff9800; text-decoration: underline; }}
        
        #word-ja {{
            font-size: 2rem;
            color: #555;
            margin-top: 5px;
            margin-bottom: 15px;
            font-weight: bold;
        }}
        #message {{
            font-size: 1.8rem;
            color: #e91e63;
            height: 35px;
            font-weight: bold;
            animation: pop 0.3s ease-out;
        }}
        @keyframes pop {{
            0% {{ transform: scale(0.5); opacity: 0; }}
            100% {{ transform: scale(1); opacity: 1; }}
        }}
        @keyframes shake {{
            0%, 100% {{ transform: translateX(0); }}
            25% {{ transform: translateX(-10px); }}
            50% {{ transform: translateX(10px); }}
            75% {{ transform: translateX(-10px); }}
        }}
        .shake {{
            animation: shake 0.3s;
            background-color: #ffebee !important;
            border-color: #f44336 !important;
        }}
        #hidden-input {{
            position: absolute;
            opacity: 0;
            width: 1px;
            height: 1px;
            border: none;
            outline: none;
            pointer-events: none;
        }}
    </style>
    </head>
    <body>
        <div id="progress-container"><div id="progress-bar"></div></div>
        
        <div id="game-area" onclick="focusInput()">
            <div id="word-en"></div>
            <div id="word-ja"></div>
            <div id="message"></div>
            <input type="text" id="hidden-input" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
        </div>

    <script>
        const words = {words_json};
        let currentIndex = 0;
        let currentWord = "";
        let typedChars = "";
        
        const enEl = document.getElementById("word-en");
        const jaEl = document.getElementById("word-ja");
        const msgEl = document.getElementById("message");
        const progressBar = document.getElementById("progress-bar");
        const gameArea = document.getElementById("game-area");
        const hiddenInput = document.getElementById("hidden-input");

        function updateProgress() {{
            const percent = (currentIndex / words.length) * 100;
            progressBar.style.width = percent + "%";
        }}

        function speak(text) {{
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'en-US';
                utterance.rate = 0.9;
                window.speechSynthesis.speak(utterance);
            }}
        }}

        function showWord() {{
            if (currentIndex >= words.length) {{
                enEl.innerHTML = "Clear!";
                jaEl.innerHTML = "おめでとう！";
                msgEl.innerHTML = "🎉🎉🎉";
                updateProgress();
                hiddenInput.blur();
                createConfetti();
                return;
            }}
            
            currentWord = words[currentIndex].en.toLowerCase();
            typedChars = "";
            jaEl.innerHTML = words[currentIndex].ja;
            msgEl.innerHTML = "";
            updateDisplay();
            updateProgress();
            
            setTimeout(() => speak(currentWord), 100);
            hiddenInput.value = "";
            focusInput();
        }}

        function updateDisplay() {{
            let html = "";
            for (let i = 0; i < currentWord.length; i++) {{
                if (i < typedChars.length) {{
                    html += `<span class="typed">${{currentWord[i]}}</span>`;
                }} else if (i === typedChars.length) {{
                    html += `<span class="current">${{currentWord[i]}}</span>`;
                }} else {{
                    html += `<span>${{currentWord[i]}}</span>`;
                }}
            }}
            enEl.innerHTML = html;
        }}

        function focusInput() {{
            hiddenInput.focus({{ preventScroll: true }});
        }}

        const praises = ["Great!", "Good Job!", "Perfect!", "Nice!", "Excellent!"];

        document.addEventListener("keydown", (e) => {{
            if (e.key.length > 1 || currentIndex >= words.length) return;

            const targetChar = currentWord[typedChars.length];
            const inputChar = e.key.toLowerCase();

            if (inputChar === targetChar) {{
                typedChars += inputChar;
                updateDisplay();
                gameArea.classList.remove("shake");
                
                if (typedChars.length === currentWord.length) {{
                    msgEl.innerHTML = praises[Math.floor(Math.random() * praises.length)];
                    currentIndex++;
                    setTimeout(showWord, 800);
                }}
            }} else {{
                gameArea.classList.remove("shake");
                void gameArea.offsetWidth;
                gameArea.classList.add("shake");
            }}
        }});
        
        hiddenInput.addEventListener("input", (e) => {{
            const val = hiddenInput.value.toLowerCase();
            if(val.length > 0) {{
                const inputChar = val[val.length - 1];
                const targetChar = currentWord[typedChars.length];
                
                if (inputChar === targetChar) {{
                    typedChars += inputChar;
                    updateDisplay();
                    gameArea.classList.remove("shake");
                    
                    if (typedChars.length === currentWord.length) {{
                        msgEl.innerHTML = praises[Math.floor(Math.random() * praises.length)];
                        currentIndex++;
                        setTimeout(showWord, 800);
                    }}
                }} else {{
                    gameArea.classList.remove("shake");
                    void gameArea.offsetWidth;
                    gameArea.classList.add("shake");
                }}
                hiddenInput.value = ""; 
            }}
        }});

        function createConfetti() {{
            for (let i = 0; i < 80; i++) {{
                const conf = document.createElement("div");
                conf.style.position = "absolute";
                conf.style.width = "12px";
                conf.style.height = "12px";
                conf.style.backgroundColor = ["#f44336", "#e91e63", "#9c27b0", "#3f51b5", "#2196f3", "#4caf50", "#ffeb3b", "#ff9800"][Math.floor(Math.random()*8)];
                conf.style.left = Math.random() * 100 + "vw";
                conf.style.top = "-20px";
                conf.style.zIndex = "1000";
                document.body.appendChild(conf);
                
                const fallDuration = Math.random() * 3 + 2;
                conf.animate([
                    {{ transform: `translate3d(0, 0, 0) rotate(0deg)` }},
                    {{ transform: `translate3d(${{Math.random()*200 - 100}}px, 100vh, 0) rotate(${{Math.random()*720}}deg)` }}
                ], {{
                    duration: fallDuration * 1000,
                    easing: 'cubic-bezier(.37,0,.63,1)',
                    fill: 'forwards'
                }});
            }}
        }}

        showWord();
        focusInput();
    </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=450, scrolling=False)
