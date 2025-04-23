#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识库生成工具启动脚本

这是一个简单的入口点脚本，用于启动知识库生成工具
"""

import sys
import os
from pathlib import Path

# 添加gen-target目录到系统路径
gen_target_dir = Path(__file__).parent / "gen-target"
sys.path.insert(0, str(gen_target_dir.absolute()))

# 导入并运行主程序
def main():
    # 将命令行参数传递给主模块
    import runpy
    runpy.run_path(str(gen_target_dir / "__main__.py"), run_name="__main__")

if __name__ == "__main__":
    main()
