#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WKT边界格式转换工具
提供WKT格式与Boundaries边界坐标格式之间的双向转换功能
纯Python实现，无外部依赖
"""

import re
import csv
import sys
import os

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False


class WKTConverter:
    """WKT与Boundaries格式双向转换器"""
    
    @staticmethod
    def detect_encoding(file_path: str) -> str:
        """
        检测文件编码格式
        支持UTF-8、GBK、GB18030、UTF-16等编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            编码名称（小写）
        """
        encodings = ['utf-8', 'gbk', 'gb18030', 'utf-16']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)
                return encoding
            except (UnicodeDecodeError, LookupError):
                continue
        
        return 'utf-8'  # 默认返回UTF-8
    
    @staticmethod
    def read_csv(file_path: str, encoding: str = 'utf-8') -> tuple:
        """
        读取CSV文件
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
            
        Returns:
            (fieldnames, rows) - 字段名列表和数据行列表
        """
        try:
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                rows = list(reader)
            return fieldnames, rows
        except Exception as e:
            raise RuntimeError(f"读取文件失败: {str(e)}")
    
    @staticmethod
    def write_csv(file_path: str, fieldnames: list, rows: list, encoding: str = 'utf-8') -> None:
        """
        写入CSV文件
        
        Args:
            file_path: 文件路径
            fieldnames: 字段名列表
            rows: 数据行列表
            encoding: 文件编码
        """
        try:
            with open(file_path, 'w', encoding=encoding, newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            raise RuntimeError(f"写入文件失败: {str(e)}")
    
    @staticmethod
    def detect_boundaries_field(fieldnames: list) -> str:
        """
        检测Boundaries字段
        
        Args:
            fieldnames: 字段名列表
            
        Returns:
            Boundaries字段名，未找到返回空字符串
        """
        # 优先查找boundaries字段
        for field in fieldnames:
            if field.lower() == 'boundaries':
                return field
        
        # 查找包含下划线和分号模式的字段（采样前几行判断）
        return ''
    
    @staticmethod
    def detect_wkt_field(fieldnames: list) -> str:
        """
        检测WKT字段
        
        Args:
            fieldnames: 字段名列表
            
        Returns:
            WKT字段名，未找到返回空字符串
        """
        wkt_keywords = ['wkt', 'geometry', 'geom', 'polygon', 'shape']
        
        for field in fieldnames:
            lower_field = field.lower()
            for keyword in wkt_keywords:
                if keyword in lower_field:
                    return field
        
        return ''
    
    @staticmethod
    def boundaries_to_wkt(boundaries_str: str) -> str:
        """
        Boundaries格式转WKT POLYGON格式
        
        Boundaries格式: 经度_纬度;经度_纬度;...
        WKT格式: POLYGON ((x1 y1, x2 y2, ...))
        
        Args:
            boundaries_str: Boundaries格式字符串
            
        Returns:
            WKT格式字符串
        """
        if not boundaries_str or not boundaries_str.strip():
            return ''
        
        points = boundaries_str.strip().split(';')
        if len(points) < 3:
            raise ValueError("边界坐标至少需要3个点才能构成多边形")
        
        # 解析每个点
        wkt_points = []
        for point in points:
            point = point.strip()
            if '_' in point:
                parts = point.split('_')
                if len(parts) >= 2:
                    lon = parts[0].strip()
                    lat = parts[1].strip()
                    wkt_points.append(f"{lon} {lat}")
        
        if len(wkt_points) < 3:
            raise ValueError("有效坐标点不足3个")
        
        # 确保多边形闭合
        if wkt_points[0] != wkt_points[-1]:
            wkt_points.append(wkt_points[0])
        
        return f"POLYGON (({', '.join(wkt_points)}))"
    
    @staticmethod
    def wkt_to_boundaries(wkt_str: str) -> str:
        """
        WKT格式转Boundaries格式
        
        WKT格式: POLYGON ((x1 y1, x2 y2, ...))
        Boundaries格式: 经度_纬度;经度_纬度;...
        
        Args:
            wkt_str: WKT格式字符串
            
        Returns:
            Boundaries格式字符串
        """
        if not wkt_str or not wkt_str.strip():
            return ''
        
        # 提取坐标部分
        match = re.search(r'POLYGON\s*\(\(\s*([^\)]+)\s*\)\)', wkt_str, re.IGNORECASE)
        if not match:
            # 尝试MULTIPOLYGON
            match = re.search(r'MULTIPOLYGON\s*\(\(\(\s*([^\)]+)\s*\)\)\)', wkt_str, re.IGNORECASE)
        
        if not match:
            raise ValueError("无法解析WKT格式")
        
        coords_str = match.group(1)
        
        # 分割坐标点
        points = re.split(r',\s*', coords_str)
        
        # 转换为Boundaries格式
        boundary_points = []
        for point in points:
            point = point.strip()
            if point:
                parts = point.split()
                if len(parts) >= 2:
                    lon = parts[0].strip()
                    lat = parts[1].strip()
                    boundary_points.append(f"{lon}_{lat}")
        
        # 去重（移除最后一个闭合点）
        if len(boundary_points) >= 2 and boundary_points[0] == boundary_points[-1]:
            boundary_points = boundary_points[:-1]
        
        return ';'.join(boundary_points)
    
    @staticmethod
    def convert_boundaries_file(input_path: str, output_path: str = None) -> str:
        """
        批量转换Boundaries文件为WKT
        
        Args:
            input_path: 输入CSV文件路径
            output_path: 输出文件路径，默认为 原文件名_wkt.csv
            
        Returns:
            输出文件路径
        """
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_wkt{ext}"
        
        # 检测编码
        encoding = WKTConverter.detect_encoding(input_path)
        
        # 读取文件
        fieldnames, rows = WKTConverter.read_csv(input_path, encoding)
        
        # 检测Boundaries字段
        boundaries_field = WKTConverter.detect_boundaries_field(fieldnames)
        if not boundaries_field:
            # 如果没有找到boundaries字段，提示用户选择
            print(f"警告：未自动检测到boundaries字段，请手动选择")
            return ""
        
        # 添加WKT字段
        new_fieldnames = fieldnames.copy()
        if 'wkt' not in new_fieldnames:
            new_fieldnames.append('wkt')
        
        # 转换数据
        for row in rows:
            boundaries_str = row.get(boundaries_field, '')
            try:
                row['wkt'] = WKTConverter.boundaries_to_wkt(boundaries_str)
            except Exception as e:
                row['wkt'] = f"错误: {str(e)}"
        
        # 写入输出文件
        WKTConverter.write_csv(output_path, new_fieldnames, rows, 'utf-8')
        
        return output_path
    
    @staticmethod
    def convert_wkt_file(input_path: str, output_path: str = None) -> str:
        """
        批量转换WKT文件为Boundaries格式
        
        Args:
            input_path: 输入CSV文件路径
            output_path: 输出文件路径，默认为 原文件名_converted.csv
            
        Returns:
            输出文件路径
        """
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_converted{ext}"
        
        # 检测编码
        encoding = WKTConverter.detect_encoding(input_path)
        
        # 读取文件
        fieldnames, rows = WKTConverter.read_csv(input_path, encoding)
        
        # 检测WKT字段
        wkt_field = WKTConverter.detect_wkt_field(fieldnames)
        if not wkt_field:
            print(f"警告：未自动检测到WKT字段，请手动选择")
            return ""
        
        # 添加boundaries字段
        new_fieldnames = fieldnames.copy()
        if 'boundaries' not in new_fieldnames:
            new_fieldnames.append('boundaries')
        
        # 转换数据
        for row in rows:
            wkt_str = row.get(wkt_field, '')
            try:
                row['boundaries'] = WKTConverter.wkt_to_boundaries(wkt_str)
            except Exception as e:
                row['boundaries'] = f"错误: {str(e)}"
        
        # 写入输出文件
        WKTConverter.write_csv(output_path, new_fieldnames, rows, 'utf-8')
        
        return output_path


def main_cli():
    """命令行界面"""
    if len(sys.argv) < 3:
        print("WKT边界格式转换工具")
        print("使用方法:")
        print("  python wkt_converter.py boundaries2wkt <输入文件> [输出文件]")
        print("  python wkt_converter.py wkt2boundaries <输入文件> [输出文件]")
        print("  python wkt_converter.py gui")
        return
    
    command = sys.argv[1].lower()
    input_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.exists(input_path):
        print(f"错误：文件不存在: {input_path}")
        return
    
    try:
        if command == 'boundaries2wkt':
            result = WKTConverter.convert_boundaries_file(input_path, output_path)
            if result:
                print(f"转换完成！输出文件: {result}")
        elif command == 'wkt2boundaries':
            result = WKTConverter.convert_wkt_file(input_path, output_path)
            if result:
                print(f"转换完成！输出文件: {result}")
        else:
            print(f"未知命令: {command}")
    except Exception as e:
        print(f"转换失败: {str(e)}")


def main_gui():
    """图形界面"""
    if not HAS_TKINTER:
        print("错误：需要安装tkinter才能使用图形界面")
        return
    
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    def select_file():
        return filedialog.askopenfilename(
            title="选择CSV文件",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
    
    def select_output_file(default_name):
        return filedialog.asksaveasfilename(
            title="保存输出文件",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV文件", "*.csv")]
        )
    
    # 选择转换模式
    mode = messagebox.askquestion(
        "选择转换方向",
        "请选择转换方向:\n\n"
        "是(Y): Boundaries → WKT\n"
        "否(N): WKT → Boundaries"
    )
    
    if mode not in ('yes', 'no'):
        return
    
    # 选择输入文件
    input_path = select_file()
    if not input_path:
        messagebox.showinfo("提示", "未选择输入文件")
        return
    
    # 生成默认输出文件名
    base, ext = os.path.splitext(input_path)
    if mode == 'yes':
        default_output = f"{base}_wkt{ext}"
    else:
        default_output = f"{base}_converted{ext}"
    
    # 选择输出文件
    output_path = select_output_file(default_output)
    if not output_path:
        messagebox.showinfo("提示", "未选择输出文件")
        return
    
    try:
        if mode == 'yes':
            WKTConverter.convert_boundaries_file(input_path, output_path)
        else:
            WKTConverter.convert_wkt_file(input_path, output_path)
        
        messagebox.showinfo("成功", f"转换完成！\n\n输出文件: {output_path}")
    except Exception as e:
        messagebox.showerror("错误", f"转换失败:\n{str(e)}")


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1].lower() == 'gui':
        main_gui()
    else:
        main_cli()
