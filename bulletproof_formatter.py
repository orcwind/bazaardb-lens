"""
坚不可摧的Python代码格式化器
无视任何语法错误，强制修复缩进问题
"""
import re
import sys
import os
import shutil
from typing import List, Tuple, Optional


class IndentFixer:
    """无视语法错误的缩进修复器"""
    
    def __init__(self, spaces_per_indent=4):
        self.spaces = ' ' * spaces_per_indent
        self.spaces_per_indent = spaces_per_indent
        
    def fix_file(self, filepath: str) -> str:
        """修复单个文件，返回修复后的内容"""
        print(f"🔧 修复文件: {os.path.basename(filepath)}")
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"⚠️  读取文件失败: {e}")
            return ""
        
        # 修复1: 统一换行符
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 修复2: 替换所有制表符为空格
        content = content.replace('\t', self.spaces)
        
        # 修复3: 按行处理，忽略语法
        lines = content.split('\n')
        fixed_lines = self._fix_lines(lines)
        
        # 重新组合
        result = '\n'.join(fixed_lines)
        
        # 最后修复：确保所有冒号后有正确缩进
        result = self._post_fix_colons(result)
        
        return result
    
    def _fix_lines(self, lines: List[str]) -> List[str]:
        """修复所有行的缩进"""
        fixed_lines = []
        indent_stack = [0]  # 缩进栈，存储每层的缩进级别
        
        i = 0
        while i < len(lines):
            line = lines[i]
            next_line = lines[i + 1] if i + 1 < len(lines) else None
            
            # 移除行尾空格
            line = line.rstrip()
            
            # 跳过空行
            if not line:
                fixed_lines.append('')
                i += 1
                continue
            
            # 处理注释（保持原样，但修复缩进）
            is_comment = line.lstrip().startswith('#')
            
            # 计算当前行的实际缩进（空格数）
            leading_spaces = len(line) - len(line.lstrip())
            
            # 检查是否是结构开始行（以冒号结尾）
            stripped = line.strip()
            is_structure_start = (
                stripped.endswith(':') and 
                not stripped.startswith('#') and
                not any(stripped.startswith(kw) for kw in ['except', 'finally', 'elif', 'else'])
            )
            
            # 检查是否是减少缩进的关键字
            is_dedent_keyword = any(
                stripped.startswith(kw) for kw in 
                ['except', 'elif', 'else', 'finally']
            )
            
            # 确定目标缩进级别
            if is_dedent_keyword:
                # 减少一级缩进
                if len(indent_stack) > 1:
                    indent_stack.pop()
                target_indent = indent_stack[-1]
            else:
                # 使用当前栈顶的缩进级别
                target_indent = indent_stack[-1]
            
            # 修复当前行的缩进
            fixed_line = ' ' * target_indent + line.lstrip()
            fixed_lines.append(fixed_line)
            
            # 如果是结构开始，下一行应该增加缩进
            if is_structure_start:
                next_indent = target_indent + self.spaces_per_indent
                indent_stack.append(next_indent)
            
            i += 1
        
        return fixed_lines
    
    def _post_fix_colons(self, content: str) -> str:
        """后处理：确保所有冒号后有正确缩进的代码块"""
        lines = content.split('\n')
        fixed = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            fixed.append(line)
            
            # 检查是否是结构开始（以冒号结尾）
            stripped = line.strip()
            if stripped and stripped.endswith(':') and not stripped.startswith('#'):
                # 排除特殊关键字
                if not any(stripped.startswith(kw) for kw in ['except', 'finally', 'elif', 'else']):
                    # 查找下一个非空、非注释行
                    j = i + 1
                    while j < len(lines):
                        next_stripped = lines[j].strip()
                        if next_stripped and not next_stripped.startswith('#'):
                            break
                        j += 1
                    
                    if j < len(lines):
                        next_line = lines[j]
                        # 计算当前行的缩进
                        current_indent = len(line) - len(line.lstrip())
                        expected_indent = current_indent + self.spaces_per_indent
                        
                        # 检查下一行的缩进
                        next_indent = len(next_line) - len(next_line.lstrip())
                        next_stripped = next_line.strip()
                        
                        # 如果下一行缩进不正确，且不是特殊关键字，则插入pass
                        if (next_indent <= current_indent and 
                            not any(next_stripped.startswith(kw) for kw in 
                                   ['except', 'finally', 'elif', 'else', 'pass', '#'])):
                            # 在结构开始后添加一个pass语句
                            fixed.append(' ' * expected_indent + 'pass')
            
            i += 1
        
        return '\n'.join(fixed)


def batch_fix_python_files(root_dir: str, backup: bool = True):
    """
    批量修复目录下所有Python文件的缩进问题
    
    Args:
        root_dir: 根目录
        backup: 是否创建备份
    """
    fixer = IndentFixer()
    fixed_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk(root_dir):
        # 跳过一些常见的不需要处理的目录
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'venv', 'env']]
        
        for file in files:
            if file.endswith('.py') and not file.endswith('.bak'):
                filepath = os.path.join(root, file)
                
                # 创建备份
                if backup:
                    backup_path = filepath + '.bak'
                    try:
                        shutil.copy2(filepath, backup_path)
                    except Exception as e:
                        print(f"⚠️  备份失败 {file}: {e}")
                
                try:
                    # 修复文件
                    fixed_content = fixer.fix_file(filepath)
                    
                    if fixed_content:
                        # 写入修复后的内容
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        
                        print(f"✅ 已修复: {file}")
                        fixed_count += 1
                    else:
                        print(f"⚠️  跳过空文件: {file}")
                    
                except Exception as e:
                    print(f"❌ 修复失败 {file}: {e}")
                    error_count += 1
    
    print(f"\n📊 修复统计: 成功 {fixed_count} 个，失败 {error_count} 个")
    return fixed_count, error_count


def install_as_hook():
    """安装为Git预提交钩子"""
    hook_content = '''#!/bin/bash
# Python缩进自动修复钩子
echo "正在自动修复Python缩进问题..."
python bulletproof_formatter.py . --no-backup
git add -u
'''
    
    hook_dir = '.git/hooks'
    if os.path.exists('.git'):
        os.makedirs(hook_dir, exist_ok=True)
        hook_file = os.path.join(hook_dir, 'pre-commit')
        
        try:
            with open(hook_file, 'w', encoding='utf-8') as f:
                f.write(hook_content)
            
            # 在Windows上需要确保可执行
            if os.name == 'nt':
                import stat
                if os.path.exists(hook_file):
                    st = os.stat(hook_file)
                    os.chmod(hook_file, st.st_mode | stat.S_IEXEC)
            
            print("✅ 已安装Git预提交钩子")
            print("   每次提交前会自动修复所有Python文件的缩进问题")
            return True
        except Exception as e:
            print(f"❌ 安装钩子失败: {e}")
            return False
    else:
        print("❌ 当前目录不是Git仓库")
        return False


def fix_single_file(filepath: str, backup: bool = True) -> bool:
    """修复单个文件"""
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        return False
    
    if not filepath.endswith('.py'):
        print(f"⚠️  不是Python文件: {filepath}")
        return False
    
    fixer = IndentFixer()
    
    # 创建备份
    if backup:
        backup_path = filepath + '.bak'
        try:
            shutil.copy2(filepath, backup_path)
            print(f"📦 已创建备份: {backup_path}")
        except Exception as e:
            print(f"⚠️  备份失败: {e}")
    
    try:
        # 修复文件
        fixed_content = fixer.fix_file(filepath)
        
        if fixed_content:
            # 写入修复后的内容
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            print(f"✅ 已修复: {filepath}")
            return True
        else:
            print(f"⚠️  修复后内容为空")
            return False
            
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='坚不可摧的Python代码格式化器 - 无视语法错误，强制修复缩进问题',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 修复单个文件
  python bulletproof_formatter.py myfile.py
  
  # 修复当前目录下所有Python文件
  python bulletproof_formatter.py .
  
  # 修复指定目录，不创建备份
  python bulletproof_formatter.py /path/to/project --no-backup
  
  # 安装为Git预提交钩子
  python bulletproof_formatter.py --install-hook
        """
    )
    
    parser.add_argument(
        'path', 
        nargs='?', 
        default='.', 
        help='要修复的文件或目录路径（默认: 当前目录）'
    )
    parser.add_argument(
        '--install-hook', 
        action='store_true', 
        help='安装为Git预提交钩子'
    )
    parser.add_argument(
        '--no-backup', 
        action='store_true', 
        help='不创建备份文件'
    )
    
    args = parser.parse_args()
    
    if args.install_hook:
        install_as_hook()
    else:
        path = os.path.abspath(args.path)
        
        if os.path.isfile(path) and path.endswith('.py'):
            # 修复单个文件
            fix_single_file(path, backup=not args.no_backup)
        elif os.path.isdir(path):
            # 批量修复目录
            print(f"📁 开始修复目录: {path}")
            print("=" * 60)
            batch_fix_python_files(path, backup=not args.no_backup)
        else:
            print(f"❌ 路径不存在或无效: {path}")
            sys.exit(1)
    
    print("\n🎉 处理完成！")
