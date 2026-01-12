#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
提取Chromium/Electron PAK文件中的简体中文语言包内容
"""

import struct
import sys
import json

def read_uint16(data, offset):
    """读取16位无符号整数（小端序）"""
    return struct.unpack('<H', data[offset:offset+2])[0]

def read_uint32(data, offset):
    """读取32位无符号整数（小端序）"""
    return struct.unpack('<I', data[offset:offset+4])[0]

def read_uint8(data, offset):
    """读取8位无符号整数"""
    return data[offset]

def extract_pak_v2(pak_file_path, output_file=None):
    """
    提取PAK文件中的内容（改进版）
    """
    try:
        with open(pak_file_path, 'rb') as f:
            data = f.read()
        
        print(f"文件大小: {len(data)} 字节\n")
        
        if len(data) < 8:
            print("文件太小，不是有效的PAK文件")
            return None
        
        # 读取文件头
        version = read_uint32(data, 0)
        encoding = read_uint32(data, 4)  # 0=BINARY, 1=UTF8, 2=UTF16
        
        print(f"版本号: {version}")
        print(f"编码类型: {encoding} (0=BINARY, 1=UTF8, 2=UTF16)")
        
        results = {
            'file_path': pak_file_path,
            'file_size': len(data),
            'version': version,
            'encoding': encoding,
            'resources': []
        }
        
        offset = 8
        
        # 尝试解析资源表
        if version == 5:  # 可能是版本5格式
            # 读取资源数量（可能是2字节）
            if offset + 2 <= len(data):
                resource_count = read_uint16(data, offset)
                print(f"资源数量: {resource_count}")
                offset += 2
                
                # 读取资源ID和偏移量
                resources = []
                for i in range(min(resource_count, 10000)):  # 限制最大数量
                    if offset + 4 > len(data):
                        break
                    resource_id = read_uint16(data, offset)
                    resource_offset = read_uint32(data, offset + 2)
                    offset += 6
                    
                    if resource_offset < len(data):
                        resources.append({
                            'id': resource_id,
                            'offset': resource_offset
                        })
                
                print(f"解析到 {len(resources)} 个资源项")
                
                # 提取每个资源的字符串
                extracted_strings = []
                for i, res in enumerate(resources):
                    if i >= 1000:  # 限制处理数量
                        break
                    try:
                        # 尝试从偏移量读取字符串
                        str_offset = res['offset']
                        if str_offset < len(data):
                            # 根据编码类型读取
                            if encoding == 2:  # UTF-16
                                string = extract_utf16_string_at_offset(data, str_offset)
                            elif encoding == 1:  # UTF-8
                                string = extract_utf8_string_at_offset(data, str_offset)
                            else:
                                string = extract_binary_string_at_offset(data, str_offset)
                            
                            if string and len(string.strip()) > 0:
                                extracted_strings.append({
                                    'id': res['id'],
                                    'offset': res['offset'],
                                    'text': string
                                })
                    except:
                        continue
                
                results['resources'] = extracted_strings
                print(f"\n成功提取 {len(extracted_strings)} 个字符串资源")
        
        # 如果上面的方法不行，尝试直接搜索中文字符串
        print("\n=== 直接搜索中文字符串 ===")
        chinese_strings = extract_chinese_strings_direct(data)
        if chinese_strings:
            results['chinese_strings'] = chinese_strings
            print(f"找到 {len(chinese_strings)} 个中文字符串")
            for i, s in enumerate(chinese_strings[:20], 1):
                print(f"{i:3d}. {s}")
            if len(chinese_strings) > 20:
                print(f"... 还有 {len(chinese_strings) - 20} 个")
        
        # 保存结果
        if output_file:
            # 清理数据，移除无法序列化的字符
            clean_results = clean_for_json(results)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(clean_results, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {output_file}")
            
            # 同时生成一个易读的文本文件
            txt_file = output_file.replace('.json', '.txt')
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(f"简体中文语言包提取结果\n")
                f.write(f"{'='*50}\n\n")
                f.write(f"文件: {pak_file_path}\n")
                f.write(f"文件大小: {len(data)} 字节\n")
                f.write(f"版本: {version}\n")
                f.write(f"编码: {encoding} (1=UTF8)\n\n")
                
                if 'chinese_strings' in results and results['chinese_strings']:
                    f.write(f"提取的中文字符串 ({len(results['chinese_strings'])} 个):\n")
                    f.write(f"{'-'*50}\n\n")
                    for i, s in enumerate(results['chinese_strings'], 1):
                        f.write(f"{i:4d}. {s}\n")
            
            print(f"文本格式结果已保存到: {txt_file}")
        
        return results
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_utf16_string_at_offset(data, offset):
    """从指定偏移量提取UTF-16字符串"""
    if offset >= len(data) - 1:
        return None
    
    chars = []
    i = offset
    while i < len(data) - 1:
        char_code = read_uint16(data, i)
        if char_code == 0:  # 字符串结束
            break
        try:
            chars.append(chr(char_code))
            i += 2
        except:
            break
        if len(chars) > 1000:  # 防止过长
            break
    
    return ''.join(chars) if chars else None

def extract_utf8_string_at_offset(data, offset):
    """从指定偏移量提取UTF-8字符串"""
    if offset >= len(data):
        return None
    
    chars = []
    i = offset
    while i < len(data):
        byte = data[i]
        if byte == 0:  # 字符串结束
            break
        chars.append(byte)
        i += 1
        if len(chars) > 1000:
            break
    
    try:
        return bytes(chars).decode('utf-8', errors='ignore')
    except:
        return None

def extract_binary_string_at_offset(data, offset):
    """从指定偏移量提取二进制字符串"""
    return extract_utf8_string_at_offset(data, offset)

def extract_chinese_strings_direct(data):
    """直接搜索文件中的中文字符串（UTF-8编码）"""
    chinese_strings = []
    
    # 尝试将整个文件解码为UTF-8
    try:
        # 分段解码，避免遇到无效字节
        text_parts = []
        i = 0
        while i < len(data):
            try:
                # 尝试解码一段数据
                chunk = data[i:i+1000]
                decoded = chunk.decode('utf-8', errors='strict')
                text_parts.append(decoded)
                i += 1000
            except UnicodeDecodeError:
                # 如果解码失败，尝试找到下一个有效字符
                try:
                    # 跳过无效字节，尝试从下一个位置开始
                    for j in range(i, min(i+10, len(data))):
                        try:
                            chunk = data[j:j+100]
                            decoded = chunk.decode('utf-8', errors='strict')
                            text_parts.append(decoded)
                            i = j + 100
                            break
                        except:
                            continue
                    else:
                        i += 1
                except:
                    i += 1
            if i >= len(data):
                break
    except:
        # 如果整体解码失败，使用错误忽略模式
        try:
            text = data.decode('utf-8', errors='ignore')
            text_parts = [text]
        except:
            return []
    
    # 合并所有文本部分
    full_text = ''.join(text_parts) if text_parts else ''
    
    # 使用正则表达式提取中文字符串
    import re
    # 匹配包含中文的字符串（至少2个字符，包含至少1个中文字符）
    pattern = r'[\u4e00-\u9fff][\u4e00-\u9fff\w\s，。！？、；：""''（）【】《》·\\-—…]*[\u4e00-\u9fff]|[\u4e00-\u9fff]{2,}'
    matches = re.findall(pattern, full_text)
    
    # 去重并过滤
    seen = set()
    for match in matches:
        cleaned = match.strip()
        if cleaned and len(cleaned) >= 2:
            # 确保包含中文字符
            if any('\u4e00' <= c <= '\u9fff' for c in cleaned):
                if cleaned not in seen:
                    chinese_strings.append(cleaned)
                    seen.add(cleaned)
    
    return chinese_strings

def extract_string_from_pos(data, start_pos):
    """从指定位置提取字符串（UTF-8编码）"""
    if start_pos >= len(data):
        return None
    
    try:
        # 尝试从当前位置解码UTF-8字符串
        i = start_pos
        bytes_list = []
        
        while i < len(data):
            byte = data[i]
            if byte == 0:  # 字符串结束符
                break
            
            bytes_list.append(byte)
            i += 1
            
            # 尝试解码当前字节序列
            try:
                decoded = bytes(bytes_list).decode('utf-8', errors='strict')
                # 如果成功解码，继续
                if len(bytes_list) > 200:  # 限制长度
                    break
            except UnicodeDecodeError:
                # 如果解码失败，可能是多字节字符的一部分，继续读取
                if len(bytes_list) > 4:  # UTF-8最多4字节
                    # 回退一个字节，尝试解码
                    bytes_list.pop()
                    i -= 1
                    try:
                        decoded = bytes(bytes_list).decode('utf-8', errors='strict')
                        break
                    except:
                        return None
                continue
        
        if bytes_list:
            try:
                result = bytes(bytes_list).decode('utf-8', errors='ignore')
                return result.strip() if result.strip() else None
            except:
                return None
    except:
        return None
    
    return None

def clean_for_json(obj):
    """清理对象，移除无法JSON序列化的字符"""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, str):
        # 移除代理对字符
        try:
            return obj.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')
        except:
            return obj.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    else:
        return obj

if __name__ == '__main__':
    pak_file = 'data/pak/zh-CN.pak'
    output_file = 'data/pak/zh-CN_extracted.json'
    
    if len(sys.argv) > 1:
        pak_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    print(f"正在提取简体中文语言包: {pak_file}\n")
    result = extract_pak_v2(pak_file, output_file)
    
    if result:
        total_strings = 0
        if 'resources' in result:
            total_strings += len(result['resources'])
        if 'chinese_strings' in result:
            total_strings += len(result['chinese_strings'])
        print(f"\n提取完成！共找到 {total_strings} 个字符串")
        if output_file:
            print(f"详细结果已保存到: {output_file}")
