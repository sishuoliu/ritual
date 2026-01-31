"""
功德轮回 v5.8 - 将 print_pack HTML 转为 A4 PDF。
依次尝试：weasyprint → Chrome/Edge 无头打印 → 提示浏览器手动打印。
"""
import os
import sys
import subprocess

html_path = os.path.join(os.path.dirname(__file__), "print_pack_v58_FINAL.html")
pdf_path = os.path.join(os.path.dirname(__file__), "print_pack_v58_FINAL.pdf")

if not os.path.exists(html_path):
    print("错误: 未找到 print_pack_v58_FINAL.html")
    sys.exit(1)

# 转为绝对路径，供浏览器使用
html_abs = os.path.abspath(html_path)
pdf_abs = os.path.abspath(pdf_path)

# 1. 尝试 weasyprint（Linux/Mac 或已装 GTK 的 Windows）
try:
    from weasyprint import HTML
    HTML(filename=html_path).write_pdf(pdf_path)
    print(f"已生成: {pdf_abs}")
    sys.exit(0)
except ImportError:
    pass
except Exception as e:
    err = str(e).lower()
    if "gobject" in err or "cairo" in err or "lib" in err:
        pass  # Windows 缺 GTK，跳过
    else:
        print(f"weasyprint 报错: {e}")
        sys.exit(1)

# 2. 尝试 Chrome 或 Edge 无头打印
chrome_paths = [
    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
]
edge_path = os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe")
if not os.path.exists(edge_path):
    edge_path = os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe")

for exe in chrome_paths + [edge_path]:
    if not exe or not os.path.exists(exe):
        continue
    try:
        cmd = [
            exe,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--print-to-pdf=" + pdf_abs,
            "file:///" + html_abs.replace("\\", "/"),
        ]
        subprocess.run(cmd, timeout=60, capture_output=True, check=True)
        print(f"已生成: {pdf_abs}")
        sys.exit(0)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        continue

# 3. 手动说明
print("未检测到可用的 PDF 生成方式（weasyprint 需 GTK，Chrome/Edge 未找到或无头打印失败）。")
print("请手动生成 PDF：")
print(f"  1. 用浏览器打开: {html_abs}")
print("  2. 按 Ctrl+P 打印")
print("  3. 目标打印机选择「另存为 PDF」或「Microsoft Print to PDF」")
print("  4. 纸张选 A4，边距适中，保存为 print_pack_v58_FINAL.pdf")
sys.exit(1)
