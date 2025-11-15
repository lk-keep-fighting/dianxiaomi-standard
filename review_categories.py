#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分类审核工具 - 用于查看和处理AI标记的不合理分类和处理异常
"""

import csv
import os
import datetime
from typing import List, Dict

def list_review_files():
    """列出所有待审核的CSV文件"""
    csv_files = {
        'categories': [],
        'exceptions': []
    }
    
    for file in os.listdir('.'):
        if file.startswith('unreasonable_categories_') and file.endswith('.csv'):
            csv_files['categories'].append(file)
        elif file.startswith('processing_exceptions_') and file.endswith('.csv'):
            csv_files['exceptions'].append(file)
    
    # 按日期倒序排列
    csv_files['categories'].sort(reverse=True)
    csv_files['exceptions'].sort(reverse=True)
    
    return csv_files

def load_csv_data(filename: str) -> List[Dict]:
    """加载CSV文件数据"""
    data = []
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return []

def display_product_info(product: Dict, index: int):
    """显示产品信息"""
    print(f"\n{'='*60}")
    print(f"📦 商品 {index + 1}")
    print(f"{'='*60}")
    print(f"🕐 时间: {product.get('时间', 'N/A')}")
    print(f"📝 标题: {product.get('商品标题', 'N/A')}")
    print(f"🔗 链接: {product.get('商品链接', 'N/A')[:80]}...")
    print(f"📂 当前分类: {product.get('当前分类', 'N/A')}")
    print(f"🤖 AI建议: {product.get('AI建议分类', 'N/A')}")
    print(f"📊 AI分析: {product.get('AI分析原因', 'N/A')}")
    print(f"✅ 状态: {product.get('处理状态', 'N/A')}")

def update_product_status(filename: str, index: int, new_status: str):
    """更新产品处理状态"""
    try:
        # 读取所有数据
        data = load_csv_data(filename)
        if 0 <= index < len(data):
            data[index]['处理状态'] = new_status
            
            # 写回文件
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['时间', '商品链接', '商品标题', '当前分类', 'AI分析原因', 'AI建议分类', '处理状态']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            print(f"✅ 已更新状态为: {new_status}")
            return True
        else:
            print("❌ 索引超出范围")
            return False
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        return False

def interactive_review(filename: str):
    """交互式审核模式"""
    data = load_csv_data(filename)
    if not data:
        print("❌ 没有数据可审核")
        return
    
    print(f"\n🎯 开始审核文件: {filename}")
    print(f"📊 总计 {len(data)} 个待审核商品")
    
    current_index = 0
    
    while current_index < len(data):
        product = data[current_index]
        
        # 跳过已处理的商品
        if product.get('处理状态') not in ['待处理', '']:
            current_index += 1
            continue
        
        display_product_info(product, current_index)
        
        print(f"\n🤔 操作选项:")
        print("  [A] 接受AI建议并标记为'已采用AI建议'")
        print("  [R] 拒绝AI建议并标记为'保持原分类'")
        print("  [M] 标记为'需要人工修改'")
        print("  [S] 跳过此商品")
        print("  [N] 下一个商品")
        print("  [P] 上一个商品")
        print("  [Q] 退出审核")
        
        choice = input("\n请选择操作 [A/R/M/S/N/P/Q]: ").strip().upper()
        
        if choice == 'A':
            update_product_status(filename, current_index, '已采用AI建议')
            current_index += 1
        elif choice == 'R':
            update_product_status(filename, current_index, '保持原分类')
            current_index += 1
        elif choice == 'M':
            update_product_status(filename, current_index, '需要人工修改')
            current_index += 1
        elif choice == 'S':
            update_product_status(filename, current_index, '已跳过')
            current_index += 1
        elif choice == 'N':
            current_index += 1
        elif choice == 'P':
            current_index = max(0, current_index - 1)
        elif choice == 'Q':
            break
        else:
            print("❌ 无效选择，请重新输入")
    
    print(f"\n✅ 审核完成! 文件: {filename}")

def show_statistics(filename: str):
    """显示统计信息"""
    data = load_csv_data(filename)
    if not data:
        return
    
    status_count = {}
    for product in data:
        status = product.get('处理状态', '待处理')
        status_count[status] = status_count.get(status, 0) + 1
    
    print(f"\n📊 文件统计: {filename}")
    print(f"{'='*40}")
    print(f"📦 总商品数: {len(data)}")
    for status, count in status_count.items():
        print(f"   {status}: {count} 个")
    print(f"{'='*40}")

def main():
    """主函数"""
    print("🔍 分类审核工具")
    print("="*50)
    
    # 列出所有审核文件
    csv_files = list_review_files()
    
    if not csv_files:
        print("❌ 未找到待审核文件")
        print("💡 请先运行主程序生成审核文件")
        return
    
    print("📁 发现以下审核文件:")
    for i, filename in enumerate(csv_files):
        file_size = os.path.getsize(filename)
        print(f"  {i+1}. {filename} ({file_size} bytes)")
    
    while True:
        print(f"\n🎯 操作选项:")
        print("  [数字] 选择文件进行审核")
        print("  [S] 显示所有文件统计")
        print("  [Q] 退出")
        
        choice = input("请选择操作: ").strip()
        
        if choice.upper() == 'Q':
            break
        elif choice.upper() == 'S':
            for filename in csv_files:
                show_statistics(filename)
        elif choice.isdigit():
            file_index = int(choice) - 1
            if 0 <= file_index < len(csv_files):
                filename = csv_files[file_index]
                
                print(f"\n选择的文件: {filename}")
                show_statistics(filename)
                
                action = input("开始审核此文件? [Y/N]: ").strip().upper()
                if action == 'Y':
                    interactive_review(filename)
            else:
                print("❌ 无效的文件编号")
        else:
            print("❌ 无效选择")

if __name__ == "__main__":
    main()