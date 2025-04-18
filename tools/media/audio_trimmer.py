#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
音频文件截取工具 - 支持m4a格式音频文件的自定义区间截取

此脚本允许用户指定m4a音频文件的开始和结束时间（以毫秒为单位），
然后截取该区间并生成一个新的音频文件。

使用方法:
    python audio_trimmer.py input.m4a output.m4a 30000 60000
    (从30秒开始截取到60秒)
"""

import os
import sys
import platform
import argparse
from pydub import AudioSegment

def ensure_long_path_support(path):
    """
    确保Windows系统下支持长路径
    
    Args:
        path (str): 原始路径
        
    Returns:
        str: 处理后的路径
    """
    if platform.system() == 'Windows' and not path.startswith('\\\\?\\'):
        # 确保路径是绝对路径
        abs_path = os.path.abspath(path)
        # 添加长路径前缀
        return '\\\\?\\' + abs_path
    return path

def safe_makedirs(directory):
    """
    安全地创建目录，处理Windows长路径问题
    
    Args:
        directory (str): 要创建的目录路径
    """
    if not os.path.exists(directory):
        directory = ensure_long_path_support(directory)
        os.makedirs(directory, exist_ok=True)

def trim_audio(input_file, output_file, start_ms, end_ms):
    """
    截取音频文件的指定区间
    
    Args:
        input_file (str): 输入音频文件路径
        output_file (str): 输出音频文件路径
        start_ms (int): 开始时间（毫秒）
        end_ms (int): 结束时间（毫秒）
        
    Returns:
        bool: 操作是否成功
    """
    try:
        # 处理Windows长路径问题
        input_file = ensure_long_path_support(input_file)
        output_file = ensure_long_path_support(output_file)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        safe_makedirs(output_dir)
        
        # 加载音频文件
        print(f"正在加载音频文件: {input_file}")
        audio = AudioSegment.from_file(input_file, format="m4a")
        
        # 检查时间范围是否有效
        if start_ms < 0:
            start_ms = 0
        if end_ms > len(audio):
            end_ms = len(audio)
        if start_ms >= end_ms:
            raise ValueError("开始时间必须小于结束时间")
            
        # 截取指定区间
        print(f"截取音频区间: {start_ms}ms 到 {end_ms}ms")
        trimmed_audio = audio[start_ms:end_ms]
        
        # 导出新音频文件
        print(f"正在导出到: {output_file}")
        trimmed_audio.export(output_file, format="m4a")
        
        print(f"音频截取成功! 新文件: {output_file}")
        print(f"原始音频长度: {len(audio)/1000:.2f}秒")
        print(f"截取后音频长度: {len(trimmed_audio)/1000:.2f}秒")
        return True
        
    except Exception as e:
        print(f"错误: {str(e)}")
        return False

def format_time(ms):
    """
    将毫秒转换为人类可读的时间格式 (HH:MM:SS.mmm)
    
    Args:
        ms (int): 毫秒数
        
    Returns:
        str: 格式化的时间字符串
    """
    seconds, ms = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='音频文件截取工具 - 支持m4a格式')
    parser.add_argument('input_file', help='输入音频文件路径')
    parser.add_argument('output_file', help='输出音频文件路径')
    parser.add_argument('start_ms', type=int, help='开始时间（毫秒）')
    parser.add_argument('end_ms', type=int, help='结束时间（毫秒）')
    
    # 添加可选参数，支持时分秒格式
    parser.add_argument('--time-format', choices=['ms', 'hms'], default='ms',
                        help='时间格式: ms=毫秒, hms=时:分:秒')
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件不存在: {args.input_file}")
        return 1
    
    # 检查输入文件扩展名
    if not args.input_file.lower().endswith('.m4a'):
        print(f"警告: 输入文件可能不是m4a格式: {args.input_file}")
        response = input("是否继续? (y/n): ")
        if response.lower() != 'y':
            return 1
    
    # 处理时间格式
    start_ms = args.start_ms
    end_ms = args.end_ms
    
    # 执行音频截取
    success = trim_audio(args.input_file, args.output_file, start_ms, end_ms)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
