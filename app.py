import streamlit as st
import google.generativeai as genai
from streamlit_option_menu import option_menu
from PIL import Image
import json
import time

# --- 1. Page & State Configuration ---
st.set_page_config(
    page_title="暮らしのパートナー (My Life Partner)",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Muji-style" aesthetics
st.markdown("""
    <style>
    .stApp {
        background-color: #Fdfbf7; /* Off-white/Beige */
        color: #4a4a4a;
        font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif;
    }
    .stButton>button {
        background-color: #8c8c8c;
        color: white;
        border-radius: 5px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #6b6b6b;
    }
    .stProgress > div > div > div > div {
        background-color: #A8C8A6; /* Soft Green */
    }
    h1, h2, h3 {
        color: #595959;
        font-weight: 300;
    }
    .battery-container {
        padding: 10px;
        border-radius: 10px;
        background-color: #eee;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'energy_level' not in st.session_state:
    st.session_state.energy_level = 80
if 'tasks' not in st.session_state:
    st.session_state.tasks = []  # List of dicts
if 'garden_counter' not in st.session_state:
    st.session_state.garden_counter = 0
if 'garden_gallery' not in st.session_state:
    st.session_state.garden_gallery = []
if 'generated_menu' not in st.session_state:
    st.session_state.generated_menu = ""

# --- 2. Helper Functions (Gemini) ---

def get_gemini_client(api_key):
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai

def ask_gemini(prompt, api_key, model_name="gemini-1.5-pro-latest", image=None):
    client = get_gemini_client(api_key)
    if not client:
        return "APIキーを設定してください。"
    
    try:
        model = client.GenerativeModel(model_name)
        if image:
            response = model.generate_content([prompt, image])
        else:
            response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

# --- 3. Sidebar & Settings ---

with st.sidebar:
    st.title("🌿 設定")
    api_key = st.text_input("Google API Key", type="password", help="Gemini APIキーを入力してください")
    postal_code = st.text_input("郵便番号 (例: 150-0001)", value="100-0001")
    
    st.markdown("---")
    st.write("心と暮らしを整える、\nあなただけのパートナー。")

# --- 4. Navigation ---

selected = option_menu(
    menu_title=None,
    options=["ココロの電池", "秘密の花園", "キッチンの魔法"],
    icons=["battery-charging", "flower1", "egg-fried"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#fafafa"},
        "icon": {"color": "#8c8c8c", "font-size": "18px"}, 
        "nav-link": {"font-size": "14px", "text-align": "center", "margin":"0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "#A8C8A6", "color": "white"},
    }
)

# --- 5. Tab 1: Energy & Tasks ---

if selected == "ココロの電池":
    st.header("🔋 ココロの電池管理")
    st.caption("無理せず、自分のエネルギーに合わせて動きましょう。")

    # Energy Slider
    current_energy = st.slider("今のエネルギー残量は？", 0, 100, st.session_state.energy_level, key="energy_slider")
    st.session_state.energy_level = current_energy

    # Visual Feedback
    color = "#A8C8A6" # Green
    if current_energy < 40: color = "#F4D03F" # Yellow
    if current_energy < 20: color = "#E74C3C" # Red
    
    st.markdown(f"""
        <div style="background-color:#e0e0e0; border-radius:10px; height:20px; width:100%;">
            <div style="background-color:{color}; width:{current_energy}%; height:100%; border-radius:10px; transition: width 0.5s;"></div>
        </div>
        <p style="text-align:right; font-size:12px;">残り {current_energy}%</p>
    """, unsafe_allow_html=True)

    # Zero Energy Handling
    if current_energy <= 0:
        st.error("⚠️ エネルギー切れです！")
        if st.button("もう無理...休む"):
            st.info("了解です。今日はもう閉店しましょう。おやすみなさい🌙")
        if st.button("5%だけ頑張る (マイクロタスク)"):
            if api_key:
                with st.spinner("AIが超簡単なタスクを考え中..."):
                    micro_task = ask_gemini(
                        "ユーザーは疲れ切っています。座ったままでもできる、1分で終わる、達成感のある超簡単な家事やセルフケアタスクを1つだけ提案してください。日本語で、優しく。",
                        api_key
                    )
                st.success(f"これならどうですか？: {micro_task}")
            else:
                st.warning("APIキーを設定してください。")

    st.markdown("---")

    # Add Task
    with st.expander("📝 新しいタスクを追加", expanded=False):
        with st.form("add_task_form"):
            t_name = st.text_input("タスク名")
            t_cost = st.slider("予想消費エネルギー", 1, 100, 20)
            t_tag = st.selectbox("種類", ["Must (必須)", "Heavy (重い)", "Light (軽い)"])
            submitted = st.form_submit_button("追加する")
            if submitted and t_name:
                st.session_state.tasks.append({
                    "id": len(st.session_state.tasks),
                    "name": t_name,
                    "est_cost": t_cost,
                    "tag": t_tag,
                    "done": False
                })
                st.rerun()

    # Task List
    st.subheader("今日のタスク")
    
    # Filter out done tasks for cleaner view or keep them strikethrough
    active_tasks = [t for t in st.session_state.tasks if not t['done']]
    
    if not active_tasks:
        st.info("タスクはありません。ゆっくりしましょう☕")
    
    for i, task in enumerate(active_tasks):
        col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
        with col1:
            # When checked, trigger completion logic
            if st.button("☐", key=f"check_{task['id']}"):
                # Mark done locally first to trigger UI update
                # In a real app, we'd use a modal, but here we use a container below
                st.session_state.temp_completed_task = task
        with col2:
            st.write(f"**{task['name']}**")
            st.caption(f"予想: -{task['est_cost']}% | {task['tag']}")
        with col3:
            st.write("")

    # Completion Logic (Pop-up simulation)
    if 'temp_completed_task' in st.session_state:
        task = st.session_state.temp_completed_task
        st.markdown(f"### 🎉 お疲れ様です！: {task['name']}")
        
        actual_cost = st.slider("実際、どれくらい疲れましたか？", 0, 100, task['est_cost'], key="actual_cost_slider")
        
        if st.button("完了を確定する"):
            # Deduct energy
            st.session_state.energy_level = max(0, st.session_state.energy_level - actual_cost)
            
            # Update task status
            for t in st.session_state.tasks:
                if t['id'] == task['id']:
                    t['done'] = True
            
            # AI Coaching
            diff = actual_cost - task['est_cost']
            if diff > 20 and api_key:
                prompt = f"ユーザーは「{task['name']}」というタスクを予想{task['est_cost']}の労力だと思っていましたが、実際は{actual_cost}かかりました。自己評価が甘かったようです。優しく、次回の見積もりのための短いアドバイスをください。"
                advice = ask_gemini(prompt, api_key)
                st.toast(advice, icon="💡")
            
            del st.session_state.temp_completed_task
            st.rerun()

# --- 6. Tab 2: Secret Garden ---

elif selected == "秘密の花園":
    st.header("🌸 秘密の花園")
    st.caption("Mustタスクを完了した日は、種に水をあげましょう。3回で花が咲きます。")

    # Calculate Must Tasks
    must_tasks = [t for t in st.session_state.tasks if "Must" in t['tag']]
    must_done = all(t['done'] for t in must_tasks) and len(must_tasks) > 0
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.metric("開花までのカウント", f"{st.session_state.garden_counter} / 3")
        
        # Simulate "End of Day" check
        if st.button("今日を記録する (水やり) 💧"):
            if must_done:
                st.session_state.garden_counter += 1
                st.balloons()
                if st.session_state.garden_counter >= 3:
                    # Trigger Bloom
                    st.session_state.garden_counter = 0
                    if api_key:
                        with st.spinner("つぼみが開いています..."):
                            # Ask Gemini to generate a flower description and an SVG
                            prompt = """
                            架空の、とても美しく癒やされる「魔法の花」を1つ考案してください。
                            出力フォーマットはJSONで:
                            {
                                "name": "花の名前",
                                "description": "花言葉や特徴の短い説明",
                                "emoji": "花を表す絵文字",
                                "svg": "この花を描画するシンプルなSVGコード(100x100, rect等は使わずpathやcircleでカラフルに)"
                            }
                            """
                            res = ask_gemini(prompt, api_key)
                            try:
                                # Simple cleaning of markdown json
                                res = res.replace("```json", "").replace("```", "")
                                flower_data = json.loads(res)
                                st.session_state.garden_gallery.append(flower_data)
                                st.success(f"新しい花が咲きました！: {flower_data['name']}")
                            except:
                                st.error("花の生成に失敗しました...でも気持ちは満開です！")
                    else:
                        st.warning("APIキーがあれば、あなただけの花が咲きます。")
            else:
                st.warning("まだ「Must」タスクが残っています！")

    with col2:
        st.write("### 成長の様子")
        # Simple Visual Progress
        progress = st.session_state.garden_counter / 3
        st.progress(progress)
        if st.session_state.garden_counter == 0:
            st.write("🌱 種が植えられています。")
        elif st.session_state.garden_counter == 1:
            st.write("🌱🌱 双葉が出ました。")
        elif st.session_state.garden_counter == 2:
            st.write("🌿 つぼみが膨らんでいます...")

    st.markdown("---")
    st.subheader("💐 あなたのガーデンギャラリー")
    
    if st.session_state.garden_gallery:
        cols = st.columns(3)
        for idx, flower in enumerate(st.session_state.garden_gallery):
            with cols[idx % 3]:
                st.markdown(f"### {flower.get('emoji', '🌸')}")
                st.markdown(f"**{flower.get('name', '名もなき花')}**")
                st.caption(flower.get('description', ''))
                if 'svg' in flower:
                    st.markdown(f'<div style="width:100px;">{flower["svg"]}</div>', unsafe_allow_html=True)
    else:
        st.write("まだ花は咲いていません。日々の積み重ねで庭を作りましょう。")

# --- 7. Tab 3: Kitchen & Tsukurioki ---

elif selected == "キッチンの魔法":
    st.header("🍳 キッチンの魔法")
    st.caption("レシートから食材を読み取り、土地柄に合わせた献立を提案します。")

    # Inputs
    uploaded_file = st.file_uploader("レシートの写真をアップロード", type=["jpg", "png", "jpeg"])
    
    if uploaded_file and api_key:
        image = Image.open(uploaded_file)
        st.image(image, caption="アップロードされたレシート", width=200)
        
        if st.button("🪄 献立を生成する"):
            with st.spinner("シェフが食材を確認し、地域情報を分析中..."):
                
                # 1. OCR & Context Prompt
                prompt_ocr = f"""
                あなたは日本の家庭料理のプロフェッショナルなシェフです。
                
                以下の情報を考慮して、タスクを実行してください。
                1. ユーザーの郵便番号: {postal_code}
                この郵便番号から、その地域のスーパーマーケットの傾向や特産品、地域の雰囲気（高級住宅街、下町など）を推測してください。
                
                2. 画像（レシート）から購入した食材リストを読み取ってください。
                
                3. 上記の食材と、推測される地域の「冷蔵庫にありそうな調味料・定番食材」を組み合わせて、
                【3日分の作り置き（つくおき）メニュー】を提案してください。
                
                出力構成:
                - **地域の分析**: {postal_code}から推測されるライフスタイルへのコメント（優しく）。
                - **3日間のメニュー**: メインと副菜。
                - **買い足しリスト**: 足りないものがあれば。
                - **魔法の調理手順**: 効率よくこれらを一気に作るための、並列処理の手順（例：お湯を沸かしている間に野菜を切る等）。
                
                トーン＆マナー: 優しく、励ますように。絵文字を多用して。
                """
                
                response_text = ask_gemini(prompt_ocr, api_key, image=image)
                st.session_state.generated_menu = response_text
    
    elif uploaded_file and not api_key:
        st.warning("APIキーを設定してください。")

    # Result Display
    if st.session_state.generated_menu:
        st.markdown("---")
        with st.container():
            st.markdown(st.session_state.generated_menu)
            
        if st.button("クリア"):
            st.session_state.generated_menu = ""
            st.rerun()

# --- Footer ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; font-size: 12px;">
    Powered by Google Gemini 1.5 Pro | Streamlit<br>
    Built for You with 🤍
</div>
""", unsafe_allow_html=True)
