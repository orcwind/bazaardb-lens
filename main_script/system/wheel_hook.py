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

    # Feature flag to disable all wheel/hook behavior when removed
    WHEEL_FEATURE_ENABLED = False

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
                delta = _get_wheel_delta_from_mouseData(ms.mouseData)
                # delta is typically +/-120 per notch
                if _is_ctrl_pressed() and _callback:
                    # compute units similar to tkinter: -1 * (delta/120)
                    try:
                        units = int(-1 * (delta / 120))
                    except Exception:
                        units = 0
                    if units != 0:
                        # Enqueue event and return immediately; main thread should drain and handle events.
                        try:
                            with _queue_lock:
                                _event_queue.append(units)
                            logging.debug(f"wheel_hook: enqueued units={units}")
                        except Exception:
                            logging.exception("wheel_hook: enqueue failed")
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
        if not WHEEL_FEATURE_ENABLED:
            logging.debug("wheel_hook: start_hook skipped (feature disabled)")
            _callback = cb
            return
        logging.info("wheel_hook: start_hook called")
        if _hook_thread and _hook_thread.is_alive():
            logging.info("wheel_hook: already running")
            _callback = cb
            return
        _callback = cb
        _stop_event.clear()
        _hook_thread = threading.Thread(target=_hook_thread_func, name="WheelHookThread", daemon=True)
        _hook_thread.start()

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
                logging.debug(f"wheel_hook: WM_INPUT received hwnd={hwnd}, wParam={wParam}, lParam={lParam}")
                size = ctypes.c_uint(0)
                res = user32.GetRawInputData(lParam, RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
                logging.debug(f"wheel_hook: GetRawInputData(header) res={res}, size={size.value}")
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
                    logging.debug(f"wheel_hook: raw.header.dwType={raw.header.dwType}, header.dwSize={raw.header.dwSize}, hDevice={raw.header.hDevice}")
                    if raw.header.dwType == RIM_TYPEMOUSE:
                        usButtonFlags = raw.mouse.usButtonFlags
                        usButtonData = raw.mouse.usButtonData
                        lLastX = raw.mouse.lLastX
                        lLastY = raw.mouse.lLastY
                        logging.debug(f"wheel_hook: RAWMOUSE usButtonFlags={usButtonFlags}, usButtonData={usButtonData}, lLastX={lLastX}, lLastY={lLastY}")
                        # wheel delta is signed short in usButtonData for wheel events
                        delta = ctypes.c_short(usButtonData).value
                        units = int(-1 * (delta / 120)) if delta != 0 else 0
                        logging.debug(f"wheel_hook: computed delta={delta}, units={units}")
                        if units != 0:
                            try:
                                with _queue_lock:
                                    _event_queue.append(units)
                                logging.info(f"wheel_hook: enqueued raw units={units}")
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
        WNDCLASSEX = ctypes.wintypes.WNDCLASSEX
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

