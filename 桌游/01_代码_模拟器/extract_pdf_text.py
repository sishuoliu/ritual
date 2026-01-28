#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF文字提取脚本
逐行提取PDF文件中的文字并保存为txt文档
"""

import os
import glob
from pathlib import Path

try:
    import pdfplumber
    USE_PDFPLUMBER = True
except ImportError:
    try:
        import PyPDF2
        USE_PDFPLUMBER = False
    except ImportError:
        print("错误: 需要安装 pdfplumber 或 PyPDF2 库")
        print("请运行: pip install pdfplumber")
        exit(1)


def extract_text_with_pdfplumber(pdf_path):
    """使用pdfplumber提取PDF文字"""
    text_lines = []
    with pdfplumber.open(pdf_path) as pdf:
        print(f"正在处理: {pdf_path}")
        print(f"总页数: {len(pdf.pages)}")
        
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"处理第 {page_num}/{len(pdf.pages)} 页...")
            text = page.extract_text()
            if text:
                # 按行分割并保留
                lines = text.split('\n')
                text_lines.extend(lines)
    
    return text_lines


def extract_text_with_pypdf2(pdf_path):
    """使用PyPDF2提取PDF文字"""
    text_lines = []
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        print(f"正在处理: {pdf_path}")
        print(f"总页数: {len(pdf_reader.pages)}")
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            print(f"处理第 {page_num}/{len(pdf_reader.pages)} 页...")
            text = page.extract_text()
            if text:
                # 按行分割并保留
                lines = text.split('\n')
                text_lines.extend(lines)
    
    return text_lines


def extract_pdf_to_txt(pdf_path, output_path=None):
    """提取PDF文字并保存为txt文件"""
    if output_path is None:
        # 生成输出文件名
        pdf_name = Path(pdf_path).stem
        output_path = Path(pdf_path).parent / f"{pdf_name}.txt"
    
    # 提取文字
    if USE_PDFPLUMBER:
        text_lines = extract_text_with_pdfplumber(pdf_path)
    else:
        text_lines = extract_text_with_pypdf2(pdf_path)
    
    # 保存为txt文件
    with open(output_path, 'w', encoding='utf-8') as f:
        for line in text_lines:
            f.write(line + '\n')
    
    print(f"\n提取完成!")
    print(f"输出文件: {output_path}")
    print(f"总行数: {len(text_lines)}")
    
    return output_path


def main():
    """主函数：处理当前文件夹中的所有PDF文件"""
    current_dir = Path(__file__).parent
    pdf_files = list(current_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("当前文件夹中没有找到PDF文件")
        return
    
    print(f"找到 {len(pdf_files)} 个PDF文件\n")
    
    for pdf_file in pdf_files:
        try:
            extract_pdf_to_txt(pdf_file)
            print("-" * 50)
        except Exception as e:
            print(f"处理 {pdf_file} 时出错: {str(e)}")
            print("-" * 50)


if __name__ == "__main__":
    main()
