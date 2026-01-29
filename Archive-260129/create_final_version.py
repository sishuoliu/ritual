# -*- coding: utf-8 -*-
import os
from pathlib import Path

base = Path(r"d:\Users\liusishuo\Desktop\MBS\ritul\桌游")
final_dir = base / "终版" / "救赎之路-简易版"
final_dir.mkdir(parents=True, exist_ok=True)
print(f"文件夹创建完成: {final_dir}")
