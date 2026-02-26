import streamlit as st
import streamlit.components.v1 as components
import requests
import base64
import json
import math
import re
from datetime import datetime, timedelta

# 配置页面布局
st.set_page_config(page_title="万物归藏 | 资源库", page_icon="📦", layout="centered")

# ==========================================
# 优化 1：保留侧边栏按钮，隐藏多余菜单
# ==========================================
hide_st_style = """
<style>
#MainMenu {visibility: hidden;}
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
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
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

# --- 初始化数据与分页状态 ---
if 'resources' not in st.session_state:
    with st.spinner("正在加载 万物归藏 资源库..."):
        res_data, file_sha = get_data_from_github()
        st.session_state.resources = res_data
        st.session_state.file_sha = file_sha

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'last_search' not in st.session_state:
    st.session_state.last_search = ""

# --- 侧边栏导航 ---
st.sidebar.title("万物归藏 导航")
page = st.sidebar.radio("选择操作", ["🌐 资源列表", "⚙️ 录入资源"])

# --- 页面 1: 前端列表展示 (带分页功能) ---
if page == "🌐 资源列表":
    st.title("📦 万物归藏")
    
    search_col1, search_col2 = st.columns([4, 1], vertical_alignment="bottom")
    with search_col1:
        search_query = st.text_input("🔍 搜索资源名称或描述...", "")
    with search_col2:
        st.button("搜索", use_container_width=True)
        
    st.write("---") 
    
    if search_query != st.session_state.last_search:
        st.session_state.current_page = 1
        st.session_state.last_search = search_query
    
    filtered_data = [
        item for item in st.session_state.resources 
        if search_query.lower() in item['name'].lower() or search_query.lower() in item.get('desc', '').lower()
    ]
    
    if not filtered_data:
        st.info("当前没有资源，或者没有搜索到匹配的内容。")
    else:
        PAGE_SIZE = 10
        total_items = len(filtered_data)
        total_pages = math.ceil(total_items / PAGE_SIZE)
        
        if st.session_state.current_page > total_pages:
            st.session_state.current_page = total_pages
            
        start_idx = (st.session_state.current_page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        paginated_data = filtered_data[start_idx:end_idx]
        
        for item in paginated_data:
            with st.container(border=True):
                st.subheader(item['name'])
                if item.get('time'):
                    st.caption(f"🕒 发布时间: {item['time']}")
                if item.get('desc'):
                    st.write(item['desc'])
                
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    st.link_button("🌐 打开链接", item['url'], use_container_width=True)
                with btn_col2:
                    get_copy_button(item['url'])
        
        if total_pages > 1:
            st.write("") 
            page_col1, page_col2, page_col3 = st.columns([1, 2, 1], vertical_alignment="center")
            with page_col1:
                if st.button("⬅️ 上一页", disabled=(st.session_state.current_page == 1), use_container_width=True):
                    st.session_state.current_page -= 1
                    st.rerun()
            with page_col2:
                st.markdown(f"<div style='text-align: center; color: #666;'>第 {st.session_state.current_page} / {total_pages} 页 (共 {total_items} 条)</div>", unsafe_allow_html=True)
            with page_col3:
                if st.button("下一页 ➡️", disabled=(st.session_state.current_page == total_pages), use_container_width=True):
                    st.session_state.current_page += 1
                    st.rerun()

# --- 页面 2: 后台管理页面 ---
elif page == "⚙️ 录入资源":
    st.title("⚙️ 新增资源")
    
    # 【核心新增】使用 Tabs 将单条录入和批量录入分开
    tab1, tab2 = st.tabs(["📝 单条手工录入", "🚀 智能批量解析"])
    
    # --- Tab 1: 单条录入 ---
    with tab1:
        with st.form("add_resource_form", clear_on_submit=True):
            new_name = st.text_input("资源名称 (必填)*")
            new_desc = st.text_area("资源描述 (选填)")
            new_url = st.text_input("资源链接 (必填)*")
            admin_pwd = st.text_input("管理员密码 (必填)*", type="password")
            submitted = st.form_submit_button("保存并发布")
            
            if submitted:
                if admin_pwd != ADMIN_PASSWORD:
                    st.error("管理员密码错误！")
                elif not new_name or not new_url:
                    st.warning("请填写完整的资源名称和链接！")
                else:
                    with st.spinner("正在同步至数据库..."):
                        beijing_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
                        new_item = {"name": new_name, "desc": new_desc, "url": new_url, "time": beijing_time}
                        st.session_state.resources.insert(0, new_item)
                        success = save_data_to_github(st.session_state.resources, st.session_state.file_sha)
                        if success:
                            st.success(f"资源【{new_name}】发布成功！")
                            res_data, file_sha = get_data_from_github()
                            st.session_state.resources = res_data
                            st.session_state.file_sha = file_sha
                            st.session_state.current_page = 1
                        else:
                            st.error("发布失败，请检查配置。")
                            st.session_state.resources.pop(0)

    # --- Tab 2: 智能批量解析 ---
    with tab2:
        st.info("💡 提示：请直接粘贴包含【一个链接】和【多个带有换行的书名/资源名】的文本段落。系统会自动去除序号并匹配链接。")
        with st.form("batch_resource_form", clear_on_submit=True):
            batch_text = st.text_area("在此粘贴文本块（高度自适应）", height=300, placeholder="链接：https://pan.baidu.com/...\n\n1.第一本书\n2.第二本书")
            batch_desc = st.text_input("批量附加描述（选填，比如：小说合集，会添加到所有条目下）")
            admin_pwd_batch = st.text_input("管理员密码 (必填)*", type="password")
            
            submitted_batch = st.form_submit_button("🚀 一键解析并批量发布")
            
            if submitted_batch:
                if admin_pwd_batch != ADMIN_PASSWORD:
                    st.error("管理员密码错误！")
                elif not batch_text.strip():
                    st.warning("内容不能为空！")
                else:
                    # 1. 尝试使用正则提取 URL
                    url_match = re.search(r'(https?://[^\s]+)', batch_text)
                    if not url_match:
                        st.error("❌ 无法在文本中找到有效的网页链接 (http/https开头)！")
                    else:
                        base_url = url_match.group(1)
                        lines = batch_text.strip().split('\n')
                        new_items_to_add = []
                        beijing_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 2. 逐行解析文本
                        for line in lines:
                            line = line.strip()
                            # 过滤掉空行、含有http的行、含有"链接："等说明性质的行
                            if not line or "http" in line or line.startswith("链接") or line.startswith("提取码"):
                                continue
                            
                            # 使用正则去除前缀数字和点，比如 "1." "20. " "3、"
                            clean_name = re.sub(r'^\d+[\.、\s]*', '', line)
                            
                            if clean_name:
                                new_items_to_add.append({
                                    "name": clean_name,
                                    "desc": batch_desc if batch_desc else "",
                                    "url": base_url, # 所有解析出来的资源共享这一个链接
                                    "time": beijing_time
                                })
                        
                        if not new_items_to_add:
                            st.warning("⚠️ 找到了链接，但没有解析到有效的资源名称。")
                        else:
                            with st.spinner(f"正在批量写入 {len(new_items_to_add)} 条数据至 GitHub..."):
                                # 倒序插入，确保第1条在网页最上面
                                for item in reversed(new_items_to_add):
                                    st.session_state.resources.insert(0, item)
                                
                                success = save_data_to_github(st.session_state.resources, st.session_state.file_sha)
                                if success:
                                    st.success(f"🎉 成功批量解析并发布了 {len(new_items_to_add)} 条资源！")
                                    # 刷新数据
                                    res_data, file_sha = get_data_from_github()
                                    st.session_state.resources = res_data
                                    st.session_state.file_sha = file_sha
                                    st.session_state.current_page = 1
                                else:
                                    st.error("发布失败，请检查网络或 GitHub 配置。")
                                    # 失败的话把刚刚加进去的数据撤销掉
                                    for _ in range(len(new_items_to_add)):
                                        st.session_state.resources.pop(0)
