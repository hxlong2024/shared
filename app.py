import streamlit as st
import streamlit.components.v1 as components
import requests
import base64
import json
from datetime import datetime, timedelta

# 配置页面布局
st.set_page_config(page_title="万物归藏 | 资源库", page_icon="📦", layout="centered")

# ==========================================
# 优化 1：隐藏菜单、部署按钮和页脚水印
# ==========================================
hide_st_style = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display: none;}
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
</style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# ==========================================
# 优化 2：自定义真实的“一键复制”按钮组件
# ==========================================
def get_copy_button(url):
    safe_url = url.replace("'", "\\'")
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    body {{ margin: 0; padding: 0; background-color: transparent; }}
    .copy-btn {{
        width: 100%; height: 40px;
        background-color: #ffffff; color: #31333f;
        border: 1px solid rgba(49, 51, 63, 0.2); border-radius: 8px;
        cursor: pointer; font-size: 14px; font-weight: 400;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        transition: border-color 0.2s, color 0.2s; box-sizing: border-box;
    }}
    .copy-btn:active {{ background-color: #ff4b4b; color: white; border-color: #ff4b4b; }}
    @media (prefers-color-scheme: dark) {{
        .copy-btn {{ background-color: transparent; color: #fafafa; border-color: rgba(250, 250, 250, 0.2); }}
    }}
    </style>
    </head>
    <body>
        <button class="copy-btn" onclick="copyToClipboard('{safe_url}', this)">🔗 复制链接</button>
        <script>
        function copyToClipboard(text, btn) {{
            navigator.clipboard.writeText(text).then(function() {{
                btn.innerText = '✅ 复制成功';
                btn.style.borderColor = '#00cc66'; btn.style.color = '#00cc66';
                setTimeout(() => {{ 
                    btn.innerText = '🔗 复制链接'; 
                    btn.style.borderColor = ''; btn.style.color = '';
                }}, 2000);
            }});
        }}
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=40)

# --- 从 Streamlit Secrets 读取 GitHub 配置 ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_OWNER = st.secrets["REPO_OWNER"]
    REPO_NAME = st.secrets["REPO_NAME"]
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"] # 从安全配置读取密码
    FILE_PATH = "resources.json"
    BRANCH = "main"
except KeyError as e:
    st.error(f"🚨 缺少必要的密钥配置：{e}！请检查 .streamlit/secrets.toml 文件。")
    st.stop()

# --- GitHub API 数据读写函数 ---
def get_data_from_github():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}?ref={BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return json.loads(base64.b64decode(data['content']).decode('utf-8')), data['sha']
    elif response.status_code == 404:
        return [], None
    else:
        st.error(f"读取数据失败: {response.status_code}")
        return [], None

def save_data_to_github(new_data, sha):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    encoded_content = base64.b64encode(json.dumps(new_data, ensure_ascii=False, indent=4).encode('utf-8')).decode('utf-8')
    payload = {"message": "Auto update resources", "content": encoded_content, "branch": BRANCH}
    if sha: payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload).status_code in [200, 201]

# --- 初始化数据 ---
if 'resources' not in st.session_state or 'file_sha' not in st.session_state:
    with st.spinner("正在加载 万物归藏 资源库..."):
        res_data, file_sha = get_data_from_github()
        st.session_state.resources = res_data
        st.session_state.file_sha = file_sha

# --- 侧边栏导航 ---
st.sidebar.title("万物归藏 导航")
page = st.sidebar.radio("选择操作", ["🌐 资源列表", "⚙️ 录入资源"])

# --- 页面 1: 前端长方形列表展示 ---
if page == "🌐 资源列表":
    st.title("📦 万物归藏")
    
    # 【新增功能】带有搜索按钮的搜索框布局
    search_col1, search_col2 = st.columns([4, 1], vertical_alignment="bottom")
    with search_col1:
        search_query = st.text_input("🔍 搜索资源名称或描述...", "")
    with search_col2:
        # 按钮起视觉确认作用，点击也会触发页面刷新
        st.button("搜索", use_container_width=True)
        
    st.write("---") 
    
    filtered_data = [
        item for item in st.session_state.resources 
        if search_query.lower() in item['name'].lower() or search_query.lower() in item.get('desc', '').lower()
    ]
    
    if not filtered_data:
        st.info("当前没有资源，或者没有搜索到匹配的内容。")
    else:
        for item in filtered_data:
            with st.container(border=True):
                st.subheader(item['name'])
                
                # 【新增功能】显示资源录入的时间（浅灰色小字）
                if item.get('time'):
                    st.caption(f"🕒 发布时间: {item['time']}")
                    
                if item.get('desc'):
                    st.write(item['desc'])
                
                # 安卓端并排显示的按钮
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    st.link_button("🌐 打开链接", item['url'], use_container_width=True)
                with btn_col2:
                    get_copy_button(item['url'])

# --- 页面 2: 后台管理页面 ---
elif page == "⚙️ 录入资源":
    st.title("⚙️ 新增资源")
    
    with st.form("add_resource_form", clear_on_submit=True):
        new_name = st.text_input("资源名称 (必填)*")
        new_desc = st.text_area("资源描述 (选填)")
        new_url = st.text_input("资源链接 (必填)*")
        admin_pwd = st.text_input("管理员密码 (必填)*", type="password")
        
        submitted = st.form_submit_button("🚀 保存并发布")
        
        if submitted:
            # 【安全升级】验证配置的密码
            if admin_pwd != ADMIN_PASSWORD:
                st.error("管理员密码错误！")
            elif not new_name or not new_url:
                st.warning("请填写完整的资源名称和链接！")
            else:
                with st.spinner("正在同步至数据库..."):
                    # 【新增功能】自动获取当前北京时间 (UTC+8)
                    beijing_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
                    
                    new_item = {
                        "name": new_name, 
                        "desc": new_desc, 
                        "url": new_url,
                        "time": beijing_time # 存入时间字段
                    }
                    st.session_state.resources.insert(0, new_item)
                    
                    success = save_data_to_github(st.session_state.resources, st.session_state.file_sha)
                    if success:
                        st.success(f"资源【{new_name}】发布成功！")
                        res_data, file_sha = get_data_from_github()
                        st.session_state.resources = res_data
                        st.session_state.file_sha = file_sha
                    else:
                        st.error("发布失败，请检查网络或 GitHub 配置。")
                        st.session_state.resources.pop(0)
