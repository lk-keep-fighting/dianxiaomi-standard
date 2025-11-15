#!/usr/bin/env python3
"""
项目清理脚本 - 安全地清理项目文件

作者: Linus Torvalds (风格)
设计原则: Safety First, Good Taste, No Data Loss
"""

import os
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from analyze_files import ProjectAnalyzer


class ProjectCleaner:
    """项目清理器"""
    
    def __init__(self, project_root: str, dry_run: bool = True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.backup_dir = self.project_root / "backup" / f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def safe_delete(self, file_path: Path) -> bool:
        """安全删除文件"""
        try:
            if self.dry_run:
                print(f"  [DRY RUN] 会删除: {file_path}")
                return True
            
            if file_path.exists():
                file_path.unlink()
                print(f"  ✅ 已删除: {file_path}")
                return True
            else:
                print(f"  ⚠️ 文件不存在: {file_path}")
                return False
        except Exception as e:
            print(f"  ❌ 删除失败 {file_path}: {e}")
            return False
    
    def safe_delete_directory(self, dir_path: Path) -> bool:
        """安全删除目录"""
        try:
            if self.dry_run:
                print(f"  [DRY RUN] 会删除目录: {dir_path}")
                return True
            
            if dir_path.exists() and dir_path.is_dir():
                shutil.rmtree(dir_path)
                print(f"  ✅ 已删除目录: {dir_path}")
                return True
            else:
                print(f"  ⚠️ 目录不存在: {dir_path}")
                return False
        except Exception as e:
            print(f"  ❌ 删除目录失败 {dir_path}: {e}")
            return False
    
    def archive_file(self, file_path: Path, archive_subdir: str) -> bool:
        """归档文件到备份目录"""
        try:
            if self.dry_run:
                print(f"  [DRY RUN] 会归档: {file_path} -> archive/{archive_subdir}/")
                return True
            
            # 创建归档目录
            archive_path = self.project_root / "archive" / archive_subdir
            archive_path.mkdir(parents=True, exist_ok=True)
            
            # 移动文件
            target_path = archive_path / file_path.name
            shutil.move(str(file_path), str(target_path))
            print(f"  ✅ 已归档: {file_path} -> {target_path}")
            return True
        except Exception as e:
            print(f"  ❌ 归档失败 {file_path}: {e}")
            return False
    
    def cleanup_project(self) -> dict:
        """执行项目清理"""
        print("🧹 开始项目清理...")
        if self.dry_run:
            print("🔍 这是预演模式 (DRY RUN)，不会真正删除文件")
        else:
            print("⚠️  这是实际执行模式，会真正删除文件！")
        
        # 分析文件
        analyzer = ProjectAnalyzer(self.project_root)
        analysis = analyzer.analyze()
        cleanup_plan = analyzer.generate_cleanup_plan(analysis)
        
        results = {
            'deleted_files': 0,
            'archived_files': 0,
            'failed_operations': 0
        }
        
        # 1. 删除整个分发目录
        print("\\n🗑️ 删除分发副本目录...")
        dist_dir = self.project_root / "digital_chief_automation_dist"
        if self.safe_delete_directory(dist_dir):
            results['deleted_files'] += len(analysis['distribution_copy'])
        
        # 2. 删除过时的表单填充文件
        print("\\n🗑️ 删除过时的表单填充文件...")
        for file_path in analysis['obsolete_form_files']:
            if self.safe_delete(self.project_root / file_path):
                results['deleted_files'] += 1
            else:
                results['failed_operations'] += 1
        
        # 3. 删除临时和调试文件  
        print("\\n🧹 删除临时和调试文件...")
        for file_path in analysis['temp_files']:
            if self.safe_delete(self.project_root / file_path):
                results['deleted_files'] += 1
            else:
                results['failed_operations'] += 1
        
        # 4. 删除冗余文档
        print("\\n📄 删除冗余文档...")
        for file_path in analysis['redundant_docs']:
            if self.safe_delete(self.project_root / file_path):
                results['deleted_files'] += 1
            else:
                results['failed_operations'] += 1
        
        # 5. 归档过时的主程序
        print("\\n🗄️ 归档过时的主程序...")
        for file_path in analysis['obsolete_main_files']:
            if self.archive_file(self.project_root / file_path, "obsolete_main"):
                results['archived_files'] += 1
            else:
                results['failed_operations'] += 1
        
        # 6. 删除Python缓存文件
        print("\\n🧹 清理Python缓存文件...")
        cache_dirs = list(self.project_root.rglob('__pycache__'))
        for cache_dir in cache_dirs:
            if self.safe_delete_directory(cache_dir):
                results['deleted_files'] += 1
        
        # 7. 删除pytest缓存
        pytest_cache = self.project_root / ".pytest_cache"
        if pytest_cache.exists():
            if self.safe_delete_directory(pytest_cache):
                results['deleted_files'] += 1
        
        return results
    
    def create_new_structure(self) -> bool:
        """创建新的项目结构"""
        print("\\n📁 创建新的项目结构...")
        
        try:
            # 创建核心目录
            directories = [
                "core",           # 核心功能代码
                "config",         # 配置文件
                "tools",          # 工具脚本  
                "docs",           # 文档
                "archive",        # 归档文件
                "logs"            # 日志文件
            ]
            
            for dir_name in directories:
                dir_path = self.project_root / dir_name
                if self.dry_run:
                    print(f"  [DRY RUN] 会创建目录: {dir_path}")
                else:
                    dir_path.mkdir(exist_ok=True)
                    print(f"  ✅ 已创建目录: {dir_path}")
            
            return True
        except Exception as e:
            print(f"  ❌ 创建目录结构失败: {e}")
            return False
    
    def move_core_files(self) -> bool:
        """移动核心文件到新的结构"""
        if self.dry_run:
            print("\\n🔄 [DRY RUN] 会重新组织核心文件...")
            return True
        
        print("\\n🔄 重新组织核心文件...")
        
        try:
            # 移动核心Python文件到core目录
            core_files = [
                'src/product_data.py',
                'src/amazon_product_parser.py', 
                'src/unified_form_filler.py',
                'src/main_refactored.py',
                'src/system_config.py'
            ]
            
            core_dir = self.project_root / "core"
            for file_path in core_files:
                src_path = self.project_root / file_path
                if src_path.exists():
                    target_path = core_dir / src_path.name
                    shutil.move(str(src_path), str(target_path))
                    print(f"  ✅ 移动: {src_path} -> {target_path}")
            
            # 移动工具脚本到tools目录
            tool_files = [
                'install_dependencies.sh',
                'run.sh', 
                'test_refactored_system.py'
            ]
            
            tools_dir = self.project_root / "tools"
            for file_path in tool_files:
                src_path = self.project_root / file_path
                if src_path.exists():
                    target_path = tools_dir / src_path.name
                    shutil.move(str(src_path), str(target_path))
                    print(f"  ✅ 移动: {src_path} -> {target_path}")
            
            # 移动配置文件
            config_files = [
                'src/form-json-schema.json'
            ]
            
            config_dir = self.project_root / "config"
            for file_path in config_files:
                src_path = self.project_root / file_path
                if src_path.exists():
                    target_path = config_dir / src_path.name
                    shutil.move(str(src_path), str(target_path))
                    print(f"  ✅ 移动: {src_path} -> {target_path}")
            
            # 移动文档到docs目录
            docs_dir = self.project_root / "docs"
            important_docs = ['README.md', 'WARP.md']
            for doc_file in important_docs:
                src_path = self.project_root / doc_file
                if src_path.exists():
                    target_path = docs_dir / src_path.name
                    shutil.move(str(src_path), str(target_path))
                    print(f"  ✅ 移动: {src_path} -> {target_path}")
            
            return True
        except Exception as e:
            print(f"  ❌ 移动文件失败: {e}")
            return False
    
    def print_summary(self, results: dict) -> None:
        """打印清理摘要"""
        print("\\n" + "="*60)
        print("📊 清理完成摘要:")
        print(f"   🗑️ 删除文件数: {results['deleted_files']}")
        print(f"   🗄️ 归档文件数: {results['archived_files']}")
        print(f"   ❌ 失败操作数: {results['failed_operations']}")
        
        if not self.dry_run:
            print("\\n✅ 项目清理完成！")
            print("\\n🚀 下一步:")
            print("   1. 检查archive/目录中的归档文件")
            print("   2. 运行测试确认系统正常: python tools/test_refactored_system.py")
            print("   3. 运行主程序: python core/main_refactored.py")
        else:
            print("\\n🔍 预演完成！如要实际执行:")
            print("   python cleanup_project.py --execute")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='清理项目文件')
    parser.add_argument('--execute', action='store_true', 
                       help='实际执行清理（默认为预演模式）')
    parser.add_argument('--restructure', action='store_true',
                       help='重新组织项目结构')
    
    args = parser.parse_args()
    
    # 创建清理器
    cleaner = ProjectCleaner('.', dry_run=not args.execute)
    
    try:
        # 执行清理
        results = cleaner.cleanup_project()
        
        # 如果需要重新组织结构
        if args.restructure:
            cleaner.create_new_structure()
            cleaner.move_core_files()
        
        # 打印摘要
        cleaner.print_summary(results)
        
    except KeyboardInterrupt:
        print("\\n🛑 清理被用户中断")
    except Exception as e:
        print(f"\\n❌ 清理过程中发生错误: {e}")


if __name__ == "__main__":
    main()
