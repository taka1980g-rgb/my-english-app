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
            
        word_count = st.slider("もんだいの数", 3, 10, 5)
        
        if st.button("🚀 AIでもんだいをつくる！", type="primary"):
            target_theme = custom_theme if theme == "じゆうに入力" else theme
            with st.spinner("AIがもんだいをつくっているよ..."):
                try:
                    # 💡 APIで単語リストを自動生成
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
                    
                    # AIの返答からJSONだけを抜き出す
                    json_str = re.search(r'\[.*\]', res.text, re.DOTALL)
                    if json_str:
                        st.session_state.typing_words = json.loads(json_str.group(0))
                        st.success("もんだいが できたよ！下のゲーム画面であそんでね。")
                    else:
                        st.error("AIがうまく作れませんでした。もう一度試してね。")
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
                    
    with tab2:
        st.write("「英単語,日本語」の形式で1行ずつ入力してね。（例: apple,りんご）")
        manual_input = st.text_area("もんだいを入力:", height=150)
        if st.button("📝 このもんだいであそぶ"):
            words = []
            for line in manual_input.split('\n'):
                if ',' in line:
                    en, ja = line.split(',', 1)
                    # 強制的に小文字に変換
                    words.append({"en": en.strip().lower(), "ja": ja.strip()})
            if words:
                st.session_state.typing_words = words
                st.success("もんだいが セットされたよ！下の画面であそんでね。")
            else:
                st.warning("正しく入力してね。")

# ==========================================
# 2. タイピングゲームエリア（軽量HTML/JS）
# ==========================================
if st.session_state.typing_words:
    st.markdown("---")
    
    # PythonのリストをJavaScriptで読み込めるJSONテキストに変換
    words_json = json.dumps(st.session_state.typing_words)
    
    # 💡 Streamlit特有の通信ラグを消すため、ゲーム部分をまるごとHTMLで埋め込む
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
            padding: 20px;
            margin: 0;
            box-sizing: border-box;
            user-select: none;
        }}
        #progress-container {{
            width: 100%;
            max-width: 600px;
            background-color: #e0e0e0;
            border-radius: 10px;
            margin-bottom: 20px;
            height: 20px;
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
            width: 100%;
            max-width: 600px;
            background: #f9f9f9;
            padding: 40px 20px;
            border-radius: 20px;
            border: 3px solid #ddd;
            cursor: pointer;
        }}
        /* 第3版のレイアウト：超特大英単語と真下の日本語訳 */
        #word-en {{
            font-size: 5.5rem;
            font-weight: bold;
            color: #333;
            letter-spacing: 5px;
            margin: 0;
            line-height: 1;
        }}
        .typed {{ color: #ccc; }}
        .current {{ color: #ff9800; text-decoration: underline; }}
        
        #word-ja {{
            font-size: 2.5rem;
            color: #555;
            margin-top: 10px;
            margin-bottom: 30px;
            font-weight: bold;
        }}
        #message {{
            font-size: 2rem;
            color: #e91e63;
            height: 40px;
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
        /* スマホやタブレット用の隠し入力欄 */
        #hidden-input {{
            opacity: 0;
            position: absolute;
            top: -1000px;
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
            
            // 強制小文字化して出題
            currentWord = words[currentIndex].en.toLowerCase();
            typedChars = "";
            jaEl.innerHTML = words[currentIndex].ja;
            msgEl.innerHTML = "";
            updateDisplay();
            updateProgress();
            
            // 表示と同時に読み上げ
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
            hiddenInput.focus();
        }}

        const praises = ["Great!", "Good Job!", "Perfect!", "Nice!", "Excellent!"];

        // PCキーボード用
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
                void gameArea.offsetWidth; // アニメーションリセット
                gameArea.classList.add("shake");
            }}
        }});
        
        // スマホ・タブレットのソフトウェアキーボード用
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

        // 紙吹雪エフェクト
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

        // 初期化
        showWord();
        focusInput();
    </script>
    </body>
    </html>
    """
    
    # 枠線のないiframeとしてStreamlitに描画
    components.html(html_code, height=500, scrolling=False)
