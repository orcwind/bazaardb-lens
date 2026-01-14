"""
Python语法自动修复器 - 专治AI生成的垃圾代码
"""
import sys
import re
import ast
import traceback
import os
import shutil
from typing import List, Tuple


class PythonSyntaxFixer:
    """修复Python语法错误的终极工具"""
    
    def __init__(self):
        self.fixes_applied = []
    
    def fix_file(self, filename):
        """修复文件中的所有语法错误"""
        print(f"🔧 正在修复: {filename}")
        
        # 备份原文件
        backup = filename + '.backup'
        try:
            shutil.copy2(filename, backup)
            print(f"📦 已创建备份: {backup}")
        except Exception as e:
            print(f"⚠️  备份失败: {e}")
        
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        
        # 多次尝试修复，直到语法正确
        for attempt in range(1, 6):
            print(f"  尝试第 {attempt} 次修复...")
            
            try:
                # 尝试解析代码
                ast.parse(content)
                print(f"✅ 语法验证通过！")
                break
            except SyntaxError as e:
                print(f"❌ 发现语法错误: {e}")
                content = self._apply_fix(content, e)
                continue
            except Exception as e:
                print(f"⚠️  其他错误: {e}")
                content = self._apply_common_fixes(content)
                continue
        
        # 写回文件
        if content != original_content:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # 验证最终结果
        try:
            ast.parse(content)
            print("🎉 修复成功！")
            if self.fixes_applied:
                print("📝 应用的修复:")
                for fix in self.fixes_applied:
                    print(f"   • {fix}")
            return True
        except SyntaxError as e:
            print(f"😞 最终验证失败: {e}")
            print(f"   错误位置: 第{e.lineno}行, 第{e.offset}列")
            print(f"   错误信息: {e.msg}")
            # 恢复备份
            try:
                shutil.copy2(backup, filename)
                print("已恢复原文件")
            except Exception:
                pass
            return False
    
    def _apply_fix(self, content, error):
        """根据具体错误应用修复"""
        lines = content.split('\n')
        line_no = error.lineno or 0
        col_no = error.offset or 0
        
        print(f"  错误位置: 第{line_no}行, 第{col_no}列")
        print(f"  错误信息: {error.msg}")
        
        # 获取错误行及其上下文
        start = max(0, line_no - 3)
        end = min(len(lines), line_no + 2)
        
        print("  错误上下文:")
        for i in range(start, end):
            prefix = '>>>' if i == line_no - 1 else '   '
            print(f"  {prefix} {i+1:4}: {lines[i]}")
        
        # 根据错误类型应用不同的修复策略
        error_msg_lower = error.msg.lower()
        
        if 'except' in error_msg_lower and 'try' in error_msg_lower:
            return self._fix_try_except(content, line_no, col_no)
        elif 'expected an indented block' in error_msg_lower:
            return self._fix_missing_indent(content, line_no)
        elif 'unexpected indent' in error_msg_lower:
            return self._fix_unexpected_indent(content, line_no)
        elif 'invalid syntax' in error_msg_lower:
            return self._fix_invalid_syntax(content, line_no, col_no)
        elif 'expected' in error_msg_lower:
            return self._fix_expected(content, line_no, col_no, error.msg)
        else:
            return self._fix_generic(content, line_no)
    
    def _fix_try_except(self, content, line_no, col_no):
        """修复try/except语法错误"""
        lines = content.split('\n')
        
        # 找到错误的行（行号从1开始）
        if line_no > len(lines):
            return content
        
        error_line = lines[line_no - 1]
        
        print(f"  修复try/except错误: {error_line}")
        
        # 常见情况1: 孤立的except语句
        if re.match(r'^\s*except', error_line):
            # 在前面添加一个try块
            indent = len(error_line) - len(error_line.lstrip())
            indent_str = ' ' * indent
            
            # 检查前面是否有try
            has_try = False
            for i in range(max(0, line_no - 10), line_no - 1):
                prev_line = lines[i].strip()
                if prev_line.startswith('try:'):
                    has_try = True
                    break
            
            if not has_try:
                # 在except前面插入try:
                lines.insert(line_no - 1, indent_str + 'try:')
                lines.insert(line_no, indent_str + '    pass')  # 添加pass语句
                
                self.fixes_applied.append(f"在第{line_no}行的except前添加了try块")
        
        # 常见情况2: try后面没有正确的内容
        elif 'try:' in error_line:
            # 确保try后面有内容
            if line_no < len(lines):
                next_line = lines[line_no]
                if not next_line.strip() or next_line.lstrip().startswith(('except', 'finally')):
                    # 在try后面添加pass
                    indent = len(error_line) - len(error_line.lstrip())
                    indent_str = ' ' * (indent + 4)
                    lines.insert(line_no, indent_str + 'pass')
                    
                    self.fixes_applied.append(f"在第{line_no}行的try后添加了pass")
        
        return '\n'.join(lines)
    
    def _fix_missing_indent(self, content, line_no):
        """修复缺少缩进的问题"""
        lines = content.split('\n')
        
        # 找到需要缩进的行
        if line_no <= len(lines) and line_no > 1:
            # 检查前一行是否以冒号结尾
            prev_line = lines[line_no - 2]
            
            if prev_line.rstrip().endswith(':') and not prev_line.strip().startswith('#'):
                # 这是一个需要缩进的代码块
                indent = len(prev_line) - len(prev_line.lstrip())
                current_line = lines[line_no - 1]
                
                # 添加缩进（4个空格）
                new_indent = ' ' * (indent + 4)
                if not current_line.startswith(new_indent) and current_line.strip():
                    lines[line_no - 1] = new_indent + current_line.lstrip()
                    
                    self.fixes_applied.append(f"修复第{line_no}行的缩进")
        
        return '\n'.join(lines)
    
    def _fix_unexpected_indent(self, content, line_no):
        """修复意外的缩进"""
        lines = content.split('\n')
        
        if line_no <= len(lines):
            error_line = lines[line_no - 1]
            
            # 检查前一行
            if line_no > 1:
                prev_line = lines[line_no - 2]
                
                # 如果前一行不是结构开始（不以冒号结尾），当前行不应该有缩进
                if not prev_line.rstrip().endswith(':'):
                    # 移除多余的缩进
                    lines[line_no - 1] = error_line.lstrip()
                    self.fixes_applied.append(f"移除第{line_no}行多余的缩进")
        
        return '\n'.join(lines)
    
    def _fix_invalid_syntax(self, content, line_no, col_no):
        """修复无效语法"""
        lines = content.split('\n')
        
        if line_no > len(lines):
            return content
        
        error_line = lines[line_no - 1]
        
        print(f"  修复无效语法: {error_line}")
        
        # 常见情况1: 孤立的except语句（如你的错误）
        if 'except' in error_line and 'try:' not in error_line:
            # 检查前面是否有try
            has_try = False
            for i in range(max(0, line_no - 10), line_no - 1):
                prev_line = lines[i].strip()
                if prev_line.startswith('try:'):
                    has_try = True
                    break
            
            if not has_try:
                # 将这一行注释掉或添加try块
                indent = len(error_line) - len(error_line.lstrip())
                indent_str = ' ' * indent
                lines[line_no - 1] = indent_str + 'try:'
                lines.insert(line_no, indent_str + '    pass')
                lines.insert(line_no + 1, error_line)
                self.fixes_applied.append(f"为孤立except添加try块")
        
        # 常见情况2: 多余的冒号
        elif error_line.strip().endswith(':') and not any(
            error_line.strip().startswith(kw) for kw in 
            ['def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ']
        ):
            # 移除多余的冒号
            lines[line_no - 1] = error_line.rstrip(':')
            self.fixes_applied.append(f"移除第{line_no}行多余的冒号")
        
        # 常见情况3: 不完整的if/for/while语句
        elif any(keyword in error_line for keyword in ['if ', 'for ', 'while ']) and ':' not in error_line:
            # 添加冒号
            lines[line_no - 1] = error_line.rstrip() + ':'
            self.fixes_applied.append(f"在第{line_no}行添加冒号")
        
        return '\n'.join(lines)
    
    def _fix_expected(self, content, line_no, col_no, error_msg):
        """修复期望的语法元素"""
        lines = content.split('\n')
        
        if line_no > len(lines):
            return content
        
        error_line = lines[line_no - 1]
        
        # 检查是否缺少冒号
        if 'expected' in error_msg.lower() and ':' in error_msg.lower():
            # 检查是否是控制结构但缺少冒号
            if any(keyword in error_line for keyword in ['if ', 'elif ', 'else', 'for ', 'while ', 'def ', 'class ', 'try:', 'except', 'finally']):
                if not error_line.rstrip().endswith(':'):
                    lines[line_no - 1] = error_line.rstrip() + ':'
                    self.fixes_applied.append(f"在第{line_no}行添加冒号")
        
        return '\n'.join(lines)
    
    def _fix_generic(self, content, line_no):
        """通用修复方法"""
        # 先尝试应用常见修复
        content = self._apply_common_fixes(content)
        return content
    
    def _apply_common_fixes(self, content):
        """应用常见的通用修复"""
        lines = content.split('\n')
        fixed = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 修复1: 孤立的except语句
            if re.match(r'^\s*except\s+.*?:', line) and i > 0:
                # 检查前面是否有try
                has_try = False
                for j in range(max(0, i - 10), i):
                    prev_line = lines[j].strip()
                    if prev_line.startswith('try:'):
                        has_try = True
                        break
                
                if not has_try:
                    print(f"  发现孤立except在第{i+1}行，正在修复...")
                    # 在前面添加try块
                    indent = len(line) - len(line.lstrip())
                    indent_str = ' ' * indent
                    fixed.append(indent_str + 'try:')
                    fixed.append(indent_str + '    pass')
                    self.fixes_applied.append(f"为孤立except添加try块")
            
            # 修复2: 函数/类定义后面没有内容
            elif re.match(r'^\s*(def|class)\s+\w+.*?:', line) and i + 1 < len(lines):
                next_line = lines[i+1]
                if not next_line.strip() or (
                    next_line.lstrip().startswith('def') or 
                    next_line.lstrip().startswith('class') or
                    next_line.lstrip().startswith('@')
                ):
                    # 添加pass语句
                    indent = len(line) - len(line.lstrip())
                    indent_str = ' ' * (indent + 4)
                    fixed.append(line)
                    fixed.append(indent_str + 'pass')
                    i += 1
                    self.fixes_applied.append(f"为函数/类定义添加pass")
                    continue
            
            # 修复3: 冒号后缺少代码块
            elif line.rstrip().endswith(':') and not line.strip().startswith('#'):
                if i + 1 < len(lines):
                    next_line = lines[i+1]
                    # 检查下一行是否缩进正确
                    current_indent = len(line) - len(line.lstrip())
                    expected_indent = current_indent + 4
                    
                    if next_line.strip() and not next_line.lstrip().startswith(('except', 'finally', 'elif', 'else', '#')):
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent <= current_indent:
                            # 插入pass语句
                            indent_str = ' ' * expected_indent
                            fixed.append(line)
                            fixed.append(indent_str + 'pass')
                            i += 1
                            self.fixes_applied.append(f"为第{i+1}行的结构添加pass")
                            continue
            
            fixed.append(line)
            i += 1
        
        return '\n'.join(fixed)


def fix_all_python_files(directory='.'):
    """修复目录下所有Python文件"""
    fixer = PythonSyntaxFixer()
    fixed_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk(directory):
        # 跳过一些目录
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'venv', 'env', '.venv']]
        
        for file in files:
            if file.endswith('.py') and not file.endswith('.backup'):
                filepath = os.path.join(root, file)
                print("\n" + "="*60)
                if fixer.fix_file(filepath):
                    fixed_count += 1
                else:
                    error_count += 1
    
    print("\n" + "="*60)
    print("📊 修复统计:")
    print(f"  ✅ 成功: {fixed_count} 个文件")
    print(f"  ❌ 失败: {error_count} 个文件")
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Python语法自动修复器 - 专治AI生成的垃圾代码',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 修复单个文件
  python syntax_fixer.py myfile.py
  
  # 修复当前目录下所有Python文件
  python syntax_fixer.py . --all
  
  # 修复指定目录
  python syntax_fixer.py /path/to/project --all
        """
    )
    
    parser.add_argument('path', nargs='?', default='.', help='文件或目录路径')
    parser.add_argument('--all', action='store_true', help='修复目录下所有Python文件')
    
    args = parser.parse_args()
    
    if args.all:
        fix_all_python_files(args.path)
    else:
        path = os.path.abspath(args.path)
        if os.path.isfile(path) and path.endswith('.py'):
            fixer = PythonSyntaxFixer()
            fixer.fix_file(path)
        elif os.path.isdir(path):
            print("请使用 --all 参数来修复目录下的所有文件")
            print("或指定具体的Python文件路径")
        else:
            print(f"❌ 路径不存在或无效: {path}")
