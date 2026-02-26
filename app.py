import streamlit as st
import requests
import base64
import json

# 配置页面布局 (改为 centered 让长方形卡片在网页中间展示，阅读体验更好)
st.set_page_config(page_title="万物归藏 | 资源库", page_icon="📦", layout="centered")

# --- 从 Streamlit Secrets 读取 GitHub 配置 ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_OWNER = st.secrets["REPO_OWNER"]
    REPO_NAME = st.secrets["REPO_NAME"]
    FILE_PATH = "resources.json"
    BRANCH = "main"
except KeyError:
    st.error("🚨 缺少必要的 GitHub 密钥配置！请检查 .streamlit/secrets.toml 文件。")
    st.stop()

# --- GitHub API 数据读写函数 ---
def get_data_from_github():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}?ref={BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        sha = data['sha']
        content = base64.b64decode(data['content']).decode('utf-8')
        return json.loads(content), sha
    elif response.status_code == 404:
        return [], None
    else:
        st.error(f"读取数据失败: {response.status_code} - {response.text}")
        return [], None

def save_data_to_github(new_data, sha):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    json_str = json.dumps(new_data, ensure_ascii=False, indent=4)
    encoded_content = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": "Auto update resources via Streamlit Admin",
        "content": encoded_content,
        "branch": BRANCH
    }
    if sha:
        payload["sha"] = sha
        
    response = requests.put(url, headers=headers, json=payload)
    return response.status_code in [200, 201]

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
    st.title("📦 万物归藏 资源库")
    
    search_query = st.text_input("🔍 搜索资源名称或描述...", "")
    st.write("---") # 分割线，让界面更清爽
    
    filtered_data = [
        item for item in st.session_state.resources 
        if search_query.lower() in item['name'].lower() or search_query.lower() in item.get('desc', '').lower()
    ]
    
    if not filtered_data:
        st.info("当前没有资源，或者没有搜索到匹配的内容。")
    else:
        # 【核心修改点】不再使用 cols(3) 的网格布局，而是每条数据独占一个长方形容器
        for item in filtered_data:
            with st.container(border=True):
                # 将长方形卡片分为左右两部分：左边(占80%)放文字，右边(占20%)放按钮
                col_left, col_right = st.columns([4, 1], vertical_alignment="center")
                
                with col_left:
                    st.subheader(item['name'])
                    if item.get('desc'):
                        st.write(item['desc'])
                        
                with col_right:
                    # 1. 增加直接跳转访问的按钮
                    st.link_button("🌐 打开链接", item['url'], use_container_width=True)
                    # 2. 利用 st.code 自带的复制功能 (鼠标悬浮会出现“复制”图标)
                    st.code(item['url'], language="text")

# --- 页面 2: 后台管理页面 ---
elif page == "⚙️ 录入资源":
    st.title("⚙️ 新增资源")
    
    with st.form("add_resource_form", clear_on_submit=True):
        new_name = st.text_input("资源名称 (必填)*")
        new_desc = st.text_area("资源描述 (选填，介绍一下这个资源的作用)")
        new_url = st.text_input("资源链接 (必填)*")
        # 【核心修改点】去掉了提取码输入框
        
        admin_pwd = st.text_input("管理员密码 (必填)*", type="password")
        
        submitted = st.form_submit_button("🚀 保存并发布")
        
        if submitted:
            if admin_pwd != "123456": # 别忘了改成你自己的密码
                st.error("管理员密码错误！")
            elif not new_name or not new_url:
                st.warning("请填写完整的资源名称和链接！")
            else:
                with st.spinner("正在同步至数据库..."):
                    # 去掉了 JSON 数据结构里的 code 字段
                    new_item = {
                        "name": new_name,
                        "desc": new_desc,
                        "url": new_url
                    }
                    st.session_state.resources.insert(0, new_item)
                    
                    success = save_data_to_github(st.session_state.resources, st.session_state.file_sha)
                    
                    if success:
                        st.success(f"资源【{new_name}】发布成功！去资源列表看看吧。")
                        res_data, file_sha = get_data_from_github()
                        st.session_state.resources = res_data
                        st.session_state.file_sha = file_sha
                    else:
                        st.error("发布失败，请检查网络或 GitHub 配置。")
                        st.session_state.resources.pop(0)
