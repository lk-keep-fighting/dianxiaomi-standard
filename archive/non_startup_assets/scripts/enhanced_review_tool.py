#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版审核工具 - 用于查看和处理AI标记的不合理分类和处理异常
"""

import csv
import os
import datetime
from typing import List, Dict, Tuple

class EnhancedReviewTool:
    """增强版审核工具"""
    
    def __init__(self):
        self.current_dir = os.getcwd()
    
    def list_all_files(self) -> Dict[str, List[str]]:
        """列出所有相关的CSV文件"""
        files = {
            'categories': [],
            'exceptions': []
        }
        
        for file in os.listdir(self.current_dir):
            if file.startswith('unreasonable_categories_') and file.endswith('.csv'):
                files['categories'].append(file)
            elif file.startswith('processing_exceptions_') and file.endswith('.csv'):
                files['exceptions'].append(file)
        
        # 按日期倒序排列
        files['categories'].sort(reverse=True)
        files['exceptions'].sort(reverse=True)
        
        return files
    
    def load_csv_data(self, filename: str) -> List[Dict]:
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
    
    def display_category_product(self, product: Dict, index: int):
        """显示分类审核商品信息"""
        print(f"\n{'='*60}")
        print(f"📦 分类审核商品 {index + 1}")
        print(f"{'='*60}")
        print(f"🕐 时间: {product.get('时间', 'N/A')}")
        print(f"📝 标题: {product.get('商品标题', 'N/A')}")
        print(f"🔗 链接: {product.get('商品链接', 'N/A')[:80]}...")
        print(f"📂 当前分类: {product.get('当前分类', 'N/A')}")
        print(f"🤖 AI建议: {product.get('AI建议分类', 'N/A')}")
        print(f"📊 AI分析: {product.get('AI分析原因', 'N/A')}")
        print(f"✅ 状态: {product.get('处理状态', 'N/A')}")
    
    def display_exception_record(self, exception: Dict, index: int):
        """显示异常记录信息"""
        print(f"\n{'='*60}")
        print(f"🚨 异常记录 {index + 1}")
        print(f"{'='*60}")
        print(f"🕐 时间: {exception.get('时间', 'N/A')}")
        print(f"📝 标题: {exception.get('商品标题', 'N/A')}")
        print(f"🔗 链接: {exception.get('商品链接', 'N/A')[:80]}...")
        print(f"📂 当前分类: {exception.get('当前分类', 'N/A')}")
        print(f"🔧 操作步骤: {exception.get('操作步骤', 'N/A')}")
        print(f"⚠️ 异常类型: {exception.get('异常类型', 'N/A')}")
        print(f"📄 错误信息: {exception.get('错误信息', 'N/A')}")
        print(f"✅ 状态: {exception.get('处理状态', 'N/A')}")
        print(f"📝 备注: {exception.get('备注', 'N/A')}")
    
    def update_record_status(self, filename: str, index: int, new_status: str, note: str = ""):
        """更新记录状态"""
        try:
            data = self.load_csv_data(filename)
            if 0 <= index < len(data):
                data[index]['处理状态'] = new_status
                if note and '备注' in data[index]:
                    data[index]['备注'] = note
                
                # 根据文件类型确定字段名
                if 'unreasonable_categories_' in filename:
                    fieldnames = ['时间', '商品链接', '商品标题', '当前分类', 'AI分析原因', 'AI建议分类', '处理状态']
                else:  # exceptions file
                    fieldnames = ['时间', '商品链接', '商品标题', '当前分类', '操作步骤', '异常类型', '错误信息', '处理状态', '备注']
                
                # 写回文件
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
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
    
    def interactive_category_review(self, filename: str):
        """交互式分类审核模式"""
        data = self.load_csv_data(filename)
        if not data:
            print("❌ 没有数据可审核")
            return
        
        print(f"\n🎯 开始分类审核: {filename}")
        print(f"📊 总计 {len(data)} 个待审核商品")
        
        current_index = 0
        
        while current_index < len(data):
            product = data[current_index]
            
            # 跳过已处理的商品
            if product.get('处理状态') not in ['待处理', '']:
                current_index += 1
                continue
            
            self.display_category_product(product, current_index)
            
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
                self.update_record_status(filename, current_index, '已采用AI建议')
                current_index += 1
            elif choice == 'R':
                self.update_record_status(filename, current_index, '保持原分类')
                current_index += 1
            elif choice == 'M':
                self.update_record_status(filename, current_index, '需要人工修改')
                current_index += 1
            elif choice == 'S':
                self.update_record_status(filename, current_index, '已跳过')
                current_index += 1
            elif choice == 'N':
                current_index += 1
            elif choice == 'P':
                current_index = max(0, current_index - 1)
            elif choice == 'Q':
                break
            else:
                print("❌ 无效选择，请重新输入")
        
        print(f"\n✅ 分类审核完成! 文件: {filename}")
    
    def interactive_exception_review(self, filename: str):
        """交互式异常审核模式"""
        data = self.load_csv_data(filename)
        if not data:
            print("❌ 没有数据可审核")
            return
        
        print(f"\n🎯 开始异常审核: {filename}")
        print(f"📊 总计 {len(data)} 个异常记录")
        
        current_index = 0
        
        while current_index < len(data):
            exception = data[current_index]
            
            # 跳过已处理的异常
            if exception.get('处理状态') not in ['待分析', '']:
                current_index += 1
                continue
            
            self.display_exception_record(exception, current_index)
            
            print(f"\n🔧 操作选项:")
            print("  [F] 标记为'已修复'")
            print("  [K] 标记为'已知问题'")
            print("  [I] 标记为'需要忽略'")
            print("  [U] 标记为'待进一步分析'")
            print("  [C] 添加备注")
            print("  [N] 下一个记录")
            print("  [P] 上一个记录")
            print("  [Q] 退出审核")
            
            choice = input("\n请选择操作 [F/K/I/U/C/N/P/Q]: ").strip().upper()
            
            if choice == 'F':
                note = input("请输入修复备注 (可选): ").strip()
                self.update_record_status(filename, current_index, '已修复', note)
                current_index += 1
            elif choice == 'K':
                note = input("请输入问题描述: ").strip()
                self.update_record_status(filename, current_index, '已知问题', note)
                current_index += 1
            elif choice == 'I':
                note = input("请输入忽略原因: ").strip()
                self.update_record_status(filename, current_index, '需要忽略', note)
                current_index += 1
            elif choice == 'U':
                note = input("请输入分析要求: ").strip()
                self.update_record_status(filename, current_index, '待进一步分析', note)
                current_index += 1
            elif choice == 'C':
                note = input("请输入备注: ").strip()
                self.update_record_status(filename, current_index, exception.get('处理状态', '待分析'), note)
            elif choice == 'N':
                current_index += 1
            elif choice == 'P':
                current_index = max(0, current_index - 1)
            elif choice == 'Q':
                break
            else:
                print("❌ 无效选择，请重新输入")
        
        print(f"\n✅ 异常审核完成! 文件: {filename}")
    
    def show_file_statistics(self, filename: str):
        """显示文件统计信息"""
        data = self.load_csv_data(filename)
        if not data:
            return
        
        status_count = {}
        for record in data:
            status = record.get('处理状态', '待处理' if 'unreasonable_categories_' in filename else '待分析')
            status_count[status] = status_count.get(status, 0) + 1
        
        file_type = "分类审核" if 'unreasonable_categories_' in filename else "异常记录"
        print(f"\n📊 {file_type}文件统计: {filename}")
        print(f"{'='*50}")
        print(f"📦 总记录数: {len(data)}")
        for status, count in status_count.items():
            print(f"   {status}: {count} 个")
        print(f"{'='*50}")
    
    def run(self):
        """运行主程序"""
        print("🔍 增强版审核工具")
        print("支持分类审核和异常分析")
        print("="*60)
        
        files = self.list_all_files()
        
        if not files['categories'] and not files['exceptions']:
            print("❌ 未找到任何审核文件")
            print("💡 请先运行主程序生成审核文件")
            return
        
        while True:
            print(f"\n📁 发现的文件:")
            
            all_files = []
            
            if files['categories']:
                print("📝 分类审核文件:")
                for i, filename in enumerate(files['categories']):
                    file_size = os.path.getsize(filename)
                    print(f"  {len(all_files)+1}. {filename} ({file_size} bytes)")
                    all_files.append(('category', filename))
            
            if files['exceptions']:
                print("🚨 异常记录文件:")
                for i, filename in enumerate(files['exceptions']):
                    file_size = os.path.getsize(filename)
                    print(f"  {len(all_files)+1}. {filename} ({file_size} bytes)")
                    all_files.append(('exception', filename))
            
            print(f"\n🎯 操作选项:")
            print("  [数字] 选择文件进行审核")
            print("  [S] 显示所有文件统计")
            print("  [Q] 退出")
            
            choice = input("请选择操作: ").strip()
            
            if choice.upper() == 'Q':
                break
            elif choice.upper() == 'S':
                for file_type, filename in all_files:
                    self.show_file_statistics(filename)
            elif choice.isdigit():
                file_index = int(choice) - 1
                if 0 <= file_index < len(all_files):
                    file_type, filename = all_files[file_index]
                    
                    print(f"\n选择的文件: {filename}")
                    self.show_file_statistics(filename)
                    
                    action = input("开始审核此文件? [Y/N]: ").strip().upper()
                    if action == 'Y':
                        if file_type == 'category':
                            self.interactive_category_review(filename)
                        else:  # exception
                            self.interactive_exception_review(filename)
                else:
                    print("❌ 无效的文件编号")
            else:
                print("❌ 无效选择")

def main():
    """主函数"""
    tool = EnhancedReviewTool()
    tool.run()

if __name__ == "__main__":
    main()