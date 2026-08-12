"""
fetch-nickname 打包脚本 (onedir 版)
运行: python build_exe.py
"""

import subprocess, sys, os, shutil

# 某些机器保留了旧 Python 的 TCL_LIBRARY / TK_LIBRARY 环境变量；
# 必须在调用 PyInstaller 前覆盖为当前 Python 的目录，否则 Tk 会被误判为损坏。
python_tcl_dir = os.path.join(os.path.dirname(sys.executable), 'tcl')
current_tcl_library = os.path.join(python_tcl_dir, 'tcl8.6')
current_tk_library = os.path.join(python_tcl_dir, 'tk8.6')
if os.path.isdir(current_tcl_library):
    os.environ['TCL_LIBRARY'] = current_tcl_library
if os.path.isdir(current_tk_library):
    os.environ['TK_LIBRARY'] = current_tk_library

print("=" * 60)
print("步骤1: 安装依赖...")
deps = ['pyinstaller', 'playwright', 'requests', 'pandas', 'openpyxl']
for d in deps:
    subprocess.run([sys.executable, '-m', 'pip', 'install', d, '-q'], check=True)

print("步骤2: 安装 Chromium 浏览器...")
subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)

# 找 chromium 路径
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
chromium_exe = p.chromium.executable_path
p.stop()
chromium_base = os.path.dirname(chromium_exe)  # e.g. .../chromium-xxx/chrome-win
chromium_dir_name = os.path.basename(chromium_base)  # e.g. chrome-win

src_dir = os.path.dirname(__file__)
src_py = os.path.join(src_dir, 'fetch-nickname.py')
dist_dir = os.path.join(src_dir, 'dist_output', 'fetch-nickname')

# 清理旧文件
if os.path.exists(dist_dir):
    shutil.rmtree(dist_dir)

print("步骤3: 开始打包...")
# --onedir: 输出为一个文件夹（里面是 exe + dll + chromium）
# --noconsole: GUI 程序不显示黑窗口
# --add-binary: 把 chromium 整个目录打进包里
result = subprocess.run([
    sys.executable, '-m', 'PyInstaller',
    '--name=fetch-nickname',
    '--onedir',
    '--noconsole',
    '--noconfirm',
    '--distpath=dist_output',
    f'--add-binary={chromium_base};{chromium_dir_name}',
    '--hidden-import=playwright',
    '--hidden-import=playwright.async_api',
    # PyInstaller 在部分 Windows Python 环境中无法自动发现 Tk 的动态组件。
    '--hidden-import=tkinter',
    '--hidden-import=tkinter.ttk',
    '--hidden-import=tkinter.scrolledtext',
    '--hidden-import=tkinter.filedialog',
    '--collect-all=tkinter',
    '--hidden-import=requests',
    '--hidden-import=pandas',
    '--hidden-import=openpyxl',
    '--hidden-import=PIL',
    '--exclude-module=matplotlib',
    '--exclude-module=scipy',
    '--exclude-module=tensorflow',
    '--exclude-module=torch',
    '--exclude-module=PyQt5',
    '--clean',
    src_py
], cwd=src_dir)

if result.returncode == 0:
    print("=" * 60)
    print("[OK] 打包成功!")
    exe_path = os.path.join(src_dir, 'dist_output', 'fetch-nickname', 'fetch-nickname.exe')
    print(f"EXE 所在文件夹: {os.path.join(src_dir, 'dist_output', 'fetch-nickname')}")
    print(f"完整 EXE 路径: {exe_path}")
    if os.path.exists(exe_path):
        print(f"EXE 大小: {os.path.getsize(exe_path) / 1024 / 1024:.1f} MB")
    print("=" * 60)
    print("使用方法: 把 dist_output\\fetch-nickname 文件夹整体拷贝到新电脑，直接运行 fetch-nickname.exe")
    print("（新电脑需要已安装 Google Chrome 才能正常运行 playwright）")
else:
    print("[ERROR] 打包失败")
    sys.exit(1)
