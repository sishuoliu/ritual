# -*- coding: utf-8 -*-
"""生成核心版PDF"""

import subprocess
import os

# 可以指定要转换的文件
html_file = os.path.abspath("print_pack_core_v1.1_COMPLETE.html")
pdf_file = os.path.abspath("print_pack_core_v1.1_COMPLETE.pdf")

# 尝试使用Edge headless
edge_paths = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

for edge_path in edge_paths:
    if os.path.exists(edge_path):
        try:
            html_url = "file:///" + html_file.replace("\\", "/")
            subprocess.run([
                edge_path,
                "--headless",
                "--disable-gpu",
                f"--print-to-pdf={pdf_file}",
                html_url
            ], check=True, timeout=120)
            print(f"已生成: {pdf_file}")
            break
        except Exception as e:
            print(f"Edge失败: {e}")
else:
    print("请使用浏览器打印为PDF")
