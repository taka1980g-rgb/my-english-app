import streamlit as st
import extra_streamlit_components as stx
import datetime

# アプリ全体の設定（タブのタイトルやアイコン）
st.set_page_config(page_title="家族専用 AI学習アプリ", page_icon="🏠", layout="centered")

# クッキーマネージャーの初期化（ブラウザにデータを保存・読み込みするためのツール）
@st.cache_resource
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1234")

# クッキーから過去のログイン状態を取得
cookie_status = cookie_manager.get(cookie="is_logged_in")

# セッションステートの初期化
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

# クッキーで「ログイン済み」と記憶されていれば、パスワード入力をスキップ
if cookie_status == "true":
    st.session_state["password_correct"] = True

# 未ログインの場合の画面
if not st.session_state["password_correct"]:
    st.title("🔒 家族専用 AI学習アプリ")
    pwd = st.text_input("合言葉（パスワード）を入力してください", type="password")
    
    if pwd == APP_PASSWORD:
        # パスワードが合っていれば、クッキーに「ログイン済み」を30日間保存
        expire_date = datetime.datetime.now() + datetime.timedelta(days=30)
        cookie_manager.set("is_logged_in", "true", expires_at=expire_date)
        
        st.session_state["password_correct"] = True
        st.rerun()
    elif pwd != "":
        st.error("パスワードが違います👀")
    
    st.stop() 

# ==========================================
# ログイン成功後の画面
# ==========================================
st.title("🏠 ホーム画面")
st.success("ログイン成功！左のサイドバーから使いたいアプリを選んでください。")

# ログアウト機能
if st.button("🚪 ログアウトする"):
    cookie_manager.delete("is_logged_in")
    st.session_state["password_correct"] = False
    st.rerun()

st.markdown("""
### 📱 アプリ一覧
* **🗣️ 1_Roleplay**: 自由に会話して実践力を鍛える英会話モード
* **🎧 2_Shadowing**: リスニングと発音を徹底的に鍛える鬼コーチモード
* **🧸 3_Kids**: お子様向けのフルひらがな＆激甘ごほうびモード
* **⌨️ 4_Typing**: えいごタイピングであそぼう！

👈 左上の「 ＞ 」ボタンを押してメニューを開いてください。
""")
