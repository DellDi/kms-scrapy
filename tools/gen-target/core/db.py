#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库连接器模块

提供通用的数据库连接和查询功能
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    raise ImportError("请安装pymysql: uv pip install pymysql")

logger = logging.getLogger("gen-target.db")


class MySQLConnector:
    """MySQL数据库连接器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化MySQL连接器
        
        Args:
            config: 数据库配置，包含host, port, user, password, db等
        """
        self.config = config
        self.conn = None
    
    def connect(self) -> bool:
        """
        连接数据库
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.conn = pymysql.connect(
                **self.config,
                cursorclass=DictCursor
            )
            logger.info(f"成功连接到数据库 {self.config['db']}")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def disconnect(self) -> None:
        """断开数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")
    
    def query(self, sql: str, params: Optional[Union[tuple, dict]] = None) -> List[Dict[str, Any]]:
        """
        执行查询
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        if not self.conn:
            if not self.connect():
                return []
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            return []
    
    def execute(self, sql: str, params: Optional[Union[tuple, dict]] = None) -> int:
        """
        执行更新操作
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            int: 影响的行数
        """
        if not self.conn:
            if not self.connect():
                return 0
        
        try:
            with self.conn.cursor() as cursor:
                rows = cursor.execute(sql, params or ())
                self.conn.commit()
                return rows
        except Exception as e:
            logger.error(f"执行失败: {e}")
            self.conn.rollback()
            return 0
