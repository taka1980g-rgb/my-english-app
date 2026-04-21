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
if "custom_word_count" not in st.session_state:
    st.session_state.custom_word_count = 5

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
        
        if st.session_state.get("trigger_translation"):
            st.session_state.trigger_translation = False
            targets = []
            for i in range(st.session_state.custom_word_count):
                en = st.session_state.get(f"en_input_{i}", "").strip()
                ja = st.session_state.get(f"ja_input_{i}", "").strip()
                if en and not ja:
                    targets.append((i, en))
            
            if targets:
                with st.spinner("AIが日本語を調べています..."):
                    try:
                        words_to_translate = [t[1] for t in targets]
                        prompt = f"子供向けアプリ用です。以下の英単語の簡単な日本語訳（ひらがな多め）をJSON配列のみで返してください。 単語: [{', '.join(words_to_translate)}] 出力例: [{{\\\"en\\\":\\\"dog\\\",\\\"ja\\\":\\\"いぬ\\\"}}]"
                        model = genai.GenerativeModel("gemini-2.5-flash")
                        res = model.generate_content(prompt)
                        json_match = re.search(r'\[.*\]', res.text, re.DOTALL)
                        if json_match:
                            translated = json.loads(json_match.group(0))
                            trans_dict = {item["en"].lower(): item["ja"] for item in translated}
                            for idx, en in targets:
                                if en.lower() in trans_dict:
                                    st.session_state[f"ja_input_{idx}"] = trans_dict[en.lower()]
                            st.success("日本語を補完しました！")
                        else:
                            st.error("⚠️ AIが正しい形式で返答しませんでした。")
                    except Exception as e:
                        st.error(f"⚠️ 翻訳中にエラーが発生しました: {e}")
            else:
                st.warning("英語を入力してください！")

        for i in range(st.session_state.custom_word_count):
            c1, c2 = st.columns(2)
            c1.text_input(f"英語 {i+1}", key=f"en_input_{i}", placeholder="例: apple")
            c2.text_input(f"日本語 {i+1}", key=f"ja_input_{i}", placeholder="例: りんご")

        st.markdown("---")
        col_add, col_ai, col_play = st.columns([1, 2, 2])
        
        if col_add.button("➕ 枠を増やす"):
            st.session_state.custom_word_count += 1
            st.rerun()

        if col_ai.button("🤖 日本語をAIにおまかせ"):
            st.session_state.trigger_translation = True
            st.rerun()

        if col_play.button("🚀 このもんだいであそぶ！", type="primary", use_container_width=True):
            valid_words = []
            for i in range(st.session_state.custom_word_count):
                en = st.session_state.get(f"en_input_{i}", "").strip().lower()
                ja = st.session_state.get(f"ja_input_{i}", "").strip()
                if en:
                    valid_words.append({"en": en, "ja": ja if ja else "(意味なし)"})
            
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
        #game {{ width: 95%; max-width: 1000px; height: 380px; background: #fcfcfc; border: 4px solid #87CEFA; border-radius: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; overflow: hidden; }}
        #en {{ font-size: 7rem; font-weight: bold; color: #333; margin: 0; letter-spacing: 4px; line-height: 1.2; transition: opacity 0.3s; }}
        #ja {{ font-size: 2.5rem; color: #666; margin-top: 5px; font-weight: bold; transition: opacity 0.3s; }}
        #msg {{ font-size: 2rem; color: #FF69B4; font-weight: bold; height: 40px; transition: opacity 0.3s; }}
        #timer-display {{ position: absolute; top: 15px; right: 25px; font-size: 1.5rem; color: #999; font-family: monospace; }}
        .typed {{ color: #ddd; }}
        .current {{ color: #FFA500; text-decoration: underline; }}
        #input-box {{ position: absolute; opacity: 0; width: 1px; height: 1px; pointer-events: none; }}
        
        /* ランキング画面のデザイン */
        #ranking-modal {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(255, 255, 255, 0.98); display: none;
            flex-direction: column; align-items: center; justify-content: center; z-index: 10;
        }}
        #ranking-modal h2 {{ color: #ff9800; margin: 0 0 10px 0; font-size: 2.5rem; }}
        .ranking-table {{ border-collapse: collapse; width: 80%; max-width: 500px; font-size: 1.2rem; margin-bottom: 10px; background: white; }}
        .ranking-table th, .ranking-table td {{ border: 2px solid #87CEFA; padding: 6px; text-align: center; }}
        .ranking-table th {{ background: #87CEFA; color: white; }}
        .ranking-table tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .top1 {{ font-weight: bold; color: #d4af37; font-size: 1.4rem; }}
        
        #entry-area {{ margin-bottom: 15px; font-size: 1.2rem; text-align: center; }}
        #player-name {{ font-size: 1.2rem; padding: 8px; width: 180px; text-align: center; border: 2px solid #87CEFA; border-radius: 5px; outline: none; }}
        .btn {{
            padding: 10px 20px; font-size: 1.1rem; color: white; background: #4CAF50;
            border: none; border-radius: 10px; cursor: pointer; font-weight: bold; margin: 5px;
        }}
        .btn:hover {{ background: #45a049; }}
        .btn-blue {{ background: #2196F3; }}
        .btn-red {{ background: #f44336; font-size: 0.9rem; padding: 5px 10px; opacity: 0.8; }}
        .btn-red:hover {{ background: #d32f2f; opacity: 1; }}
        
        #controls {{ display: flex; flex-wrap: wrap; justify-content: center; margin-top: 5px; }}
    </style>
    </head>
    <body>
        <div id="prog-bg"><div id="prog-bar"></div></div>
        <div id="game" onclick="handleGameClick()">
            <div id="timer-display">TIME: 0.0s</div>
            <div id="en"></div>
            <div id="ja"></div>
            <div id="msg"></div>
            <input type="text" id="input-box" autocomplete="off" autocorrect="off" spellcheck="false">
            
            <div id="ranking-modal">
                <h2>👑 【<span id="rank-word-count"></span>問】ランキング 👑</h2>
                <div id="entry-area">
                    タイム: <strong style="color:red; font-size:1.5rem;" id="final-time-disp"></strong> 秒<br><br>
                    なまえ：<input type="text" id="player-name" placeholder="ここに名前をいれてね">
                    <button class="btn btn-blue" onclick="saveScore()">とうろく</button>
                </div>
                <table class="ranking-table" id="ranking-table">
                    <thead><tr><th>順位</th><th>なまえ</th><th>タイム</th></tr></thead>
                    <tbody id="ranking-body"></tbody>
                </table>
                <div id="controls">
                    <button class="btn" onclick="restart()">もういちど あそぶ</button>
                    <button class="btn btn-red" onclick="resetRanking()">ランキングをリセット</button>
                </div>
            </div>
        </div>
    <script>
        const words = {words_json};
        const storageKey = "typing_ranking_" + words.length;
        let idx = 0, typed = "";
        let startTime = null, timerInterval = null, finalTimeStr = "";

        const enDiv = document.getElementById("en"), jaDiv = document.getElementById("ja"), 
              msgDiv = document.getElementById("msg"), bar = document.getElementById("prog-bar"),
              box = document.getElementById("input-box"), timerDiv = document.getElementById("timer-display"),
              rankingModal = document.getElementById("ranking-modal"), rankingBody = document.getElementById("ranking-body"),
              entryArea = document.getElementById("entry-area"), playerNameInput = document.getElementById("player-name");

        // 前回の名前を復元
        playerNameInput.value = localStorage.getItem("typing_last_name") || "";
        document.getElementById("rank-word-count").innerText = words.length;

        function speak(t) {{ window.speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(t); u.lang = 'en-US'; u.rate = 0.8; window.speechSynthesis.speak(u); }}

        // ゲームエリアをクリックした時の処理
        function handleGameClick() {{
            // ランキング画面が出ていない時だけタイピングボックスにフォーカス
            if (rankingModal.style.display !== "flex") {{
                box.focus({{preventScroll: true}});
            }}
        }}

        function restart() {{
            rankingModal.style.display = "none";
            idx = 0; typed = ""; startTime = null;
            clearInterval(timerInterval);
            timerDiv.innerText = "TIME: 0.0s";
            enDiv.style.opacity = "1"; jaDiv.style.opacity = "1"; msgDiv.style.opacity = "1";
            init();
        }}

        function init() {{
            if (idx >= words.length) {{ 
                clearInterval(timerInterval);
                finalTimeStr = ((Date.now() - startTime) / 1000).toFixed(1);
                enDiv.style.opacity = "0"; jaDiv.style.opacity = "0"; msgDiv.style.opacity = "0";
                
                document.getElementById("final-time-disp").innerText = finalTimeStr;
                entryArea.style.display = "block";
                loadRankingTable();
                rankingModal.style.display = "flex";
                createConfetti();
                return; 
            }}
            typed = "";
            jaDiv.innerText = words[idx].ja;
            msgDiv.innerText = "";
            render();
            bar.style.width = (idx / words.length * 100) + "%";
            setTimeout(() => speak(words[idx].en), 200);
            box.focus({{preventScroll: true}});
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

        function handleInput(char) {{
            if (idx >= words.length || rankingModal.style.display === "flex") return;
            
            if (startTime === null) {{
                startTime = Date.now();
                timerInterval = setInterval(() => {{
                    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                    timerDiv.innerText = "TIME: " + elapsed + "s";
                }}, 100);
            }}

            const target = words[idx].en.toLowerCase();
            if (char === target[typed.length]) {{
                typed += char;
                if (typed === target) {{
                    idx++; msgDiv.innerText = "Good Job!"; setTimeout(init, 500);
                }} else render();
            }}
        }}

        document.addEventListener("keydown", (e) => {{
            // 入力欄にフォーカスがある時はタイピング判定をスキップ
            if (document.activeElement === playerNameInput) return;
            if (e.key.length > 1) return;
            handleInput(e.key.toLowerCase());
        }});
        
        box.addEventListener("input", (e) => {{
            const val = e.target.value.toLowerCase();
            if(val.length > 0) {{
                handleInput(val[val.length - 1]);
                e.target.value = ""; 
            }}
        }});

        function loadRankingTable() {{
            let rankings = JSON.parse(localStorage.getItem(storageKey) || "[]");
            rankingBody.innerHTML = "";
            if (rankings.length === 0) {{
                rankingBody.innerHTML = "<tr><td colspan='3'>まだデータがありません</td></tr>";
                return;
            }}
            rankings.forEach((r, i) => {{
                const tr = document.createElement("tr");
                if (i === 0) tr.classList.add("top1");
                tr.innerHTML = `<td>${{i + 1}}位</td><td>${{r.name}}</td><td>${{r.time.toFixed(1)}}秒</td>`;
                rankingBody.appendChild(tr);
            }});
        }}

        function saveScore() {{
            const nameInput = playerNameInput.value.trim() || "ななし";
            localStorage.setItem("typing_last_name", nameInput);
            
            let rankings = JSON.parse(localStorage.getItem(storageKey) || "[]");
            rankings.push({{ name: nameInput, time: parseFloat(finalTimeStr) }});
            rankings.sort((a, b) => a.time - b.time);
            rankings = rankings.slice(0, 5);
            
            localStorage.setItem(storageKey, JSON.stringify(rankings));
            entryArea.style.display = "none";
            loadRankingTable();
        }}

        function resetRanking() {{
            if (confirm("この問題数のランキングをすべて消去しますか？")) {{
                localStorage.removeItem(storageKey);
                loadRankingTable();
            }}
        }}

        function createConfetti() {{
            for (let i = 0; i < 50; i++) {{
                const conf = document.createElement("div");
                conf.style.position = "absolute";
                conf.style.width = "10px"; conf.style.height = "10px";
                conf.style.backgroundColor = ["#f44336", "#e91e63", "#9c27b0", "#3f51b5", "#2196f3", "#4caf50", "#ffeb3b", "#ff9800"][Math.floor(Math.random()*8)];
                conf.style.left = Math.random() * 100 + "%"; conf.style.top = "-20px";
                conf.style.zIndex = "20";
                rankingModal.appendChild(conf);
                const fallDuration = Math.random() * 2 + 1.5;
                conf.animate([
                    {{ transform: `translate3d(0, 0, 0) rotate(0deg)` }},
                    {{ transform: `translate3d(${{Math.random()*100 - 50}}px, 400px, 0) rotate(${{Math.random()*720}}deg)` }}
                ], {{ duration: fallDuration * 1000, easing: 'ease-in', fill: 'forwards' }});
            }}
        }}

        init();
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=500)
    
    if st.button("↩️ もんだいを作りなおす"):
        st.session_state.typing_words = []
        st.rerun()
