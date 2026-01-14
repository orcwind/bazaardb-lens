#!/usr/bin/env python3
"""
强制重新缩进Python文件 - 无视所有现有缩进，从头开始
"""
import sys
import re
import ast
import shutil
from io import StringIO


class ForceReindenter:
    """强制重新缩进整个文件"""
    
    def __init__(self, indent_size=4):
        self.indent_size = indent_size
        self.indent_char = ' ' * indent_size
    
    def process_file(self, filename):
        """处理文件"""
        print(f"🔨 强制重写缩进: {filename}")
        
        # 备份
        backup = filename + '.backup'
        try:
            shutil.copy2(filename, backup)
            print(f"📦 已备份到: {backup}")
        except Exception as e:
            print(f"⚠️  备份失败: {e}")
        
        # 读取原始内容
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 先尝试简单修复
        fixed = self._simple_fix(content)
        
        # 如果简单修复失败，使用暴力方法
        try:
            ast.parse(fixed)
            print("✅ 简单修复成功")
            result = fixed
        except SyntaxError as e:
            print(f"⚠️  简单修复失败: {e}")
            print("💥 使用暴力重写方法...")
            result = self._brute_force_rewrite(content)
        
        # 写回文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(result)
        
        # 验证结果
        try:
            ast.parse(result)
            print("🎉 语法验证通过！")
            return True
        except SyntaxError as e:
            print(f"😞 最终验证失败: {e}")
            print("恢复备份...")
            try:
                shutil.copy2(backup, filename)
            except Exception:
                pass
            return False
    
    def _simple_fix(self, content):
        """简单修复：只做绝对安全的操作"""
        lines = content.split('\n')
        fixed_lines = []
        
        # 记录函数/类定义的状态
        block_stack = []  # 记录块开始的关键字和缩进级别
        
        for i, line in enumerate(lines):
            original_line = line
            stripped = line.strip()
            
            # 跳过空行和注释（保持原样）
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue
            
            # 检查是否是块开始
            is_block_start = False
            block_keyword = None
            
            # 匹配各种块开始
            patterns = [
                (r'^class\s+\w+', 'class'),
                (r'^def\s+\w+', 'def'),
                (r'^if\s+', 'if'),
                (r'^elif\s+', 'elif'),
                (r'^else\s*:', 'else'),
                (r'^for\s+', 'for'),
                (r'^while\s+', 'while'),
                (r'^try\s*:', 'try'),
                (r'^except\s+', 'except'),
                (r'^finally\s*:', 'finally'),
                (r'^with\s+', 'with'),
                (r'^async\s+def\s+\w+', 'async def'),
                (r'^async\s+for\s+', 'async for'),
                (r'^async\s+with\s+', 'async with'),
            ]
            
            for pattern, keyword in patterns:
                if re.match(pattern, stripped):
                    is_block_start = True
                    block_keyword = keyword
                    break
            
            # 处理减少缩进的关键字
            if block_keyword in ['elif', 'else', 'except', 'finally']:
                # 减少一级缩进（与对应的if/try对齐）
                while block_stack:
                    last_keyword = block_stack[-1][0]
                    if last_keyword in ['if', 'try']:
                        # 保持相同缩进级别
                        break
                    else:
                        # 弹出栈
                        block_stack.pop()
            
            # 计算正确的缩进
            indent_level = len(block_stack)
            indent = self.indent_char * indent_level
            
            # 构建修复后的行
            if is_block_start:
                fixed_line = indent + stripped
                
                # 检查是否有冒号（应该有）
                if ':' not in stripped:
                    fixed_line += ':'
                
                # 添加到块栈
                block_stack.append((block_keyword, indent_level))
            else:
                # 普通行：使用当前缩进级别
                fixed_line = indent + stripped
            
            fixed_lines.append(fixed_line)
            
            # 检查是否是块结束
            # 某些关键字可能结束一个块（return, break, continue, pass, raise）
            end_keywords = ['return', 'break', 'continue', 'pass', 'raise']
            if any(stripped.startswith(kw) for kw in end_keywords):
                # 检查下一行是否减少缩进
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    next_stripped = next_line.strip()
                    
                    if next_stripped:
                        # 检查下一行是否是块开始关键字
                        is_next_block_start = any(
                            re.match(pattern, next_stripped) for pattern, _ in patterns
                        )
                        
                        # 如果下一行是块开始，可能需要调整
                        if is_next_block_start:
                            # 检查是否是elif/else/except/finally
                            if any(next_stripped.startswith(kw) for kw in ['elif', 'else', 'except', 'finally']):
                                # 这些关键字应该与对应的if/try对齐，不需要弹出
                                pass
                            else:
                                # 其他块开始，可能需要弹出当前块
                                # 但这里不弹出，让下一行处理
                                pass
        
        return '\n'.join(fixed_lines)
    
    def _brute_force_rewrite(self, content):
        """暴力重写：完全忽略原有缩进，基于语法重写"""
        print("💣 执行暴力重写...")
        
        # 先尝试用tokenize解析
        try:
            import tokenize
            from io import BytesIO
            
            # 将内容转换为token流
            tokens = list(tokenize.tokenize(BytesIO(content.encode('utf-8')).readline))
            
            # 重新构建代码
            output = []
            indent_level = 0
            last_was_newline = False
            
            for tok in tokens:
                if tok.type == tokenize.INDENT:
                    indent_level += 1
                elif tok.type == tokenize.DEDENT:
                    indent_level -= 1
                elif tok.type == tokenize.NL:
                    if not last_was_newline:
                        output.append('\n')
                        last_was_newline = True
                elif tok.type == tokenize.NEWLINE:
                    output.append('\n')
                    output.append(' ' * (self.indent_size * indent_level))
                    last_was_newline = True
                elif tok.type == tokenize.ENCODING:
                    continue
                else:
                    if last_was_newline and tok.type != tokenize.INDENT:
                        output.append(' ' * (self.indent_size * indent_level))
                    output.append(tok.string)
                    last_was_newline = False
            
            result = ''.join(output)
            return result
            
        except Exception as e:
            print(f"Tokenize失败: {e}")
            # 使用最后的手段：基于冒号重写
        
        # 最后的手段：基于冒号和关键字重写
        lines = content.split('\n')
        result_lines = []
        indent_level = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                result_lines.append(stripped if stripped.startswith('#') else '')
                continue
            
            # 检查是否减少缩进
            dedent_keywords = ['else:', 'elif', 'except', 'finally:', 'return', 'break', 'continue', 'pass']
            starts_with_dedent = any(stripped.startswith(kw) for kw in dedent_keywords)
            
            if starts_with_dedent and indent_level > 0:
                # 检查是否是elif/else/except/finally（应该与if/try对齐）
                if any(stripped.startswith(kw) for kw in ['elif', 'else:', 'except', 'finally:']):
                    # 这些关键字应该与对应的if/try对齐，减少一级
                    indent_level = max(0, indent_level - 1)
                else:
                    # 其他关键字，减少一级
                    indent_level = max(0, indent_level - 1)
            
            # 添加缩进
            indented_line = ' ' * (self.indent_size * indent_level) + stripped
            result_lines.append(indented_line)
            
            # 检查是否增加缩进（以冒号结尾但不是字典/切片）
            if stripped.endswith(':') and not stripped.startswith(('"', "'", '#', '[')):
                # 跳过一些特殊情况
                if not any(stripped.startswith(kw) for kw in ['lambda', 'dict(', 'slice(']):
                    indent_level += 1
        
        return '\n'.join(result_lines)
    
    def _create_minimal_valid_script(self, content):
        """创建最小有效脚本：删除所有有问题的代码"""
        print("⚠️  创建最小有效脚本...")
        
        lines = content.split('\n')
        valid_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 跳过明显有问题的行
            if stripped.startswith('except ') and 'try:' not in '\n'.join(lines[max(0, i-10):i]):
                # 孤立的except
                print(f"  删除孤立except: 第{i+1}行")
                continue
            
            if stripped == 'else:' and 'if ' not in '\n'.join(lines[max(0, i-10):i]):
                # 孤立的else
                print(f"  删除孤立else: 第{i+1}行")
                continue
            
            if stripped == 'finally:' and 'try:' not in '\n'.join(lines[max(0, i-10):i]):
                # 孤立的finally
                print(f"  删除孤立finally: 第{i+1}行")
                continue
            
            # 保留其他行
            valid_lines.append(line)
        
        result = '\n'.join(valid_lines)
        
        # 最后确保所有结构都有内容
        result = re.sub(
            r'(try:|def .*?:|class .*?:|if .*?:|for .*?:|while .*?:)\s*\n\s*(?!(?:except|#|elif|else))', 
            r'\1\n    pass\n', 
            result
        )
        
        return result


def main():
    if len(sys.argv) < 2:
        print("使用方法: python force_reindent.py <文件名>")
        print("示例: python force_reindent.py Bazaar_Lens.py")
        return
    
    filename = sys.argv[1]
    
    # 检查文件是否存在
    import os
    if not os.path.exists(filename):
        print(f"错误: 文件不存在 {filename}")
        return
    
    # 创建修复器
    fixer = ForceReindenter(indent_size=4)
    
    # 尝试修复
    success = fixer.process_file(filename)
    
    if success:
        print("\n✅ 修复完成！")
        print("请运行修复后的文件进行测试:")
        print(f"  python {filename}")
    else:
        print("\n😞 修复失败")
        print("尝试使用最小有效脚本方法...")
        
        # 读取备份
        backup = filename + '.backup'
        try:
            with open(backup, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 创建最小有效脚本
            minimal = fixer._create_minimal_valid_script(content)
            
            # 保存为新文件
            new_filename = filename.replace('.py', '_minimal.py')
            with open(new_filename, 'w', encoding='utf-8') as f:
                f.write(minimal)
            
            print(f"📄 已创建最小有效脚本: {new_filename}")
            print("请检查此文件，并逐步添加回被删除的代码")
        except Exception as e:
            print(f"创建最小脚本失败: {e}")


if __name__ == "__main__":
    main()
