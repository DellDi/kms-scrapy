#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高级音频处理工具 - 支持多种格式的音频文件处理

功能:
1. 截取指定时间区间
2. 调整音量
3. 转换音频格式
4. 添加淡入淡出效果
5. 合并多个音频文件

支持格式: m4a, mp3, wav, ogg, flac等(依赖ffmpeg)
"""

import os
import sys
import platform
import argparse
from datetime import datetime
import re
from pydub import AudioSegment
from pydub.effects import normalize
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 支持的音频格式
SUPPORTED_FORMATS = ['m4a', 'mp3', 'wav', 'ogg', 'flac']

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

def parse_time(time_str):
    """
    解析时间字符串为毫秒
    支持格式:
    - 纯数字 (直接作为毫秒)
    - MM:SS (分:秒)
    - HH:MM:SS (时:分:秒)
    - 任何以上格式加小数点表示毫秒 (如 01:30.500)
    
    Args:
        time_str (str): 时间字符串
        
    Returns:
        int: 毫秒数
    """
    # 如果是纯数字，直接返回
    if time_str.isdigit():
        return int(time_str)
    
    # 检查是否为浮点数（秒）
    try:
        return int(float(time_str) * 1000)
    except ValueError:
        pass
    
    # 尝试解析 HH:MM:SS.mmm 或 MM:SS.mmm 格式
    time_parts = time_str.replace(',', '.').split('.')
    main_time = time_parts[0]
    ms = 0
    if len(time_parts) > 1:
        # 处理毫秒部分
        ms_str = time_parts[1]
        if len(ms_str) == 1:
            ms = int(ms_str) * 100
        elif len(ms_str) == 2:
            ms = int(ms_str) * 10
        elif len(ms_str) >= 3:
            ms = int(ms_str[:3])
    
    # 分割时:分:秒
    parts = main_time.split(':')
    
    if len(parts) == 3:  # HH:MM:SS
        hours, minutes, seconds = map(int, parts)
        total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + ms
    elif len(parts) == 2:  # MM:SS
        minutes, seconds = map(int, parts)
        total_ms = (minutes * 60 + seconds) * 1000 + ms
    else:
        raise ValueError(f"无法解析时间格式: {time_str}")
    
    return total_ms

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

def get_file_format(file_path):
    """
    获取文件格式
    
    Args:
        file_path (str): 文件路径
        
    Returns:
        str: 文件格式 (不带点)
    """
    _, ext = os.path.splitext(file_path)
    return ext.lstrip('.').lower()

def load_audio(file_path):
    """
    加载音频文件
    
    Args:
        file_path (str): 音频文件路径
        
    Returns:
        AudioSegment: 加载的音频对象
    """
    file_path = ensure_long_path_support(file_path)
    file_format = get_file_format(file_path)
    
    if file_format not in SUPPORTED_FORMATS:
        logger.warning(f"警告: 文件格式 '{file_format}' 可能不受支持")
    
    try:
        return AudioSegment.from_file(file_path, format=file_format)
    except Exception as e:
        logger.error(f"加载音频文件失败: {e}")
        raise

def trim_audio(audio, start_ms, end_ms):
    """
    截取音频的指定区间
    
    Args:
        audio (AudioSegment): 音频对象
        start_ms (int): 开始时间（毫秒）
        end_ms (int): 结束时间（毫秒）
        
    Returns:
        AudioSegment: 截取后的音频对象
    """
    # 检查时间范围是否有效
    if start_ms < 0:
        logger.warning(f"开始时间 {start_ms}ms 小于0，已调整为0ms")
        start_ms = 0
    
    if end_ms > len(audio):
        logger.warning(f"结束时间 {end_ms}ms 超出音频长度 {len(audio)}ms，已调整为 {len(audio)}ms")
        end_ms = len(audio)
    
    if start_ms >= end_ms:
        raise ValueError(f"开始时间 ({start_ms}ms) 必须小于结束时间 ({end_ms}ms)")
    
    logger.info(f"截取音频区间: {format_time(start_ms)} 到 {format_time(end_ms)}")
    return audio[start_ms:end_ms]

def adjust_volume(audio, volume_db):
    """
    调整音频音量
    
    Args:
        audio (AudioSegment): 音频对象
        volume_db (float): 音量调整值 (dB)
        
    Returns:
        AudioSegment: 调整后的音频对象
    """
    logger.info(f"调整音量: {volume_db}dB")
    return audio + volume_db

def add_fade(audio, fade_in_ms, fade_out_ms):
    """
    添加淡入淡出效果
    
    Args:
        audio (AudioSegment): 音频对象
        fade_in_ms (int): 淡入时长（毫秒）
        fade_out_ms (int): 淡出时长（毫秒）
        
    Returns:
        AudioSegment: 处理后的音频对象
    """
    result = audio
    
    if fade_in_ms > 0:
        logger.info(f"添加淡入效果: {fade_in_ms}ms")
        result = result.fade_in(fade_in_ms)
    
    if fade_out_ms > 0:
        logger.info(f"添加淡出效果: {fade_out_ms}ms")
        result = result.fade_out(fade_out_ms)
    
    return result

def normalize_audio(audio):
    """
    标准化音频音量
    
    Args:
        audio (AudioSegment): 音频对象
        
    Returns:
        AudioSegment: 标准化后的音频对象
    """
    logger.info("标准化音频音量")
    return normalize(audio)

def merge_audios(audio_files, crossfade_ms=0):
    """
    合并多个音频文件
    
    Args:
        audio_files (list): 音频文件路径列表
        crossfade_ms (int): 交叉淡入淡出时长（毫秒）
        
    Returns:
        AudioSegment: 合并后的音频对象
    """
    if not audio_files:
        raise ValueError("没有提供音频文件")
    
    logger.info(f"正在合并 {len(audio_files)} 个音频文件")
    
    # 加载第一个音频文件
    result = load_audio(audio_files[0])
    
    # 合并其余音频文件
    for file_path in audio_files[1:]:
        audio = load_audio(file_path)
        
        if crossfade_ms > 0:
            logger.info(f"使用 {crossfade_ms}ms 交叉淡变合并文件: {os.path.basename(file_path)}")
            result = result.append(audio, crossfade=crossfade_ms)
        else:
            logger.info(f"合并文件: {os.path.basename(file_path)}")
            result += audio
    
    return result

def process_audio(args):
    """
    处理音频文件
    
    Args:
        args: 命令行参数
        
    Returns:
        bool: 操作是否成功
    """
    try:
        # 加载音频文件
        logger.info(f"正在加载音频文件: {args.input_file}")
        audio = load_audio(args.input_file)
        logger.info(f"原始音频长度: {format_time(len(audio))}")
        
        # 截取指定区间
        if args.start is not None or args.end is not None:
            start_ms = parse_time(args.start) if args.start is not None else 0
            end_ms = parse_time(args.end) if args.end is not None else len(audio)
            audio = trim_audio(audio, start_ms, end_ms)
        
        # 调整音量
        if args.volume is not None:
            audio = adjust_volume(audio, args.volume)
        
        # 标准化音量
        if args.normalize:
            audio = normalize_audio(audio)
        
        # 添加淡入淡出效果
        if args.fade_in or args.fade_out:
            fade_in_ms = parse_time(args.fade_in) if args.fade_in else 0
            fade_out_ms = parse_time(args.fade_out) if args.fade_out else 0
            audio = add_fade(audio, fade_in_ms, fade_out_ms)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(args.output_file)
        if output_dir:
            safe_makedirs(output_dir)
        
        # 导出处理后的音频
        output_format = get_file_format(args.output_file)
        logger.info(f"正在导出到: {args.output_file} (格式: {output_format})")
        
        # 处理Windows长路径问题
        output_file = ensure_long_path_support(args.output_file)
        
        # 设置导出参数
        export_params = {}
        if args.bitrate:
            export_params["bitrate"] = args.bitrate
        
        audio.export(
            output_file,
            format=output_format,
            **export_params
        )
        
        logger.info(f"处理完成! 新文件: {args.output_file}")
        logger.info(f"处理后音频长度: {format_time(len(audio))}")
        return True
        
    except Exception as e:
        logger.error(f"处理音频时出错: {str(e)}")
        return False

def merge_mode(args):
    """
    合并模式处理
    
    Args:
        args: 命令行参数
        
    Returns:
        bool: 操作是否成功
    """
    try:
        # 合并音频文件
        audio = merge_audios(args.input_files, args.crossfade)
        
        # 标准化音量
        if args.normalize:
            audio = normalize_audio(audio)
        
        # 添加淡入淡出效果
        if args.fade_in or args.fade_out:
            fade_in_ms = parse_time(args.fade_in) if args.fade_in else 0
            fade_out_ms = parse_time(args.fade_out) if args.fade_out else 0
            audio = add_fade(audio, fade_in_ms, fade_out_ms)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(args.output_file)
        if output_dir:
            safe_makedirs(output_dir)
        
        # 导出处理后的音频
        output_format = get_file_format(args.output_file)
        logger.info(f"正在导出到: {args.output_file} (格式: {output_format})")
        
        # 处理Windows长路径问题
        output_file = ensure_long_path_support(args.output_file)
        
        # 设置导出参数
        export_params = {}
        if args.bitrate:
            export_params["bitrate"] = args.bitrate
        
        audio.export(
            output_file,
            format=output_format,
            **export_params
        )
        
        logger.info(f"合并完成! 新文件: {args.output_file}")
        logger.info(f"合并后音频长度: {format_time(len(audio))}")
        return True
        
    except Exception as e:
        logger.error(f"合并音频时出错: {str(e)}")
        return False

def main():
    """主函数"""
    # 创建主解析器
    parser = argparse.ArgumentParser(
        description='高级音频处理工具 - 支持多种格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 截取音频的30秒到1分钟区间
  python audio_processor.py trim input.m4a output.m4a --start 30000 --end 60000
  
  # 使用时分秒格式截取音频
  python audio_processor.py trim input.m4a output.m4a --start 0:30 --end 1:00
  
  # 调整音量并添加淡入淡出效果
  python audio_processor.py trim input.m4a output.m4a --start 0:30 --end 1:00 --volume 3 --fade-in 1000 --fade-out 2000
  
  # 合并多个音频文件
  python audio_processor.py merge output.m4a input1.m4a input2.m4a input3.m4a --crossfade 500
        """
    )
    
    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 截取命令
    trim_parser = subparsers.add_parser('trim', help='截取音频')
    trim_parser.add_argument('input_file', help='输入音频文件路径')
    trim_parser.add_argument('output_file', help='输出音频文件路径')
    trim_parser.add_argument('--start', help='开始时间 (毫秒或 HH:MM:SS 格式)')
    trim_parser.add_argument('--end', help='结束时间 (毫秒或 HH:MM:SS 格式)')
    trim_parser.add_argument('--volume', type=float, help='音量调整 (dB)')
    trim_parser.add_argument('--normalize', action='store_true', help='标准化音量')
    trim_parser.add_argument('--fade-in', help='淡入时长 (毫秒)')
    trim_parser.add_argument('--fade-out', help='淡出时长 (毫秒)')
    trim_parser.add_argument('--bitrate', help='输出比特率 (如 "192k")')
    
    # 合并命令
    merge_parser = subparsers.add_parser('merge', help='合并多个音频文件')
    merge_parser.add_argument('output_file', help='输出音频文件路径')
    merge_parser.add_argument('input_files', nargs='+', help='输入音频文件路径列表')
    merge_parser.add_argument('--crossfade', type=int, default=0, help='交叉淡变时长 (毫秒)')
    merge_parser.add_argument('--normalize', action='store_true', help='标准化音量')
    merge_parser.add_argument('--fade-in', help='淡入时长 (毫秒)')
    merge_parser.add_argument('--fade-out', help='淡出时长 (毫秒)')
    merge_parser.add_argument('--bitrate', help='输出比特率 (如 "192k")')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 1
    
    # 根据子命令执行相应的操作
    if args.command == 'trim':
        success = process_audio(args)
    elif args.command == 'merge':
        success = merge_mode(args)
    else:
        parser.print_help()
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
