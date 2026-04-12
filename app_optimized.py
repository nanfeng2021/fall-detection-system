#!/usr/bin/env python3
"""
摔倒检测系统 - 主入口（带认证）

启动命令:
    streamlit run app_optimized.py --server.address 0.0.0.0 --server.port 8501
"""

import streamlit as st
from pathlib import Path

# 重定向到登录页
st.switch_page("app_login.py")
