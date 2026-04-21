import streamlit as st

# アプリ全体の設定（タブのタイトルやアイコン）
st.set_page_config(page_title="家族専用 AI学習アプリ", page_icon="🏠", layout="centered")

APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1234")

if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔒 家族専用 AI学習アプリ")
    pwd = st.text_input("合言葉（パスワード）を入力してください", type="password")
    if pwd == APP_PASSWORD:
        st.session_state["password_correct"] = True
        st.rerun()
    elif pwd != "":
        st.error("パスワードが違います👀")
    st.stop() 

# ログイン成功後の画面
st.title("🏠 ホーム画面")
st.success("ログイン成功！左のサイドバーから使いたいアプリを選んでください。")
st.markdown("""
### 📱 アプリ一覧
* **🗣️ 1_Roleplay**: 自由に会話して実践力を鍛える英会話モード
* **🎧 2_Shadowing**: リスニングと発音を徹底的に鍛える鬼コーチモード
* **🧸 3_Kids**: 【NEW!】お子様向けのフルひらがな＆激甘ごほうびモード
* **⌨️ 4_Typing**: 【NEW!】えいごタイピングであそぼう！

👈 左上の「 ＞ 」ボタンを押してメニューを開いてください。
""")
