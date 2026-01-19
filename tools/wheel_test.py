#!/usr/bin/env python3
"""
Quick test script to print mouse wheel events (delta / num).
Run with: python tools\wheel_test.py

Instructions:
 - Focus the small window that appears.
 - Scroll the wheel up and down and watch the console output for positive/negative values.
 - On Linux X11 you may see Button-4/Button-5 events instead.
"""
import tkinter as tk


def on_wheel(event):
    # event.delta on Windows (positive for up, negative for down, multiples of 120)
    # event.num on X11: 4 = up, 5 = down
    delta = getattr(event, "delta", None)
    num = getattr(event, "num", None)
    print(f"mousewheel event - delta: {delta}, num: {num}")


def main():
    root = tk.Tk()
    root.title("BazaarInfo wheel test")
    root.geometry("420x120")
    label = tk.Label(
        root,
        text="把焦点放在这里并滚轮上下（观察控制台输出）。\nWindows 上应看到 delta 为正/负。",
        padx=12,
        pady=12,
    )
    label.pack(fill="both", expand=True)

    # Bind both common wheel event types
    root.bind("<MouseWheel>", on_wheel)   # Windows / Mac (delta)
    root.bind("<Button-4>", on_wheel)     # X11 up
    root.bind("<Button-5>", on_wheel)     # X11 down

    # Ensure the label can get focus easily
    label.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()

