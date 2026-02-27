import streamlit as st
import requests
import base64
import json
import math
import re
from datetime import datetime, timedelta

# 配置页面布局
st.set_page_config(page_title="万物归藏 | 资源库", page_icon="📦", layout="centered")

# ==========================================
# 核心美化：精准隐藏右上角，极致紧凑风格
# ==========================================
custom_css = """
<style>
/* 🎯 核心修复：精准隐藏右上角的所有图标容器，但不隐藏整个 header（保留侧边栏按钮） */
[data-testid="stHeaderActionElements"] {
    display: none !important;
}
#MainMenu {
    display: none !important;
}
.stDeployButton {
    display: none !important;
}
footer {
    display: none !important;
}

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
st.markdown(custom_css, unsafe_allow_html=True)

# --- 从 Streamlit Secrets 读取 GitHub 配置 ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_OWNER = st.secrets["REPO_OWNER"]
    REPO_NAME = st.secrets["REPO_NAME"]
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
    FILE_PATH = "resources.json"
    BRANCH = "main"
except KeyError:
    st.error("🚨 缺少必要的密钥配置！请检查 .streamlit/secrets.toml 文件。")
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
        st.error("网络请求出错，请重试。")
        return [], None

def save_data_to_github(new_data, sha):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    encoded_content = base64.b64encode(json.dumps(new_data, ensure_ascii=False, indent=4).encode('utf-8')).decode('utf-8')
    payload = {"message": "Auto update resources", "content": encoded_content, "branch": BRANCH}
    if sha: payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload).status_code in [200, 201]

# --- 初始化数据 ---
if 'resources' not in st.session_state:
    with st.spinner("正在加载 万物归藏 ..."):
        res_data, file_sha = get_data_from_github()
        st.session_state.resources = res_data
        st.session_state.file_sha = file_sha

if 'current_page' not in st.session_state: st.session_state.current_page = 1
if 'last_search' not in st.session_state: st.session_state.last_search = ""

# --- 侧边栏导航 ---
st.sidebar.title("万物归藏")
page = st.sidebar.radio("选择面板", ["🌐 探索资源", "⚙️ 后台录入"])

# --- 页面 1: 前端列表展示 ---
if page == "🌐 探索资源":
    st.title("📦 万物归藏")
    st.markdown("<p style='color: #64748b; margin-top: -15px; margin-bottom: 20px; font-size: 14px;'>极简、高效的资源收录网络</p>", unsafe_allow_html=True)
    
    search_col1, search_col2 = st.columns([5, 1], vertical_alignment="center")
    with search_col1:
        search_query = st.text_input("搜索框", label_visibility="collapsed", placeholder="输入书名、工具或关键词检索...")
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
    
    if not filtered_data:
        st.info("💡 当前没有资源，或者没有搜索到匹配的内容。")
    else:
        PAGE_SIZE = 15
        total_items = len(filtered_data)
        total_pages = math.ceil(total_items / PAGE_SIZE)
        
        if st.session_state.current_page > total_pages: st.session_state.current_page = total_pages
        start_idx = (st.session_state.current_page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        paginated_data = filtered_data[start_idx:end_idx]
        
        for item in paginated_data:
            with st.container(border=True):
                col_left, col_right = st.columns([5, 1], vertical_alignment="center")
                with col_left:
                    header_html = f"<span style='font-size: 15px; font-weight: 600; color: #1e293b; margin-right: 10px;'>{item['name']}</span>"
                    if item.get('time'): header_html += f"<span style='color: #94a3b8; font-size: 12px; font-family: monospace;'>{item['time'][:10]}</span>" 
                    st.markdown(header_html, unsafe_allow_html=True)
                    if item.get('desc'):
                        st.markdown(f"<div style='color: #64748b; font-size: 13px; margin-top: 2px; line-height: 1.4; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>{item['desc']}</div>", unsafe_allow_html=True)
                with col_right:
                    st.link_button("打开", item['url'], use_container_width=True)
        
        if total_pages > 1:
            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True) 
            page_col1, page_col2, page_col3 = st.columns([1, 2, 1], vertical_alignment="center")
            with page_col1:
                if st.button("上一页", disabled=(st.session_state.current_page == 1), use_container_width=True):
                    st.session_state.current_page -= 1; st.rerun()
            with page_col2:
                st.markdown(f"<div style='text-align: center; color: #94a3b8; font-size: 13px;'>{st.session_state.current_page} / {total_pages} &nbsp;|&nbsp; 共 {total_items} 条</div>", unsafe_allow_html=True)
            with page_col3:
                if st.button("下一页", disabled=(st.session_state.current_page == total_pages), use_container_width=True):
                    st.session_state.current_page += 1; st.rerun()

# --- 页面 2: 后台管理页面 ---
elif page == "⚙️ 后台录入":
    st.title("⚙️ 资源控制台")
    tab1, tab2 = st.tabs(["📝 单条手工录入", "🚀 终极缓冲池引擎"])
    
    with tab1:
        with st.form("add_resource_form", clear_on_submit=True):
            new_name = st.text_input("资源名称 (必填)*")
            new_desc = st.text_area("资源描述 (选填)")
            new_url = st.text_input("资源链接 (必填)*")
            admin_pwd = st.text_input("管理员密码 (必填)*", type="password")
            if st.form_submit_button("保存并发布"):
                if admin_pwd != ADMIN_PASSWORD: st.error("密码错误！")
                elif not new_name or not new_url: st.warning("请填写完整！")
                else:
                    with st.spinner("正在同步..."):
                        beijing_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
                        st.session_state.resources.insert(0, {"name": new_name, "desc": new_desc, "url": new_url, "time": beijing_time})
                        if save_data_to_github(st.session_state.resources, st.session_state.file_sha):
                            st.success(f"发布成功！")
                            res_data, file_sha = get_data_from_github()
                            st.session_state.resources, st.session_state.file_sha = res_data, file_sha
                            st.session_state.current_page = 1
                        else:
                            st.error("发布失败，请检查配置。")
                            st.session_state.resources.pop(0)

    with tab2:
        st.info("💡 完全采用缓冲池状态机逻辑：遇文本进池，遇链接收网。空行作为组别断路器防止误绑。")
        with st.form("batch_resource_form", clear_on_submit=True):
            batch_text = st.text_area("在此粘贴野生文本", height=350)
            batch_desc = st.text_input("批量附加描述（选填）")
            admin_pwd_batch = st.text_input("管理员密码 (必填)*", type="password")
            
            if st.form_submit_button("🚀 启动缓冲池入库"):
                if admin_pwd_batch != ADMIN_PASSWORD:
                    st.error("密码错误！")
                elif not batch_text.strip():
                    st.warning("内容不能为空！")
                else:
                    lines = batch_text.strip().split('\n')
                    new_items_to_add = []
                    beijing_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
                    
                    text_pool = []
                    current_url = None
                    
                    for line in lines:
                        original_line = line.strip()
                        
                        if not original_line:
                            current_url = None
                            continue
                            
                        url_match = re.search(r'(https?://[^\s]+)', original_line)
                        
                        if url_match:
                            found_url = url_match.group(1)
                            
                            if text_pool:
                                for name in text_pool:
                                    new_items_to_add.append({"name": name, "desc": batch_desc, "url": found_url, "time": beijing_time})
                                text_pool = []
                                
                            current_url = found_url
                            
                            clean_line = re.sub(r'https?://[^\s]+', '', original_line)
                            clean_line = re.sub(r'(链接|提取码|密码)[:：\s]*[a-zA-Z0-9]*', '', clean_line).strip()
                            if clean_line:
                                clean_name = re.sub(r'^[\d\.、\s❤️🎧📁🔥]+', '', clean_line).strip()
                                clean_name = re.sub(r'^链接[:：]\s*', '', clean_name)
                                if "《" in clean_name and "》" in clean_name: clean_name = clean_name[clean_name.find("《"):]
                                else: clean_name = re.sub(r'^[【\[].*?[】\]]', '', clean_name).strip()
                                
                                if clean_name and clean_name not in ['言情', '耽美', '国漫', '酸涩文+失忆梗'] and "转存失败" not in clean_name:
                                    new_items_to_add.append({"name": clean_name, "desc": batch_desc, "url": current_url, "time": beijing_time})
                        
                        else:
                            clean_name = re.sub(r'^[\d\.、\s❤️🎧📁🔥]+', '', original_line).strip()
                            clean_name = re.sub(r'^链接[:：]\s*', '', clean_name)
                            
                            if "《" in clean_name and "》" in clean_name:
                                clean_name = clean_name[clean_name.find("《"):]
                            else:
                                clean_name = re.sub(r'^[【\[].*?[】\]]', '', clean_name).strip()
                                
                            if not clean_name or clean_name in ['言情', '耽美', '国漫', '酸涩文+失忆梗'] or "转存失败" in clean_name:
                                continue
                                
                            if current_url:
                                new_items_to_add.append({"name": clean_name, "desc": batch_desc, "url": current_url, "time": beijing_time})
                            else:
                                text_pool.append(clean_name)
                                
                    if not new_items_to_add:
                        st.error("❌ 解析失败：没有找到合规的书单与链接匹配。")
                    else:
                        with st.spinner(f"正在写入 {len(new_items_to_add)} 条数据..."):
                            for item in reversed(new_items_to_add):
                                st.session_state.resources.insert(0, item)
                                
                            if save_data_to_github(st.session_state.resources, st.session_state.file_sha):
                                st.success(f"🎉 成功解析并发布了 {len(new_items_to_add)} 条资源！")
                                res_data, file_sha = get_data_from_github()
                                st.session_state.resources, st.session_state.file_sha = res_data, file_sha
                                st.session_state.current_page = 1
                            else:
                                st.error("发布失败。")
                                for _ in range(len(new_items_to_add)): st.session_state.resources.pop(0)
