"""
主控制器 - 整合所有功能模块
"""
import os
import threading
import time
import logging
import traceback
import win32gui
from config import ConfigManager
from data.loader import DataLoader
from game.position import PositionConfig
from game.monitor import LogMonitor
from system.update import UpdateChecker
from .gui_manager import GUIManager
from .ocr_processor import OCRProcessor
from .window_detector import WindowDetector
from .cleanup_manager import CleanupManager


class MainController:
    """主控制器 - 整合所有功能模块"""

    def __init__(self):
        """初始化主控制器"""
        # 配置管理
        self.config = ConfigManager()

        # 数据管理
        self.data_loader = DataLoader()
        self.position_config = PositionConfig()

        # 功能模块
        self.gui_manager = GUIManager()
        self.window_detector = WindowDetector()
        self.cleanup_manager = CleanupManager()
        self.log_monitor = LogMonitor()
        # OCR处理器需要window_detector和position_config，所以后初始化
        self.ocr_processor = OCRProcessor()

        # 系统功能
        self.update_checker = UpdateChecker(self.config)

        # 状态管理
        self.is_running = True
        self.ctrl_pressed = False
        self.alt_pressed = False
        self.shift_pressed = False
        self.last_check_time = time.time()
        self.check_interval = 0.1

        # 线程管理
        self.keep_alive_thread = None

    def initialize(self):
        """初始化所有模块 - 每个模块独立异常处理，确保一个失败不影响其他"""
        # 配置Tesseract路径
        try:
            tesseract_path = self.config.get_tesseract_path()
            if tesseract_path and os.path.exists(tesseract_path):
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                logging.info(f"[MainController] 已设置Tesseract路径: {tesseract_path}")
            else:
                logging.warning(f"[MainController] Tesseract路径不存在: {tesseract_path}")
        except Exception as e:
            logging.error(f"[MainController] 配置Tesseract路径失败: {e}")
            logging.error(traceback.format_exc())
        
        # 加载数据
        try:
            self.data_loader.load_monster_data()
        except Exception as e:
            logging.error(f"[MainController] 加载怪物数据失败: {e}")
            logging.error(traceback.format_exc())
        
        try:
            self.data_loader.load_event_data()
            # 检查matcher是否初始化成功
            if hasattr(self.data_loader, 'matcher') and self.data_loader.matcher:
                logging.info(f"[MainController] 文本匹配器已初始化: {type(self.data_loader.matcher).__name__}")
            else:
                logging.warning(f"[MainController] 文本匹配器未初始化或为None: matcher={getattr(self.data_loader, 'matcher', 'NOT_FOUND')}")
        except Exception as e:
            logging.error(f"[MainController] 加载事件数据失败: {e}")
            logging.error(traceback.format_exc())
        
        try:
            self.data_loader.load_items_data()
        except Exception as e:
            logging.error(f"[MainController] 加载物品数据失败: {e}")
            logging.error(traceback.format_exc())

        # 加载位置配置
        try:
            self.position_config.load_position_config()
        except Exception as e:
            logging.error(f"[MainController] 加载位置配置失败: {e}")
            logging.error(traceback.format_exc())

        # 创建GUI窗口
        try:
            self.gui_manager.create_info_window()
        except Exception as e:
            logging.error(f"[MainController] 创建GUI窗口失败: {e}")
            logging.error(traceback.format_exc())

        # 启动游戏日志监控
        try:
            # 将uuid_to_item_data传递给LogMonitor（直接设置属性）
            if self.data_loader.uuid_to_item_data:
                self.log_monitor.uuid_to_item_data = self.data_loader.uuid_to_item_data
            self.log_monitor.start_log_monitor()
        except Exception as e:
            logging.error(f"[MainController] 启动游戏日志监控失败: {e}")
            logging.error(traceback.format_exc())

        # 启动保活线程
        self.keep_alive_thread = threading.Thread(
            target=self.keep_alive, daemon=True)
        self.keep_alive_thread.start()

        # 启动GUI更新定时器
        self.gui_manager.start_gui_update_timer(
            is_running_callback=lambda: self.is_running)

        # 检查更新
        if self.config.get("auto_update", True):
            self.update_checker.check_update()

    def keep_alive(self):
        """保活机制，检查Ctrl键、Alt键和Shift键状态和程序响应（不直接操作GUI）"""
        import win32api
        import pyautogui
        
        VK_CONTROL = 0x11  # Ctrl键的虚拟键码
        VK_MENU = 0x12  # Alt键的虚拟键码（VK_MENU是Alt键）
        VK_SHIFT = 0x10  # Shift键的虚拟键码
        self.last_action_time = 0  # 上次执行动作的时间
        debounce_delay = 0.2  # 防抖动延迟(秒) - 从0.5秒减少到0.2秒，提高响应速度
        last_ocr_task_time = 0  # 上次OCR任务开始的时间
        last_position = (0, 0)  # 上次鼠标位置
        position_update_interval = 0.05  # 位置更新间隔从0.1秒减少到0.05秒，提高跟随流畅度
        last_position_update = 0
        
        # 创建OCR线程池（单线程，避免并发问题）
        import concurrent.futures
        ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="OCR")

        while self.is_running:
            try:
                current_time = time.time()
                
                # 首先检查鼠标是否在游戏窗口内
                # 只有在游戏窗口内时，才响应Ctrl/Shift键
                import pyautogui
                cursor_x, cursor_y = pyautogui.position()
                game_hwnd, game_rect = self.window_detector.get_game_window()
                
                # 检查鼠标是否在游戏窗口内
                is_cursor_in_game = False
                if game_hwnd and game_rect:
                    hwnd_at_cursor = win32gui.WindowFromPoint((cursor_x, cursor_y))
                    root_hwnd = win32gui.GetAncestor(hwnd_at_cursor, 2)  # GA_ROOT = 2
                    is_cursor_in_game = (root_hwnd == game_hwnd)
                
                # 使用win32api检查Ctrl键、Shift键状态（Alt键功能已禁用）
                ctrl_state = win32api.GetAsyncKeyState(VK_CONTROL)
                shift_state = win32api.GetAsyncKeyState(VK_SHIFT)
                is_ctrl_pressed = (ctrl_state & 0x8000) != 0
                is_shift_pressed = (shift_state & 0x8000) != 0

                # 处理Ctrl键状态变化（无论鼠标是否在游戏窗口内）
                # 这样当切换出游戏时，Ctrl键释放也能隐藏窗口
                if is_ctrl_pressed != self.ctrl_pressed:
                    self.ctrl_pressed = is_ctrl_pressed
                    if is_ctrl_pressed:
                        # 只有鼠标在游戏窗口内时才处理Ctrl键按下
                        if is_cursor_in_game:
                            time_since_last = current_time - self.last_action_time
                            logging.info(
                                f"Ctrl键按下（游戏内），距离上次动作: {time_since_last:.2f}秒，"
                                f"防抖动延迟: {debounce_delay}秒")
                            # 添加防抖动: 检查距离上次动作的时间是否足够
                            # 同时检查上次OCR任务是否完成（避免任务堆积）
                            time_since_last_ocr = current_time - last_ocr_task_time
                            if current_time - self.last_action_time >= debounce_delay and time_since_last_ocr >= 0.1:
                                # 检查光标是否在图标区域内（用于决定是否显示信息）
                                in_area, _ = self.window_detector.is_cursor_in_icon_area(
                                    cursor_x, cursor_y, 'monster',
                                    window_rect=game_rect,
                                    position_config=self.position_config)
                                if not in_area:
                                    logging.info(f"光标不在图标区域内，但仍保存截图。光标位置: ({cursor_x}, {cursor_y})")
                                
                                logging.info("防抖动检查通过，开始OCR识别并保存截图")
                                last_ocr_task_time = current_time  # 记录OCR任务开始时间
                                # Ctrl键被按下，获取并显示信息（使用右上角区域）
                                # 使用线程池异步执行OCR，避免阻塞按键检测
                                # 即使不在图标区域内，也调用get_text_at_cursor来保存截图
                                future = ocr_executor.submit(
                                    self.ocr_processor.get_text_at_cursor,
                                    region_type='monster',
                                    window_detector=self.window_detector,
                                    position_config=self.position_config,
                                    skip_checks=True
                                )
                                # 设置超时，避免长时间阻塞
                                try:
                                    text = future.result(timeout=1.5)  # 1.5秒超时
                                    # 如果不在图标区域内，即使OCR成功也不显示信息
                                    if not in_area:
                                        text = None
                                except concurrent.futures.TimeoutError:
                                    logging.warning("OCR识别超时，但截图已保存")
                                    text = None
                                
                                # 只有在text不为None时才处理
                                if text:
                                    x, y = pyautogui.position()
                                    last_position = (x, y)
                                    # 添加到GUI更新队列而不是直接操作
                                    with self.gui_manager.gui_update_lock:
                                        self.gui_manager.gui_update_queue.append({
                                            'type': 'show',
                                            'text': text,
                                            'x': x,
                                            'y': y,
                                            'data_matcher': self.data_loader.matcher,
                                            'data_loader': self.data_loader
                                        })
                                    self.last_action_time = current_time
                                else:
                                    logging.warning("OCR识别返回空文本")
                                    # 即使OCR失败，也更新last_action_time以防止频繁触发
                                    self.last_action_time = current_time
                            else:
                                logging.info(
                                    f"防抖动阻止：距离上次动作仅 {time_since_last:.2f}秒，"
                                    f"需要等待 {debounce_delay - time_since_last:.2f}秒")
                        else:
                            # 鼠标不在游戏窗口内时按下Ctrl键，不处理
                            logging.debug("Ctrl键按下（游戏外），忽略")
                    else:
                            # Ctrl键释放（无论鼠标是否在游戏窗口内）
                            location = "游戏内" if is_cursor_in_game else "游戏外"
                            logging.info(f"Ctrl键释放（{location}）")
                            # Ctrl键释放，添加隐藏任务到队列
                            with self.gui_manager.gui_update_lock:
                                self.gui_manager.gui_update_queue.append({'type': 'hide'})

                    # Shift键状态发生变化（物品附魔显示）
                    if is_shift_pressed != self.shift_pressed:
                        self.shift_pressed = is_shift_pressed
                        if is_shift_pressed:
                            time_since_last = current_time - self.last_action_time
                            logging.info(
                                f"Shift键按下（游戏内），距离上次动作: {time_since_last:.2f}秒，"
                                f"防抖动延迟: {debounce_delay}秒")
                            # 添加防抖动: 检查距离上次动作的时间是否足够
                            # 同时检查上次OCR任务是否完成（避免任务堆积）
                            time_since_last_ocr = current_time - last_ocr_task_time
                            if current_time - self.last_action_time >= debounce_delay and time_since_last_ocr >= 0.1:
                                # 检查光标是否在图标区域内（用于决定是否显示信息）
                                in_area, _ = self.window_detector.is_cursor_in_icon_area(
                                    cursor_x, cursor_y, 'item',
                                    window_rect=game_rect,
                                    position_config=self.position_config)
                                if not in_area:
                                    logging.info(f"光标不在图标区域内，但仍保存截图。光标位置: ({cursor_x}, {cursor_y})")
                                
                                logging.info("Shift键防抖动检查通过，开始物品OCR识别并保存截图")
                                last_ocr_task_time = current_time  # 记录OCR任务开始时间
                                # Shift键被按下，获取物品信息并显示附魔
                                # 使用线程池异步执行OCR，避免阻塞按键检测
                                # 即使不在图标区域内，也调用get_text_at_cursor来保存截图
                                future = ocr_executor.submit(
                                    self.ocr_processor.get_text_at_cursor,
                                    region_type='item',
                                    window_detector=self.window_detector,
                                    position_config=self.position_config,
                                    skip_checks=True
                                )
                                # 设置超时，避免长时间阻塞
                                try:
                                    text = future.result(timeout=1.5)  # 1.5秒超时
                                    # 如果不在图标区域内，即使OCR成功也不显示信息
                                    if not in_area:
                                        text = None
                                except concurrent.futures.TimeoutError:
                                    logging.warning("OCR识别超时，但截图已保存")
                                    text = None
                                
                                if text:
                                    x, y = pyautogui.position()
                                    last_position = (x, y)
                                    # 添加到GUI更新队列而不是直接操作
                                    with self.gui_manager.gui_update_lock:
                                        self.gui_manager.gui_update_queue.append({
                                            'type': 'show_enchantments',
                                            'text': text,
                                            'x': x,
                                            'y': y,
                                            'data_matcher': self.data_loader.matcher,
                                            'data_loader': self.data_loader
                                        })
                                    self.last_action_time = current_time
                                else:
                                    logging.warning("Shift OCR识别返回空文本")
                                    # 即使OCR失败，也更新last_action_time以防止频繁触发
                                    self.last_action_time = current_time
                            else:
                                logging.info(
                                    f"Shift键防抖动阻止：距离上次动作仅 {time_since_last:.2f}秒，"
                                    f"需要等待 {debounce_delay - time_since_last:.2f}秒")
                        else:
                            # Shift键释放
                            logging.info("Shift键释放（游戏内）")
                            # Shift键释放，添加隐藏任务到队列
                            with self.gui_manager.gui_update_lock:
                                self.gui_manager.gui_update_queue.append({'type': 'hide'})

                # 更新窗口位置（如果窗口显示中且Ctrl键或Shift键仍然按下）
                if self.ctrl_pressed or self.shift_pressed:
                    # 限制位置更新频率
                    if current_time - last_position_update >= position_update_interval:
                        x, y = pyautogui.position()
                        # 只在位置变化时更新
                        if (x, y) != last_position:
                            last_position = (x, y)
                            with self.gui_manager.gui_update_lock:
                                self.gui_manager.gui_update_queue.append({
                                    'type': 'move',  # 改为 move 类型，只移动位置不调整大小
                                    'x': x,
                                    'y': y
                                })
                            last_position_update = current_time

                # 短暂休眠以减少CPU使用
                time.sleep(0.02)

            except Exception as e:
                logging.error(f"保活线程异常: {e}")
                time.sleep(1)  # 发生异常时稍长的休眠
                continue
        
        # 循环结束后关闭OCR线程池
        if 'ocr_executor' in locals() and ocr_executor:
            try:
                ocr_executor.shutdown(wait=True)
                logging.info("OCR线程池已关闭")
            except Exception as e:
                logging.error(f"关闭OCR线程池失败: {e}")

    def run(self):
        """运行主程序"""
        try:
            # 确保GUI窗口已创建
            if not self.gui_manager.info_window:
                self.gui_manager.create_info_window()
            
            if self.gui_manager.info_window:
                # 运行tkinter主循环
                self.gui_manager.info_window.mainloop()
            else:
                # 如果没有GUI窗口，保持主线程运行
                import time
                while self.is_running:
                    time.sleep(1)
        except Exception as e:
            logging.error(f"主程序运行异常: {e}")
            self.stop()

    def stop(self):
        """停止程序"""
        logging.info("正在停止程序...")
        self.is_running = False

        # 先销毁GUI窗口（这会退出mainloop）
        if self.gui_manager.info_window:
            try:
                # 销毁窗口会退出mainloop
                self.gui_manager.info_window.quit()
                self.gui_manager.info_window.destroy()
                self.gui_manager.info_window = None
            except Exception as e:
                logging.error(f"销毁GUI窗口失败: {e}")

        # 停止线程
        if self.keep_alive_thread and self.keep_alive_thread.is_alive():
            self.keep_alive_thread.join(timeout=1)

        # 停止日志监控
        self.log_monitor.stop_log_monitor()

        # 清理资源
        self.cleanup_manager.cleanup_temp_files()
        self.cleanup_manager.cleanup_icon_cache()

        logging.info("程序已停止")
