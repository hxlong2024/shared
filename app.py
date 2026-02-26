import streamlit as st
import requests
import base64
import json

# 配置页面布局
st.set_page_config(page_title="我的资源发布站", page_icon="📦", layout="wide")

# --- 从 Streamlit Secrets 读取 GitHub 配置 ---
# 请确保在 Streamlit Cloud 的后台配置了这些环境变量
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_OWNER = st.secrets["REPO_OWNER"]  # 你的 GitHub 用户名
    REPO_NAME = st.secrets["REPO_NAME"]    # 你的仓库名
    FILE_PATH = "resources.json"           # 数据文件路径
    BRANCH = "main"                        # 你的主分支名称 (可能是 main 或 master)
except KeyError:
    st.error("🚨 缺少必要的 GitHub 密钥配置！请在 Streamlit Secrets 中配置 GITHUB_TOKEN, REPO_OWNER, 和 REPO_NAME。")
    st.stop()

# --- GitHub API 数据读写函数 ---
def get_data_from_github():
    """通过 GitHub API 读取 resources.json 文件"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}?ref={BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        sha = data['sha'] # 获取文件的 SHA 值，更新文件时必须带上
        content = base64.b64decode(data['content']).decode('utf-8')
        return json.loads(content), sha
    elif response.status_code == 404:
        return [], None # 文件不存在时返回空列表
    else:
        st.error(f"读取数据失败: {response.status_code} - {response.text}")
        return [], None

def save_data_to_github(new_data, sha):
    """通过 GitHub API 更新 resources.json 文件"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 将数据转为 JSON 并进行 base64 编码
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
    with st.spinner("正在从 GitHub 拉取最新资源..."):
        res_data, file_sha = get_data_from_github()
        st.session_state.resources = res_data
        st.session_state.file_sha = file_sha

# --- 侧边栏导航 ---
st.sidebar.title("导航面板")
page = st.sidebar.radio("选择页面", ["🌐 资源大厅", "⚙️ 后台管理"])

# --- 页面 1: 前端资源大厅 ---
if page == "🌐 资源大厅":
    st.title("📦 资源大厅")
    
    search_query = st.text_input("🔍 搜索资源名称或描述...", "")
    
    filtered_data = [
        item for item in st.session_state.resources 
        if search_query.lower() in item['name'].lower() or search_query.lower() in item.get('desc', '').lower()
    ]
    
    if not filtered_data:
        st.info("还没有发布任何资源，去后台添加吧！")
    else:
        cols = st.columns(3)
        for index, item in enumerate(filtered_data):
            with cols[index % 3]:
                with st.container(border=True):
                    st.subheader(item['name'])
                    st.write(item.get('desc', ''))
                    st.caption("🔗 链接 (点击右上角一键复制):")
                    st.code(item['url'], language="text")
                    if item.get('code'):
                        st.caption("🔑 提取码:")
                        st.code(item['code'], language="text")

# --- 页面 2: 后台管理页面 ---
elif page == "⚙️ 后台管理":
    st.title("⚙️ 发布新资源")
    
    with st.form("add_resource_form", clear_on_submit=True):
        new_name = st.text_input("资源名称 (必填)*")
        new_desc = st.text_area("资源描述")
        new_url = st.text_input("资源链接 (必填)*")
        new_code = st.text_input("提取码 (选填)")
        admin_pwd = st.text_input("管理员密码 (必填)*", type="password")
        
        submitted = st.form_submit_button("🚀 同步到 GitHub 并发布")
        
        if submitted:
            if admin_pwd != "123456": # 记得修改这个密码
                st.error("管理员密码错误！")
            elif not new_name or not new_url:
                st.warning("请填写资源名称和链接！")
            else:
                with st.spinner("正在写入 GitHub 仓库..."):
                    new_item = {
                        "name": new_name,
                        "desc": new_desc,
                        "url": new_url,
                        "code": new_code
                    }
                    # 插入到最前面
                    st.session_state.resources.insert(0, new_item)
                    
                    # 保存到 GitHub
                    success = save_data_to_github(st.session_state.resources, st.session_state.file_sha)
                    
                    if success:
                        st.success(f"资源【{new_name}】发布成功！")
                        # 重新拉取以更新 SHA 值，防止连续点击发布报错
                        res_data, file_sha = get_data_from_github()
                        st.session_state.resources = res_data
                        st.session_state.file_sha = file_sha
                    else:
                        st.error("发布失败，请检查 GitHub Token 或仓库配置。")
                        # 失败时回退本地数据
                        st.session_state.resources.pop(0)
