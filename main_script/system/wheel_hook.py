"""
Windows global mouse wheel hook (WH_MOUSE_LL) to capture wheel events and forward them
to a provided callback when active. Limited to Windows; on other platforms this module
provides no-op functions.

Usage:
    from main_script.system import wheel_hook
    wheel_hook.start_hook(callback)   # callback(delta)
    wheel_hook.stop_hook()
"""
import sys
import logging

if sys.platform != "win32":
    # Provide no-op shims on non-Windows platforms
    def start_hook(cb):
        logging.info("wheel_hook: start_hook no-op on non-Windows")

    def stop_hook():
        logging.info("wheel_hook: stop_hook no-op on non-Windows")

    def is_running():
        return False

else:
    import ctypes
    import threading
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    WH_MOUSE_LL = 14
    WM_MOUSEWHEEL = 0x020A
    VK_CONTROL = 0x11

    # Feature flag to enable/disable low-level wheel/hook behavior.
    # 设置为 True 可在 Windows 上启用全局滚轮捕获（需要管理员权限或适当环境）。
    # 如果遇到兼容性问题，可改回 False。
    WHEEL_FEATURE_ENABLED = True
    # Diagnostic flags (set True temporarily to force enqueue for debugging)
    DIAG_FORCE_ENQUEUE = True
    # Test mode: when True, skip RawInput and force using WH_MOUSE_LL only.
    # 已结束临时 WH-only 测试，恢复为 False 以同时使用 RawInput + WH_MOUSE_LL（有过滤策略）。
    FORCE_WH_ONLY = False

    # Define C types for hook prototypes
    LRESULT = ctypes.c_long
    WPARAM = wintypes.WPARAM
    LPARAM = wintypes.LPARAM

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class MSLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("pt", POINT),
            ("mouseData", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    _hook_handle = None
    _hook_thread = None
    _callback = None
    _stop_event = threading.Event()
    from collections import deque
    _event_queue = deque()
    _queue_lock = threading.Lock()

    # LowLevelMouseProc prototype
    CMPFUNC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, WPARAM, LPARAM)

    def _get_wheel_delta_from_mouseData(mouseData):
        # wheel delta is in high-order word of mouseData (signed short)
        hi = (mouseData >> 16) & 0xFFFF
        # convert to signed short
        if hi & 0x8000:
            hi = hi - 0x10000
        return hi

    def _is_ctrl_pressed():
        # GetAsyncKeyState returns short; highest bit set if key is down
        state = user32.GetAsyncKeyState(VK_CONTROL)
        return (state & 0x8000) != 0

    # Ensure CallNextHookEx has correct arg/return types to avoid ctypes conversion errors
    try:
        user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, WPARAM, LPARAM]
        user32.CallNextHookEx.restype = LRESULT
    except Exception:
        pass

    def _low_level_mouse_proc(nCode, wParam, lParam):
        try:
            if nCode == 0 and wParam == WM_MOUSEWHEEL:
                # lParam may be a pointer-sized integer; cast via c_void_p to pointer
                try:
                    lp = ctypes.c_void_p(lParam)
                    ms = ctypes.cast(lp, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                except Exception:
                    # fallback: if lParam already a pointer-like object
                    ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                # 计算原始 delta（signed short），通常每档为 +/-120
                try:
                    raw_mouseData = ms.mouseData & 0xFFFFFFFF
                    # log raw mouseData hex for diagnostics
                    logging.debug(f"wheel_hook: low_level mouseData=0x{raw_mouseData:08X}")
                    # compute signed hi-word (wheel delta) robustly
                    delta = _get_wheel_delta_from_mouseData(raw_mouseData)
                    # also compute via c_short for parity with RawInput path and log both (debug)
                    try:
                        alt_signed = ctypes.c_short((raw_mouseData >> 16) & 0xFFFF).value
                    except Exception:
                        alt_signed = delta
                    logging.debug(f"wheel_hook: low_level computed delta={delta}, alt_signed={alt_signed}")
                except Exception:
                    delta = 0

                # 仅在 Ctrl 被按下且有回调时入队并记录（避免噪音）
                ctrl = _is_ctrl_pressed()
                logging.debug(f"wheel_hook: low_level ctrl_pressed={ctrl}, callback_set={_callback is not None}")
                direction = "UP" if delta < 0 else ("DOWN" if delta > 0 else "NONE")
                logging.debug(f"wheel_hook: low_level direction={direction}")
                # Extra low-level diagnostic: include wParam/hiword and full mouseData for tracing
                try:
                    wparam_val = int(wParam)
                except Exception:
                    wparam_val = 0
                logging.debug(f"wheel_hook: LOW_LEVEL summary wParam=0x{wparam_val:08X}, mouseData=0x{raw_mouseData:08X}, delta={delta}, direction={direction}")
                # For diagnostics we may force enqueue even when Ctrl not pressed
                if DIAG_FORCE_ENQUEUE or (ctrl and _callback):
                    # 为兼容之前的单位计算，仍尝试计算 units（不强制使用）
                    try:
                        units = int(-1 * (delta / 120))
                    except Exception:
                        units = 0
                    try:
                        logging.debug(f"wheel_hook: low_level raw delta={delta}")
                    except Exception:
                        pass
                    try:
                        with _queue_lock:
                            _event_queue.append(delta)
                        logging.debug(f"wheel_hook: enqueued raw delta (low_level)={delta} (0x{(delta & 0xFFFF):04X})")
                    except Exception:
                        logging.exception("wheel_hook: enqueue failed (low_level)")
                    else:
                        logging.debug("wheel_hook: low_level not enqueued (ctrl not pressed and DIAG_FORCE_ENQUEUE is False)")
        except Exception:
            logging.exception("wheel_hook: low level proc error")
        # Call next hook (ensure proper types)
        try:
            return user32.CallNextHookEx(_hook_handle, nCode, wParam, lParam)
        except Exception:
            # If CallNextHookEx fails, return 0 to continue chain safely
            try:
                return LRESULT(0)
            except Exception:
                return 0

    def _hook_thread_func():
        global _hook_handle
        CMP = CMPFUNC(_low_level_mouse_proc)
        # Store CMP on thread to keep reference alive
        thread_local = threading.local()
        thread_local.cmp = CMP
        hInstance = kernel32.GetModuleHandleW(None)
        # First try using module handle obtained via GetModuleHandleW
        _hook_handle = user32.SetWindowsHookExW(WH_MOUSE_LL, CMP, hInstance, 0)
        if not _hook_handle:
            err = kernel32.GetLastError()
            logging.warning(f"wheel_hook: initial SetWindowsHookExW failed, GetLastError={err}; trying with hMod=0 fallback")
            # Fallback: try installing hook with hMod = 0 (NULL). This often works for low-level hooks.
            _hook_handle = user32.SetWindowsHookExW(WH_MOUSE_LL, CMP, 0, 0)
            if not _hook_handle:
                err2 = kernel32.GetLastError()
                # Try to format message for err2
                try:
                    FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000
                    buf = ctypes.create_unicode_buffer(512)
                    kernel32.FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM, None, err2, 0, buf, len(buf), None)
                    msg = buf.value.strip()
                except Exception:
                    msg = "<failed to format error>"
                logging.error(f"wheel_hook: SetWindowsHookExW failed after fallback, GetLastError={err2}, msg={msg}")
                return
            else:
                logging.info("wheel_hook: SetWindowsHookExW succeeded with hMod=0 fallback")
        else:
            logging.info("wheel_hook: SetWindowsHookExW succeeded with module handle")
        logging.info("wheel_hook: hook installed")
        msg = wintypes.MSG()
        while not _stop_event.is_set():
            res = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if res == 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        try:
            if _hook_handle:
                user32.UnhookWindowsHookEx(_hook_handle)
        except Exception:
            logging.exception("wheel_hook: unhook failed")
        logging.info("wheel_hook: hook thread exiting")

    def start_hook(cb):
        """Start the WH_MOUSE_LL hook and set callback(delta_units)."""
        global _hook_thread, _callback, _stop_event, _hook_handle
        logging.info("wheel_hook: start_hook called")
        _callback = cb
        # Prefer Raw Input listener (more reliable across environments). If the feature flag
        # is enabled, start the raw input listener; otherwise, fallback to legacy hook thread.
        try:
            if WHEEL_FEATURE_ENABLED:
                # When FORCE_WH_ONLY is set, skip RawInput entirely for a controlled test
                if FORCE_WH_ONLY:
                    logging.info("wheel_hook: FORCE_WH_ONLY=True, skipping start_raw_input_listener (using WH_MOUSE_LL only)")
                else:
                    # start raw input listener (non-blocking)
                    try:
                        start_raw_input_listener()
                        logging.info("wheel_hook: start_raw_input_listener invoked as primary mechanism")
                        # DO NOT return here: also try to start legacy WH_MOUSE_LL as a backup
                        logging.info("wheel_hook: continuing to start WH_MOUSE_LL as backup")
                    except Exception:
                        logging.exception("wheel_hook: start_raw_input_listener failed, falling back to hook thread")

            # Fallback: legacy WH_MOUSE_LL hook thread
            if _hook_thread and _hook_thread.is_alive():
                logging.info("wheel_hook: hook thread already running")
                return
            _stop_event.clear()
            _hook_thread = threading.Thread(target=_hook_thread_func, name="WheelHookThread", daemon=True)
            _hook_thread.start()
        except Exception:
            logging.exception("wheel_hook: start_hook failed to start any listener")

    def drain_events():
        """Drain and return queued wheel events (thread-safe). Called from main thread."""
        events = []
        if not WHEEL_FEATURE_ENABLED:
            return events
        try:
            with _queue_lock:
                while _event_queue:
                    events.append(_event_queue.popleft())
        except Exception:
            logging.exception("wheel_hook: drain_events failed")
        try:
            # If this batch contains any small signed delta (likely from low-level hook),
            # prefer those and filter out very large RawInput deltas (which may be device-specific)
            # to avoid large RawInput values (e.g. 1024) overriding small signed deltas (-120).
            if events:
                has_small_signed = any(abs(e) <= 120 for e in events)
                if has_small_signed:
                    filtered = [e for e in events if abs(e) < 500]
                    if len(filtered) != len(events):
                        logging.debug(f"wheel_hook: drain_events filtered {len(events)-len(filtered)} large delta(s) because small signed delta present")
                    events = filtered
                # Normalize any remaining excessively large deltas to a single wheel step (±120)
                # This prevents a single RawInput event with large magnitude (e.g. 1024) from
                # moving the view multiple pages at once.
                normalized = []
                large_count = 0
                for e in events:
                    if abs(e) > 500:
                        large_count += 1
                        normalized.append(120 if e > 0 else -120)
                    else:
                        normalized.append(e)
                if large_count:
                    logging.info(f"wheel_hook: drain_events normalized {large_count} large delta(s) to ±120")
                events = normalized
        except Exception:
            logging.exception("wheel_hook: drain_events post-filter failed")
        return events

    # ---------------- Raw Input fallback (preferred) ----------------
    _raw_thread = None
    _raw_hwnd = None
    _raw_running = False

    WM_INPUT = 0x00FF
    RIDEV_INPUTSINK = 0x00000100
    RID_INPUT = 0x10000003
    RIM_TYPEMOUSE = 0

    class RAWINPUTHEADER(ctypes.Structure):
        _fields_ = [
            ("dwType", ctypes.c_uint),
            ("dwSize", ctypes.c_uint),
            ("hDevice", ctypes.c_void_p),
            ("wParam", ctypes.c_ulong)
        ]

    class RAWMOUSE(ctypes.Structure):
        _fields_ = [
            ("usFlags", ctypes.c_ushort),
            ("usButtonFlags", ctypes.c_ushort),
            ("usButtonData", ctypes.c_ushort),
            ("ulRawButtons", ctypes.c_ulong),
            ("lLastX", ctypes.c_long),
            ("lLastY", ctypes.c_long),
            ("ulExtraInformation", ctypes.c_ulong),
        ]

    class RAWINPUT(ctypes.Structure):
        _fields_ = [
            ("header", RAWINPUTHEADER),
            ("mouse", RAWMOUSE)
        ]

    class RAWINPUTDEVICE(ctypes.Structure):
        _fields_ = [
            ("usUsagePage", ctypes.c_ushort),
            ("usUsage", ctypes.c_ushort),
            ("dwFlags", ctypes.c_uint),
            ("hwndTarget", ctypes.c_void_p),
        ]

    def _wnd_proc(hwnd, msg, wParam, lParam):
        if msg == WM_INPUT:
            try:
                # 信息级别记录 Raw Input 收到事件（包括参数），便于判断是否收到了向上滚事件
                logging.info(f"wheel_hook: WM_INPUT received hwnd={hwnd}, wParam={wParam}, lParam={lParam}")
                size = ctypes.c_uint(0)
                res = user32.GetRawInputData(lParam, RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
                logging.info(f"wheel_hook: GetRawInputData(header) res={res}, size={size.value}")
                if size.value == 0:
                    logging.debug("wheel_hook: WM_INPUT size==0, returning")
                    return user32.DefWindowProcW(hwnd, msg, wParam, lParam)
                buf = ctypes.create_string_buffer(size.value)
                res = user32.GetRawInputData(lParam, RID_INPUT, buf, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
                logging.debug(f"wheel_hook: GetRawInputData(data) res={res}, expected={size.value}")
                if res == size.value:
                    try:
                        raw = ctypes.cast(ctypes.byref(buf), ctypes.POINTER(RAWINPUT)).contents
                    except Exception:
                        logging.exception("wheel_hook: failed to cast raw input buffer to RAWINPUT")
                        return user32.DefWindowProcW(hwnd, msg, wParam, lParam)
                    logging.info(f"wheel_hook: raw.header.dwType={raw.header.dwType}, header.dwSize={raw.header.dwSize}, hDevice={raw.header.hDevice}")
                    if raw.header.dwType == RIM_TYPEMOUSE:
                        usButtonFlags = raw.mouse.usButtonFlags
                        usButtonData = raw.mouse.usButtonData
                        lLastX = raw.mouse.lLastX
                        lLastY = raw.mouse.lLastY
                        # Log raw values including hex for diagnostics
                        logging.info(f"wheel_hook: RAWMOUSE usButtonFlags=0x{usButtonFlags:04X}, usButtonData=0x{usButtonData:04X}, lLastX={lLastX}, lLastY={lLastY}")
                        # wheel delta is usually in usButtonData (unsigned short) but must be interpreted as signed short
                        try:
                            delta = ctypes.c_short(usButtonData).value
                        except Exception:
                            delta = 0
                        # Extra RawInput diagnostics for delta/direction tracing
                        logging.debug(f"wheel_hook: RAW_INPUT summary usButtonFlags=0x{usButtonFlags:04X}, usButtonData=0x{usButtonData:04X}, derived_delta={delta}, lLastY={lLastY}")
                        # If usButtonData is zero, only treat lLastY as wheel movement when
                        # the RAWMOUSE.usButtonFlags indicates a wheel event (RI_MOUSE_WHEEL).
                        RI_MOUSE_WHEEL = 0x0400
                        if delta == 0:
                            if (usButtonFlags & RI_MOUSE_WHEEL) and lLastY != 0:
                                try:
                                    # lLastY is usually small integer steps; convert to typical wheel delta scale
                                    delta = int(lLastY * 120)
                                    logging.info(f"wheel_hook: derived raw delta from lLastY: lLastY={lLastY} -> delta={delta}")
                                except Exception:
                                    pass
                            else:
                                # Not a wheel event -- ignore mouse movement deltas
                                delta = 0
                        # 直接把原始 delta 入队，避免舍弃小增量；记录 original usButtonData hex for troubleshooting
                        direction = "UP" if delta < 0 else ("DOWN" if delta > 0 else "NONE")
                        logging.info(f"wheel_hook: computed raw delta={delta} (usButtonData=0x{usButtonData:04X}), direction={direction}")
                        if delta != 0:
                            try:
                                with _queue_lock:
                                    _event_queue.append(delta)
                                # Preserve explicit debug for sign/preserved value
                                logging.debug(f"wheel_hook: enqueued raw delta (raw path)={delta} (0x{(delta & 0xFFFF):04X})")
                                logging.info(f"wheel_hook: enqueued raw delta={delta} (0x{(delta & 0xFFFF):04X})")
                            except Exception:
                                logging.exception("wheel_hook: enqueue failed (raw)")
            except Exception:
                logging.exception("wheel_hook: raw input processing failed")
        return user32.DefWindowProcW(hwnd, msg, wParam, lParam)

    WNDPROCTYPE = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, ctypes.c_uint, ctypes.c_int, ctypes.c_int)

    def _raw_message_thread():
        global _raw_hwnd, _raw_running
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hInstance = kernel32.GetModuleHandleW(None)
        # Minimal WNDCLASSEX definition
        class WNDCLASSEX(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("style", ctypes.c_uint),
                ("lpfnWndProc", WNDPROCTYPE),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", ctypes.c_void_p),
                ("hIcon", ctypes.c_void_p),
                ("hCursor", ctypes.c_void_p),
                ("hbrBackground", ctypes.c_void_p),
                ("lpszMenuName", ctypes.c_wchar_p),
                ("lpszClassName", ctypes.c_wchar_p),
                ("hIconSm", ctypes.c_void_p)
            ]
        wndproc = WNDPROCTYPE(_wnd_proc)
        className = "BazaarLensRawInputWindow"
        wcex = WNDCLASSEX()
        wcex.cbSize = ctypes.sizeof(WNDCLASSEX)
        wcex.style = 0
        wcex.lpfnWndProc = wndproc
        wcex.cbClsExtra = 0
        wcex.cbWndExtra = 0
        wcex.hInstance = hInstance
        wcex.hIcon = 0
        wcex.hCursor = 0
        wcex.hbrBackground = 0
        wcex.lpszMenuName = None
        wcex.lpszClassName = className
        wcex.hIconSm = 0
        try:
            atom = user32.RegisterClassExW(ctypes.byref(wcex))
        except Exception:
            atom = 0
        logging.debug(f"wheel_hook: RegisterClassExW returned atom={atom}")
        hwnd = user32.CreateWindowExW(0, className, "RawInputHiddenWindow", 0, 0, 0, 0, 0, 0, 0, hInstance, None)
        _raw_hwnd = hwnd
        logging.debug(f"wheel_hook: CreateWindowExW returned hwnd={hwnd}")
        # Register raw input for mouse with INPUTSINK
        try:
            rid = RAWINPUTDEVICE()
            rid.usUsagePage = 0x01
            rid.usUsage = 0x02
            rid.dwFlags = RIDEV_INPUTSINK
            rid.hwndTarget = hwnd
            ok = user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(rid))
            if not ok:
                err = kernel32.GetLastError()
                try:
                    buf = ctypes.create_unicode_buffer(512)
                    kernel32.FormatMessageW(0x00001000, None, err, 0, buf, len(buf), None)
                    msg = buf.value.strip()
                except Exception:
                    msg = "<failed to format error>"
                logging.warning(f"wheel_hook: RegisterRawInputDevices failed, GetLastError={err}, msg={msg}, hwnd={hwnd}")
            else:
                logging.info("wheel_hook: RegisteredRawInputDevices succeeded")
        except Exception:
            logging.exception("wheel_hook: exception while calling RegisterRawInputDevices")
        _raw_running = True
        msg = wintypes.MSG()
        while _raw_running:
            res = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if res == 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        try:
            if _raw_hwnd:
                user32.DestroyWindow(_raw_hwnd)
        except Exception:
            pass
        _raw_hwnd = None

    def start_raw_input_listener():
        """Start raw input message window and thread."""
        global _raw_thread, _raw_running
        if not WHEEL_FEATURE_ENABLED:
            logging.debug("wheel_hook: start_raw_input_listener skipped (feature disabled)")
            return
        logging.info("wheel_hook: start_raw_input_listener called")
        if _raw_thread and _raw_thread.is_alive():
            return
        _raw_running = True
        _raw_thread = threading.Thread(target=_raw_message_thread, name="RawInputThread", daemon=True)
        _raw_thread.start()
        logging.info("wheel_hook: raw input thread started")

    def stop_raw_input_listener():
        global _raw_running
        if not WHEEL_FEATURE_ENABLED:
            logging.debug("wheel_hook: stop_raw_input_listener skipped (feature disabled)")
            return
        _raw_running = False
        try:
            if _raw_hwnd:
                user32.PostMessageW(_raw_hwnd, 0x0012, 0, 0)  # WM_QUIT
        except Exception:
            pass

    def stop_hook():
        """Stop the hook and thread."""
        global _stop_event
        if not WHEEL_FEATURE_ENABLED:
            logging.debug("wheel_hook: stop_hook skipped (feature disabled)")
            return
        _stop_event.set()
        # Post a quit message to unblock GetMessage
        try:
            user32.PostThreadMessageW(_hook_thread.ident, 0x0012, 0, 0)  # WM_QUIT
        except Exception:
            pass

    def is_running():
        return _hook_thread is not None and _hook_thread.is_alive()

