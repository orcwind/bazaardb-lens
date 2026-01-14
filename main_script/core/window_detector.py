"""
游戏窗口检测模块
"""
import win32gui
import win32process
import win32api
import win32con
import psutil
import logging


class WindowDetector:
    """游戏窗口检测器"""

    def __init__(self):
        self.game_hwnd = None
        self.game_rect = None
        self._cache_time = 0  # 缓存时间戳
        self._cache_duration = 1.0  # 缓存有效期（秒）

    def get_game_window(self):
        """获取游戏窗口句柄和位置"""
        import time
        current_time = time.time()
        
        # 如果有缓存且未过期，检查窗口是否仍然有效
        if self.game_hwnd and (current_time - self._cache_time) < self._cache_duration:
            try:
                # 检查窗口是否仍然存在且可见
                if win32gui.IsWindow(self.game_hwnd) and win32gui.IsWindowVisible(self.game_hwnd):
                    if not win32gui.IsIconic(self.game_hwnd):
                        # 更新窗口位置（位置可能变化）
                        rect = win32gui.GetWindowRect(self.game_hwnd)
                        self.game_rect = rect
                        return self.game_hwnd, self.game_rect
            except Exception:
                pass
            # 缓存的窗口无效，清除缓存
            self.game_hwnd = None
            self.game_rect = None
        
        try:
            # 方法1: 通过进程名查找游戏窗口
            hwnd = self._find_window_by_process()
            if hwnd:
                # 检查窗口是否最小化
                if win32gui.IsIconic(hwnd):
                    logging.info("游戏窗口已最小化，跳过")
                    return None, None
                # 检查窗口是否可见
                if not win32gui.IsWindowVisible(hwnd):
                    logging.info("游戏窗口不可见，跳过")
                    return None, None
                rect = win32gui.GetWindowRect(hwnd)
                logging.debug(f"通过进程名找到游戏窗口，坐标: {rect}")
                self.game_hwnd = hwnd
                self.game_rect = rect
                self._cache_time = current_time  # 更新缓存时间
                return hwnd, rect

            # 方法2: 尝试多种可能的游戏窗口名称
            window_names = [
                "The Bazaar",
                "The Bazaar - DirectX 11",
                "The Bazaar - DirectX 12",
                "The Bazaar - Vulkan",
                "The Bazaar - OpenGL"
            ]

            hwnd = None
            found_window_name = None
            for name in window_names:
                hwnd = win32gui.FindWindow(None, name)
                if hwnd:
                    found_window_name = name
                    logging.debug(f"找到游戏窗口: {name}")
                    break

            # 方法3: 通过类名查找
            if not hwnd:
                hwnd = win32gui.FindWindow("UnityWndClass", None)
                if hwnd:
                    found_window_name = "UnityWndClass"
                    logging.debug(f"通过类名找到游戏窗口: UnityWndClass")

            # 方法4: 枚举所有窗口，寻找真正的游戏窗口（排除编辑器等）
            if not hwnd:
                # 排除的关键词（这些不是游戏窗口）
                exclude_keywords = [
                    '.py', '.txt', '.db', 'Cursor', '编辑器', 'Editor',
                    'IDE', 'VSCode', 'PyCharm', 'bazaardb-desktop',
                    'Administrator', 'price_database', '服务器管理'
                ]
                
                def enum_windows_callback(hwnd_test, windows):
                    if win32gui.IsWindowVisible(hwnd_test):
                        window_text = win32gui.GetWindowText(hwnd_test)
                        window_text_lower = window_text.lower()
                        
                        # 检查是否包含排除关键词
                        is_excluded = any(
                            keyword.lower() in window_text_lower 
                            for keyword in exclude_keywords
                        )
                        
                        # 只接受真正的游戏窗口名称
                        is_game_window = (
                            "the bazaar" in window_text_lower and
                            not is_excluded
                        )
                        
                        if is_game_window:
                            rect = win32gui.GetWindowRect(hwnd_test)
                            width = rect[2] - rect[0]
                            height = rect[3] - rect[1]
                            windows.append(
                                (hwnd_test, window_text, rect, width, height))
                            logging.debug(
                                f"找到候选游戏窗口: {window_text}, 尺寸: {width}x{height}, 坐标: {rect}")
                    return True

                windows = []
                win32gui.EnumWindows(enum_windows_callback, windows)

                # 记录所有找到的窗口用于调试
                if windows:
                    logging.info(f"找到的所有游戏窗口候选:")
                    for h, t, r, w, h_val in windows:
                        logging.info(f"  - {t}: {w}x{h_val} at {r}")

                # 过滤出尺寸合理的窗口（游戏窗口应该比较大）
                valid_windows = [
                    (h, t, r, w, h_val) for h, t, r, w, h_val in windows
                    if w > 800 and h_val > 600
                ]

                if valid_windows:
                    # 选择最大的窗口
                    valid_windows.sort(key=lambda x: x[3] * x[4], reverse=True)
                    hwnd = valid_windows[0][0]
                    found_window_name = valid_windows[0][1]
                    logging.info(
                        f"通过枚举找到游戏窗口: {found_window_name}, "
                        f"尺寸: {valid_windows[0][3]}x{valid_windows[0][4]}")
                elif windows:
                    # 如果没有尺寸合理的窗口，选择最大的
                    windows.sort(key=lambda x: x[3] * x[4], reverse=True)
                    hwnd = windows[0][0]
                    found_window_name = windows[0][1]
                    logging.warning(
                        f"使用最大窗口作为备选: {found_window_name}, "
                        f"尺寸: {windows[0][3]}x{windows[0][4]}")

            if hwnd:
                try:
                    # 使用AttachThreadInput方法处理SetForegroundWindow错误
                    foreground_hwnd = win32gui.GetForegroundWindow()
                    foreground_thread_id = win32process.GetWindowThreadProcessId(
                        foreground_hwnd)[0]
                    current_thread_id = win32api.GetCurrentThreadId()

                    # 将线程输入关联起来
                    if foreground_thread_id != current_thread_id:
                        win32process.AttachThreadInput(
                            foreground_thread_id, current_thread_id, True)
                        win32gui.SetForegroundWindow(hwnd)
                        win32process.AttachThreadInput(
                            foreground_thread_id, current_thread_id, False)
                    else:
                        win32gui.SetForegroundWindow(hwnd)
                except Exception as e:
                    # 如果设置前台窗口失败，记录错误但继续
                    logging.warning(f"设置游戏窗口为前台失败: {e}")
                    pass

                rect = win32gui.GetWindowRect(hwnd)
                # 检查窗口状态
                is_minimized = win32gui.IsIconic(hwnd)
                is_visible = win32gui.IsWindowVisible(hwnd)
                logging.info(f"找到游戏窗口: {found_window_name}, 坐标: {rect}")
                logging.info(f"窗口状态 - 最小化: {is_minimized}, 可见: {is_visible}")
                
                # 如果窗口最小化或不可见，返回None
                if is_minimized:
                    logging.info("游戏窗口已最小化，跳过")
                    return None, None
                if not is_visible:
                    logging.info("游戏窗口不可见，跳过")
                    return None, None

                # 如果窗口太小，尝试获取客户端区域
                if rect[2] - rect[0] < 200 or rect[3] - rect[1] < 100:
                    try:
                        client_rect = win32gui.GetClientRect(hwnd)
                        client_width = client_rect[2]
                        client_height = client_rect[3]
                        logging.info(
                            f"客户端区域尺寸: {client_width}x{client_height}")

                        if client_width > 800 and client_height > 600:
                            # 使用客户端坐标重新计算窗口坐标
                            point = win32gui.ClientToScreen(hwnd, (0, 0))
                            rect = (
                                point[0],
                                point[1],
                                point[0] + client_width,
                                point[1] + client_height)
                            logging.info(f"使用客户端坐标: {rect}")
                    except Exception as e:
                        logging.warning(f"获取客户端坐标失败: {e}")

                self.game_hwnd = hwnd
                self.game_rect = rect
                self._cache_time = current_time  # 更新缓存时间
                return hwnd, rect

            logging.warning("未找到游戏窗口")
            return None, None
        except Exception as e:
            logging.error(f"获取游戏窗口失败: {e}")
            return None, None

    def _find_window_by_process(self):
        """通过进程名查找游戏窗口"""
        try:
            # 查找 Bazaar_Lens.exe 或 The Bazaar.exe 进程
            process_names = [
                "Bazaar_Lens.exe",
                "The Bazaar.exe",
                "TheBazaar.exe"]

            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.name()
                    if any(name.lower() in proc_name.lower()
                           for name in process_names):
                        pid = proc.pid
                        logging.debug(f"找到游戏进程: {proc_name} (PID: {pid})")

                        # 通过进程ID查找对应的窗口
                        def enum_windows_callback(hwnd, windows):
                            _, found_pid = win32process.GetWindowThreadProcessId(
                                hwnd)
                            if found_pid == pid and win32gui.IsWindowVisible(
                                    hwnd):
                                window_text = win32gui.GetWindowText(hwnd)
                                if window_text:  # 只选择有标题的窗口
                                    rect = win32gui.GetWindowRect(hwnd)
                                    width = rect[2] - rect[0]
                                    height = rect[3] - rect[1]
                                    windows.append(
                                        (hwnd, window_text, rect, width, height))
                            return True

                        windows = []
                        win32gui.EnumWindows(enum_windows_callback, windows)

                        if windows:
                            # 选择最大的窗口
                            windows.sort(
                                key=lambda x: x[3] * x[4], reverse=True)
                            best_window = windows[0]
                            logging.debug(
                                f"通过进程找到窗口: {best_window[1]}, "
                                f"尺寸: {best_window[3]}x{best_window[4]}")
                            return best_window[0]

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return None
        except Exception as e:
            logging.error(f"通过进程查找窗口失败: {e}")
            return None

    def is_cursor_in_icon_area(
            self,
            cursor_x,
            cursor_y,
            entity_type='monster',
            window_rect=None,
            position_config=None):
        """
        检查鼠标是否在图标区域内

        Args:
            cursor_x, cursor_y: 鼠标坐标（屏幕绝对坐标）
            entity_type: 'monster' 或 'item'
            window_rect: 游戏窗口坐标 (left, top, right, bottom)
            position_config: 位置配置字典

        Returns:
            tuple: (是否在区域内, 图标区域的实际坐标) 或 (False, None)
        """
        import traceback
        
        if not position_config:
            return False, None

        if not window_rect or len(window_rect) != 4:
            logging.warning("[区域检测] 窗口坐标无效，无法进行图标区域检测")
            return False, None

        try:
            # position_config是PositionConfig对象，需要访问position_config属性
            config_dict = position_config.position_config if position_config else None
            if not config_dict:
                return None
            icon_data = config_dict.get(entity_type, {}).get('icon', {})
            if not icon_data:
                return False, None

            # 获取参考坐标（从配置文件，这些是记录时的屏幕绝对坐标）
            ref_tl = (icon_data['top_left']['x'], icon_data['top_left']['y'])
            ref_tr = (icon_data['top_right']['x'], icon_data['top_right']['y'])
            ref_bl = (icon_data['bottom_left']['x'], icon_data['bottom_left']['y'])
            ref_br = (icon_data['bottom_right']['x'], icon_data['bottom_right']['y'])

            # 计算参考图标的边界框（使用最小外接矩形）
            ref_min_x = min(ref_tl[0], ref_tr[0], ref_bl[0], ref_br[0])
            ref_max_x = max(ref_tl[0], ref_tr[0], ref_bl[0], ref_br[0])
            ref_min_y = min(ref_tl[1], ref_tr[1], ref_bl[1], ref_br[1])
            ref_max_y = max(ref_tl[1], ref_tr[1], ref_bl[1], ref_br[1])

            # 方法1：直接比较绝对坐标（适用于窗口位置不变的情况）
            # 使用宽裕的容差（扩大20%的范围）
            tolerance_x = (ref_max_x - ref_min_x) * 0.2
            tolerance_y = (ref_max_y - ref_min_y) * 0.2

            # 检查鼠标是否在图标区域内（使用容差）
            if (ref_min_x - tolerance_x <= cursor_x <= ref_max_x + tolerance_x and
                ref_min_y - tolerance_y <= cursor_y <= ref_max_y + tolerance_y):
                # 返回实际图标区域的坐标（使用容差后的范围）
                actual_icon_area = {
                    'min_x': ref_min_x - tolerance_x,
                    'max_x': ref_max_x + tolerance_x,
                    'min_y': ref_min_y - tolerance_y,
                    'max_y': ref_max_y + tolerance_y
                }
                logging.debug(f"[区域检测] 鼠标在图标区域内（绝对坐标匹配）")
                return True, actual_icon_area

            # 方法2：如果绝对坐标不匹配，尝试使用相对位置匹配
            # 扩大容差范围，允许更大的位置变化（扩大到100%的范围）
            expanded_tolerance_x = (ref_max_x - ref_min_x) * 1.0
            expanded_tolerance_y = (ref_max_y - ref_min_y) * 1.0

            # 检查鼠标是否在扩大后的图标区域内
            if (ref_min_x - expanded_tolerance_x <= cursor_x <= ref_max_x + expanded_tolerance_x and
                ref_min_y - expanded_tolerance_y <= cursor_y <= ref_max_y + expanded_tolerance_y):
                # 检查鼠标是否在窗口内
                if (window_rect[0] <= cursor_x <= window_rect[2] and
                    window_rect[1] <= cursor_y <= window_rect[3]):
                    # 返回实际图标区域的坐标（使用扩大容差后的范围）
                    actual_icon_area = {
                        'min_x': ref_min_x - expanded_tolerance_x,
                        'max_x': ref_max_x + expanded_tolerance_x,
                        'min_y': ref_min_y - expanded_tolerance_y,
                        'max_y': ref_max_y + expanded_tolerance_y
                    }
                    logging.info(
                        f"[区域检测] 鼠标在图标区域内（扩大容差匹配，容差: "
                        f"{expanded_tolerance_x:.1f}x{expanded_tolerance_y:.1f}）")
                    return True, actual_icon_area

            return False, None
        except Exception as e:
            logging.error(f"检查鼠标是否在 {entity_type} 图标区域内失败: {e}")
            logging.error(traceback.format_exc())
            return False, None

    def _build_icon_area_from_cursor(
            self,
            cursor_x,
            cursor_y,
            entity_type='monster',
            position_config=None):
        """
        根据鼠标位置构建图标区域

        Args:
            cursor_x, cursor_y: 鼠标坐标（屏幕绝对坐标）
            entity_type: 'monster' 或 'item'
            position_config: 位置配置字典

        Returns:
            dict: 图标区域的实际坐标（包含min_x, max_x, min_y, max_y），或 None
        """
        import traceback
        
        if not position_config:
            return None

        try:
            # position_config是PositionConfig对象，需要访问position_config属性
            config_dict = position_config.position_config if position_config else None
            if not config_dict:
                return None
            icon_data = config_dict.get(entity_type, {}).get('icon', {})
            if not icon_data:
                return None

            # 获取参考坐标（从配置文件）
            ref_tl = (icon_data['top_left']['x'], icon_data['top_left']['y'])
            ref_tr = (icon_data['top_right']['x'], icon_data['top_right']['y'])
            ref_bl = (icon_data['bottom_left']['x'], icon_data['bottom_left']['y'])
            ref_br = (icon_data['bottom_right']['x'], icon_data['bottom_right']['y'])

            # 计算参考图标的尺寸（使用最小外接矩形）
            ref_min_x = min(ref_tl[0], ref_tr[0], ref_bl[0], ref_br[0])
            ref_max_x = max(ref_tl[0], ref_tr[0], ref_bl[0], ref_br[0])
            ref_min_y = min(ref_tl[1], ref_tr[1], ref_bl[1], ref_br[1])
            ref_max_y = max(ref_tl[1], ref_tr[1], ref_bl[1], ref_br[1])

            icon_width = ref_max_x - ref_min_x
            icon_height = ref_max_y - ref_min_y

            # 检查图标尺寸是否有效
            if icon_width <= 0 or icon_height <= 0:
                logging.warning(
                    f"[区域检测] {entity_type} 图标尺寸无效: {icon_width}x{icon_height}，将使用固定小区域")
                return None

            # 假设鼠标位置在图标的左上角附近（偏移图标尺寸的15%）
            offset_factor = 0.15
            icon_tl_x = cursor_x - int(icon_width * offset_factor)
            icon_tl_y = cursor_y - int(icon_height * offset_factor)

            # 构建图标区域（以计算出的左上角为基准）
            icon_area = {
                'min_x': icon_tl_x,
                'max_x': icon_tl_x + icon_width,
                'min_y': icon_tl_y,
                'max_y': icon_tl_y + icon_height
            }

            icon_center_x = (icon_area['min_x'] + icon_area['max_x']) // 2
            icon_center_y = (icon_area['min_y'] + icon_area['max_y']) // 2
            logging.info(
                f"[区域检测] 构建的图标区域({entity_type}): 尺寸={icon_width}x{icon_height}, "
                f"中心=({icon_center_x}, {icon_center_y})")
            return icon_area
        except Exception as e:
            logging.error(f"根据鼠标位置构建图标区域失败: {e}")
            logging.error(traceback.format_exc())
            return None

    def calculate_name_area_from_icon(
            self, icon_area, entity_type='monster', position_config=None):
        """
        根据图标区域计算名称区域

        Args:
            icon_area: 图标区域的实际坐标（dict，包含min_x, max_x, min_y, max_y）
            entity_type: 'monster' 或 'item'
            position_config: PositionConfig实例，用于获取偏移量

        Returns:
            tuple: (x1, y1, x2, y2) 名称区域的截图坐标，或 None
        """
        if not position_config:
            return None
        
        # 获取偏移量
        try:
            offset = position_config.calculate_relative_offset(entity_type)
            if not offset:
                logging.error(f"无法获取{entity_type}的相对偏移量")
                return None

            # 检查offset是否包含必需的键
            required_keys = ['x_offset_tl', 'y_offset_tl', 'x_offset_br', 'y_offset_br']
            missing_keys = [key for key in required_keys if key not in offset]
            if missing_keys:
                logging.error(f"偏移量缺少必需的键: {missing_keys}, 当前offset: {offset}")
                return None
        except Exception as e:
            logging.error(f"获取偏移量时出错: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return None

        try:

            # 使用图标的左上角作为基准点
            icon_tl_x = icon_area['min_x']
            icon_tl_y = icon_area['min_y']

            # 计算名称区域的左上角和右下角（使用平均偏移量）
            avg_x_offset_tl = offset['x_offset_tl']
            avg_y_offset_tl = offset['y_offset_tl']
            avg_x_offset_br = offset['x_offset_br']
            avg_y_offset_br = offset['y_offset_br']

            # 计算名称区域
            name_tl_x = icon_tl_x + avg_x_offset_tl
            name_tl_y = icon_tl_y + avg_y_offset_tl
            name_br_x = icon_area['max_x'] + avg_x_offset_br
            name_br_y = icon_area['max_y'] + avg_y_offset_br

            # 扩大范围，增加容差（上下左右各增加20%）
            name_width = name_br_x - name_tl_x
            name_height = name_br_y - name_tl_y
            padding_x = name_width * 0.2
            padding_y = name_height * 0.2

            x1 = int(name_tl_x - padding_x)
            y1 = int(name_tl_y - padding_y)
            x2 = int(name_br_x + padding_x)
            y2 = int(name_br_y + padding_y)

            logging.debug(
                f"计算出的名称区域({entity_type}): ({x1}, {y1}) -> ({x2}, {y2})")
            return (x1, y1, x2, y2)
        except Exception as e:
            logging.error(f"根据图标区域计算名称区域失败: {e}")
            return None
