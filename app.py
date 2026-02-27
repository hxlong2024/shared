import streamlit as st
import requests
import base64
import json
import math
import re
from datetime import datetime, timedelta

# ==========================================
# 🛑 核弹级界面清爽术：必须放在代码最顶部 🛑
# ==========================================
st.set_page_config(page_title="万物归藏 | 资源库", page_icon="📦", layout="centered")

# 定义终极 CSS
obliterate_ui_css = """
<style>
/* 🎯 1. 强行隐藏整个头部（含右上角头像、Deploy 等） */
header[data-testid="stHeader"] {
    visibility: hidden !important;
    background: transparent !important;
}

/* 🎯 2. 强行隐藏整个底部（含 Streamlit 水印） */
footer {
    visibility: hidden !important;
    display: none !important;
}

/* 🎯 3. 【核心修复】将左上角的侧边栏呼出按钮重新设为可见 */
header[data-testid="stHeader"] button[data-testid="stSidebarCollapseButton"] {
    visibility: visible !important;
    color: #475569 !important;
    background-color: rgba(255,255,255,0.8) !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
}

/* 🎯 4. 【云端绝杀】彻底隐藏右下角的 Manage App 悬浮按钮 */
.viewerBadge_container { display: none !important; }
.viewerBadge_link { display: none !important; }
[data-testid="viewerBadge"] { display: none !important; }

/* 调整主页面间距 */
.block-container {
    padding-top: 3rem !important;
    padding-bottom: 1rem !important;
}

/* ==========================================
   极简数据台自定义样式
   ========================================== */
/* 全局背景色调 */
.stApp { background-color: #f8fafc; }

/* 搜索框紧凑化 */
.stTextInput input {
    border-radius: 12px !important;
    border: 1px solid #e2e8f0 !important;
    padding: 10px 16px !important;
    font-size: 14px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
    transition: all 0.2s ease !important;
}
.stTextInput input:focus {
    border-color: #64748b !important;
    box-shadow: 0 0 0 1px #64748b !important;
}

/* 卡片极简美化 */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #ffffff;
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    padding: 2px 8px !important; 
    margin-bottom: -8px !important; 
    transition: background-color 0.2s !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    background-color: #f8fafc !important;
    border-color: #cbd5e1 !important;
}

/* 打开链接按钮 */
.stLinkButton a {
    border-radius: 6px !important;
    background-color: #f1f5f9 !important;
    color: #475569 !important;
    border: 1px solid #e2e8f0 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    height: 32px !important;
    padding: 0 12px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 0.2s !important;
}
.stLinkButton a:hover {
    background-color: #e2e8f0 !important;
    color: #0f172a !important;
}

/* 分页按钮 */
.stButton button {
    border-radius: 8px !important;
    font-size: 13px !important;
    padding: 4px 8px !important;
    border: 1px solid #e2e8f0 !important;
}
</style>
"""
# 注入终极 CSS
st.markdown(obliterate_ui_css, unsafe_allow_html=True)

# --- 后续核心逻辑原封不动 ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_OWNER = st.secrets["REPO_OWNER"]
    REPO_NAME = st.secrets["REPO_NAME"]
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
    FILE_PATH = "resources.json"
    BRANCH = "main"
except KeyError:
    st.error("🚨 缺少密钥配置！请检查 .streamlit/secrets.toml 文件。")
    st.stop()

def get_data_from_github():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}?ref={BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return json.loads(base64.b64decode(data['content']).decode('utf-8')), data['sha']
    elif response.status_code == 404: return [], None
    else: return [], None

def save_data_to_github(new_data, sha):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    encoded_content = base64.b64encode(json.dumps(new_data, ensure_ascii=False, indent=4).encode('utf-8')).decode('utf-8')
    payload = {"message": "Update", "content": encoded_content, "branch": BRANCH}
    if sha: payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload).status_code in [200, 201]

if 'resources' not in st.session_state:
    res_data, file_sha = get_data_from_github()
    st.session_state.resources, st.session_state.file_sha = res_data, file_sha

if 'current_page' not in st.session_state: st.session_state.current_page = 1
if 'last_search' not in st.session_state: st.session_state.last_search = ""

st.sidebar.title("万物归藏")
page = st.sidebar.radio("选择面板", ["🌐 探索资源", "⚙️ 后台录入"])

if page == "🌐 探索资源":
    st.title("📦 万物归藏")
    st.markdown("<p style='color: #64748b; margin-top: -15px; margin-bottom: 20px; font-size: 14px;'>极简、高效的资源收录网络</p>", unsafe_allow_html=True)
    
    search_col1, search_col2 = st.columns([5, 1], vertical_alignment="center")
    with search_col1:
        search_query = st.text_input("搜索", label_visibility="collapsed", placeholder="输入书名或工具检索...")
    with search_col2:
        st.button("检索", use_container_width=True)
        
    st.write("") 
    
    if search_query != st.session_state.last_search:
        st.session_state.current_page = 1
        st.session_state.last_search = search_query
    
    filtered_data = [
        item for item in st.session_state.resources 
        if search_query.lower() in item['name'].lower() or search_query.lower() in item.get('desc', '').lower()
    ]
    
    if not filtered_data: st.info("💡 没有搜索到内容。")
    else:
        PAGE_SIZE = 15
        total_items = len(filtered_data)
        total_pages = math.ceil(total_items / PAGE_SIZE)
        if st.session_state.current_page > total_pages: st.session_state.current_page = total_pages
        
        start_idx = (st.session_state.current_page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        for item in filtered_data[start_idx:end_idx]:
            with st.container(border=True):
                col_left, col_right = st.columns([5, 1], vertical_alignment="center")
                with col_left:
                    st.markdown(f"<span style='font-size: 15px; font-weight: 600; color: #1e293b; margin-right: 10px;'>{item['name']}</span>", unsafe_allow_html=True)
                    if item.get('time'): st.markdown(f"<span style='color: #94a3b8; font-size: 12px; font-family: monospace;'>{item['time'][:10]}</span>", unsafe_allow_html=True) 
                    if item.get('desc'):
                        st.markdown(f"<div style='color: #64748b; font-size: 13px; margin-top: 2px;'>{item['desc']}</div>", unsafe_allow_html=True)
                with col_right: st.link_button("打开", item['url'], use_container_width=True)
        
        if total_pages > 1:
            st.write("")
            page_col1, page_col2, page_col3 = st.columns([1, 2, 1], vertical_alignment="center")
            with page_col1:
                if st.button("上一页", disabled=(st.session_state.current_page == 1), use_container_width=True):
                    st.session_state.current_page -= 1; st.rerun()
            with page_col2:
                st.markdown(f"<div style='text-align: center; color: #94a3b8; font-size: 13px;'>{st.session_state.current_page} / {total_pages} &nbsp;|&nbsp; 共 {total_items} 条</div>", unsafe_allow_html=True)
            with page_col3:
                if st.button("下一页", disabled=(st.session_state.current_page == total_pages), use_container_width=True):
                    st.session_state.current_page += 1; st.rerun()

elif page == "⚙️ 后台录入":
    st.title("⚙️ 资源控制台")
    tab1, tab2 = st.tabs(["📝 单条录入", "🚀 动态缓冲池"])
    with tab1:
        with st.form("add_form", clear_on_submit=True):
            new_name = st.text_input("名称 (必填)")
            new_desc = st.text_area("描述")
            new_url = st.text_input("链接 (必填)")
            admin_pwd = st.text_input("密码", type="password")
            if st.form_submit_button("发布"):
                if admin_pwd != ADMIN_PASSWORD: st.error("密码错误")
                elif not new_name or not new_url: st.warning("请填写完整")
                else:
                    beijing_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.resources.insert(0, {"name": new_name, "desc": new_desc, "url": new_url, "time": beijing_time})
                    if save_data_to_github(st.session_state.resources, st.session_state.file_sha):
                        res_data, file_sha = get_data_from_github()
                        st.session_state.resources, st.session_state.file_sha = res_data, file_sha
                        st.session_state.current_page = 1
                        st.success("发布成功")
                    else: st.error("发布失败")
    with tab2:
        with st.form("batch_form", clear_on_submit=True):
            batch_text = st.text_area("文本块", height=350)
            batch_desc = st.text_input("批量描述")
            admin_pwd_batch = st.text_input("密码", type="password")
            if st.form_submit_button("智能解析发布"):
                if admin_pwd_batch != ADMIN_PASSWORD: st.error("密码错误")
                else:
                    lines = batch_text.strip().split('\n')
                    new_items, text_pool, current_url = [], [], None
                    beijing_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
                    for line in lines:
                        original_line = line.strip()
                        if not original_line: current_url = None; continue
                        url_match = re.search(r'(https?://[^\s]+)', original_line)
                        if url_match:
                            found_url = url_match.group(1)
                            if text_pool:
                                for name in text_pool: new_items.append({"name": name, "desc": batch_desc, "url": found_url, "time": beijing_time})
                                text_pool = []
                            current_url = found_url
                            clean_line = re.sub(r'https?://[^\s]+', '', original_line)
                            clean_line = re.sub(r'(链接|提取码|密码)[:：\s]*[a-zA-Z0-9]*', '', clean_line).strip()
                            if clean_line:
                                clean_name = re.sub(r'^[\d\.、\s❤️🎧📁🔥]+', '', clean_line).strip()
                                clean_name = re.sub(r'^链接[:：]\s*', '', clean_name)
                                if "《" in clean_name and "》" in clean_name: clean_name = clean_name[clean_name.find("《"):]
                                else: clean_name = re.sub(r'^[【\[].*?[】\]]', '', clean_name).strip()
                                if clean_name and clean_name not in ['言情','耽美','国漫'] and "转存失败" not in clean_name: new_items.append({"name": clean_name, "desc": batch_desc, "url": current_url, "time": beijing_time})
                        else:
                            clean_name = re.sub(r'^[\d\.、\s❤️🎧📁🔥]+', '', original_line).strip()
                            clean_name = re.sub(r'^链接[:：]\s*', '', clean_name)
                            if "《" in clean_name and "》" in clean_name: clean_name = clean_name[clean_name.find("《"):]
                            else: clean_name = re.sub(r'^[【\[].*?[】\]]', '', clean_name).strip()
                            if not clean_name or clean_name in ['言情','耽美','国漫'] or "转存失败" in clean_name: continue
                            if current_url: new_items.append({"name": clean_name, "desc": batch_desc, "url": current_url, "time": beijing_time})
                            else: text_pool.append(clean_name)
                    if not new_items: st.error("解析失败")
                    else:
                        for item in reversed(new_items): st.session_state.resources.insert(0, item)
                        if save_data_to_github(st.session_state.resources, st.session_state.file_sha):
                            res_data, file_sha = get_data_from_github()
                            st.session_state.resources, st.session_state.file_sha = res_data, file_sha
                            st.session_state.current_page = 1
                            st.success("发布成功")
