"""
测试格式化器的示例文件（包含各种缩进问题）
这个文件故意包含各种缩进错误，用于测试格式化器
"""

# 测试1: Tab缩进
def test_tab_indent():
    if True:
        return "Tab缩进"

        # 测试2: 混合缩进
        def test_mixed_indent():
            if True:
                return "混合缩进"  # Tab和空格混合
                pass

                # 测试3: 冒号后缺少代码块
                def test_missing_block():
                    if True:
                        return "缺少代码块"

                        # 测试4: 缩进不一致
                        def test_inconsistent():
                            if True:
                                for i in range(10):
                                    if i > 5:
                                        return i  # 缩进错误

                                        # 测试5: try/except缩进问题
                                        def test_try_except():
                                            try:
                                                process()
                                            except:
                                            pass

                                            # 测试6: 嵌套结构
                                            def test_nested():
                                                if condition:
                                                    for item in items:
                                                        try:
                                                            result = process(item)
                                                        except:
                                                        return None

                                                        # 测试7: 类定义
                                                        class TestClass:
                                                            def method(self):
                                                                return "缩进错误"
