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
        self._invalid_cache_time = 0  # 无效状态缓存时间戳
        self._invalid_cache_duration = 2.0  # 无效状态缓存（秒）- 窗口最小化时不频繁重试
        self._last_log_time = 0  # 上次日志时间
        self._log_interval = 10.0  # 日志间隔（秒）

    def get_game_window(self):
        """获取游戏窗口句柄和位置"""
        import time
        current_time = time.time()
        
        # 如果最近检测结果是无效的，直接返回None（避免频繁重试）
        if (current_time - self._invalid_cache_time) < self._invalid_cache_duration:
            return None, None
        
        # 如果有缓存且未过期，检查窗口是否仍然有效
        if self.game_hwnd and (current_time - self._cache_time) < self._cache_duration:
            try:
                # 首先检查窗口是否仍然存在
                if win32gui.IsWindow(self.game_hwnd):
                    # 优先检查窗口是否最小化（无论是否可见，最小化就直接返回None）
                    if win32gui.IsIconic(self.game_hwnd):
                        self._set_invalid_cache(current_time, "游戏窗口已最小化，跳过")
                        self.game_hwnd = None
                        self.game_rect = None
                        return None, None
                    # 检查窗口是否可见
                    if win32gui.IsWindowVisible(self.game_hwnd):
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
                    self._set_invalid_cache(current_time, "游戏窗口已最小化，跳过")
                    return None, None
                # 检查窗口是否可见
                if not win32gui.IsWindowVisible(hwnd):
                    self._set_invalid_cache(current_time, "游戏窗口不可见，跳过")
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

                # 记录所有找到的窗口用于调试（debug级别）
                if windows:
                    logging.debug(f"找到的所有游戏窗口候选:")
                    for h, t, r, w, h_val in windows:
                        logging.debug(f"  - {t}: {w}x{h_val} at {r}")

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
                    logging.debug(
                        f"通过枚举找到游戏窗口: {found_window_name}, "
                        f"尺寸: {valid_windows[0][3]}x{valid_windows[0][4]}")
                elif windows:
                    # 如果没有尺寸合理的窗口，选择最大的
                    windows.sort(key=lambda x: x[3] * x[4], reverse=True)
                    hwnd = windows[0][0]
                    found_window_name = windows[0][1]
                    logging.debug(
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
                    # 如果设置前台窗口失败，不输出日志（这是预期行为）
                    pass

                rect = win32gui.GetWindowRect(hwnd)
                # 检查窗口状态
                is_minimized = win32gui.IsIconic(hwnd)
                is_visible = win32gui.IsWindowVisible(hwnd)
                logging.debug(f"找到游戏窗口: {found_window_name}, 坐标: {rect}")
                logging.debug(f"窗口状态 - 最小化: {is_minimized}, 可见: {is_visible}")
                
                # 如果窗口最小化或不可见，返回None
                if is_minimized:
                    self._set_invalid_cache(current_time, "游戏窗口已最小化，跳过")
                    return None, None
                if not is_visible:
                    self._set_invalid_cache(current_time, "游戏窗口不可见，跳过")
                    return None, None

                # 如果窗口太小，尝试获取客户端区域
                if rect[2] - rect[0] < 200 or rect[3] - rect[1] < 100:
                    try:
                        client_rect = win32gui.GetClientRect(hwnd)
                        client_width = client_rect[2]
                        client_height = client_rect[3]
                        logging.debug(
                            f"客户端区域尺寸: {client_width}x{client_height}")

                        if client_width > 800 and client_height > 600:
                            # 使用客户端坐标重新计算窗口坐标
                            point = win32gui.ClientToScreen(hwnd, (0, 0))
                            rect = (
                                point[0],
                                point[1],
                                point[0] + client_width,
                                point[1] + client_height)
                            logging.debug(f"使用客户端坐标: {rect}")
                    except Exception as e:
                        logging.debug(f"获取客户端坐标失败: {e}")

                self.game_hwnd = hwnd
                self.game_rect = rect
                self._cache_time = current_time  # 更新缓存时间
                return hwnd, rect

            self._set_invalid_cache(current_time, "未找到游戏窗口")
            return None, None
        except Exception as e:
            logging.error(f"获取游戏窗口失败: {e}")
            self._invalid_cache_time = current_time
            return None, None
    
    def _set_invalid_cache(self, current_time, message):
        """设置无效状态缓存，并控制日志频率"""
        self._invalid_cache_time = current_time
        # 每隔一段时间才输出一次日志，避免刷屏
        if (current_time - self._last_log_time) >= self._log_interval:
            self._last_log_time = current_time
            logging.info(message)

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
