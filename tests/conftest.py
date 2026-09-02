"""pytest 配置：自动添加项目根到 sys.path，确保模块可导入。"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))