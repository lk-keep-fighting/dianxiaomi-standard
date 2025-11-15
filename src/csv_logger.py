#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV日志工具 - 用于记录分类审核和处理异常
"""

import os
import csv
import datetime
from typing import Optional


class CSVLogger:
    """CSV日志记录器"""
    
    def __init__(self, base_path: Optional[str] = None):
        """
        初始化CSV日志记录器
        
        Args:
            base_path: CSV文件保存的基础路径，默认为当前工作目录
        """
        self.base_path = base_path or os.getcwd()
    
    def write_unreasonable_category(self, product_url: str, title: str, current_category: str, 
                                  ai_reason: str, suggested_category: Optional[str] = None) -> Optional[str]:
        """
        将分类不合理的商品信息写入CSV文件，供后续人工处理
        
        Args:
            product_url: 商品链接
            title: 商品标题 
            current_category: 当前分类
            ai_reason: AI分析原因
            suggested_category: AI建议分类
            
        Returns:
            CSV文件路径，失败时返回None
        """
        # 创建CSV文件路径
        csv_filename = f"unreasonable_categories_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
        csv_path = os.path.join(self.base_path, csv_filename)
        
        # 检查文件是否存在，如果不存在则创建并写入表头
        file_exists = os.path.exists(csv_path)
        
        try:
            with open(csv_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['时间', '商品链接', '商品标题', '当前分类', 'AI分析原因', 'AI建议分类', '处理状态']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # 如果是新文件，写入表头
                if not file_exists:
                    writer.writeheader()
                    print(f"✅ 创建分类审核文件: {csv_filename}")
                
                # 写入数据行
                writer.writerow({
                    '时间': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '商品链接': product_url,
                    '商品标题': title[:100] + '...' if len(title) > 100 else title,  # 限制标题长度
                    '当前分类': current_category,
                    'AI分析原因': ai_reason[:200] + '...' if len(ai_reason) > 200 else ai_reason,  # 限制原因长度
                    'AI建议分类': suggested_category or '无建议',
                    '处理状态': '待处理'
                })
                
            print(f"📝 已记录待处理商品到文件: {csv_filename}")
            return csv_path
            
        except Exception as e:
            print(f"⚠️ 写入分类审核CSV文件失败: {e}")
            return None
    
    def write_processing_exception(self, product_url: str, title: str, current_category: str,
                                 exception_type: str, error_message: str, 
                                 operation_step: str = "未知步骤") -> Optional[str]:
        """
        将处理异常信息写入CSV文件，供后续排查和处理
        
        Args:
            product_url: 商品链接
            title: 商品标题
            current_category: 当前分类  
            exception_type: 异常类型
            error_message: 错误信息
            operation_step: 出错的操作步骤
            
        Returns:
            CSV文件路径，失败时返回None
        """
        # 创建CSV文件路径
        csv_filename = f"processing_exceptions_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
        csv_path = os.path.join(self.base_path, csv_filename)
        
        # 检查文件是否存在，如果不存在则创建并写入表头
        file_exists = os.path.exists(csv_path)
        
        try:
            with open(csv_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['时间', '商品链接', '商品标题', '当前分类', '操作步骤', '异常类型', '错误信息', '处理状态', '备注']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # 如果是新文件，写入表头
                if not file_exists:
                    writer.writeheader()
                    print(f"🚨 创建异常记录文件: {csv_filename}")
                
                # 写入数据行
                writer.writerow({
                    '时间': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '商品链接': product_url,
                    '商品标题': title[:100] + '...' if len(title) > 100 else title,  # 限制标题长度
                    '当前分类': current_category,
                    '操作步骤': operation_step,
                    '异常类型': exception_type,
                    '错误信息': error_message[:300] + '...' if len(error_message) > 300 else error_message,  # 限制错误信息长度
                    '处理状态': '待分析',
                    '备注': ''
                })
                
            print(f"🚨 已记录处理异常到文件: {csv_filename}")
            return csv_path
            
        except Exception as e:
            print(f"⚠️ 写入异常记录CSV文件失败: {e}")
            return None
    
    def get_daily_stats(self, date_str: Optional[str] = None) -> dict:
        """
        获取指定日期的统计信息
        
        Args:
            date_str: 日期字符串 (YYYYMMDD)，默认为今天
            
        Returns:
            包含统计信息的字典
        """
        if not date_str:
            date_str = datetime.datetime.now().strftime('%Y%m%d')
        
        stats = {
            'date': date_str,
            'unreasonable_categories': 0,
            'processing_exceptions': 0,
            'files': []
        }
        
        # 检查分类审核文件
        category_file = f"unreasonable_categories_{date_str}.csv"
        category_path = os.path.join(self.base_path, category_file)
        if os.path.exists(category_path):
            try:
                with open(category_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    stats['unreasonable_categories'] = sum(1 for row in reader) - 1  # 减去表头
                    stats['files'].append(category_file)
            except Exception as e:
                print(f"⚠️ 读取分类审核文件失败: {e}")
        
        # 检查异常记录文件
        exception_file = f"processing_exceptions_{date_str}.csv"
        exception_path = os.path.join(self.base_path, exception_file)
        if os.path.exists(exception_path):
            try:
                with open(exception_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    stats['processing_exceptions'] = sum(1 for row in reader) - 1  # 减去表头
                    stats['files'].append(exception_file)
            except Exception as e:
                print(f"⚠️ 读取异常记录文件失败: {e}")
        
        return stats
    
    def print_daily_summary(self, date_str: Optional[str] = None):
        """
        打印指定日期的汇总信息
        
        Args:
            date_str: 日期字符串 (YYYYMMDD)，默认为今天
        """
        stats = self.get_daily_stats(date_str)
        
        print(f"\n📊 日期 {stats['date']} 汇总")
        print(f"{'='*50}")
        print(f"📝 分类审核记录: {stats['unreasonable_categories']} 条")
        print(f"🚨 处理异常记录: {stats['processing_exceptions']} 条")
        
        if stats['files']:
            print(f"📁 生成的文件:")
            for file in stats['files']:
                file_path = os.path.join(self.base_path, file)
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                print(f"   • {file} ({file_size} bytes)")
        else:
            print("✅ 今日无记录文件生成")
        print(f"{'='*50}")


# 全局实例，方便直接使用
csv_logger = CSVLogger()

# 兼容性函数，保持向后兼容
def write_unreasonable_category_to_csv(product_url: str, title: str, current_category: str, 
                                     ai_reason: str, suggested_category: Optional[str] = None) -> Optional[str]:
    """
    兼容性函数：将分类不合理的商品信息写入CSV文件
    """
    return csv_logger.write_unreasonable_category(
        product_url, title, current_category, ai_reason, suggested_category
    )

def write_processing_exception_to_csv(product_url: str, title: str, current_category: str,
                                    exception_type: str, error_message: str, 
                                    operation_step: str = "未知步骤") -> Optional[str]:
    """
    便捷函数：将处理异常信息写入CSV文件
    """
    return csv_logger.write_processing_exception(
        product_url, title, current_category, exception_type, error_message, operation_step
    )


# 使用示例
if __name__ == "__main__":
    # 创建日志记录器
    logger = CSVLogger()
    
    # 测试分类审核记录
    logger.write_unreasonable_category(
        product_url="https://www.amazon.com/test-product",
        title="测试产品标题",
        current_category="错误分类",
        ai_reason="AI分析这个分类不合理的原因",
        suggested_category="建议的正确分类"
    )
    
    # 测试异常记录
    logger.write_processing_exception(
        product_url="https://www.amazon.com/error-product", 
        title="出错的产品",
        current_category="某个分类",
        exception_type="ElementNotFoundError",
        error_message="无法找到指定的页面元素",
        operation_step="填充表单"
    )
    
    # 打印今日汇总
    logger.print_daily_summary()