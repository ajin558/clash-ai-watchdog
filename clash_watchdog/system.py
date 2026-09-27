# -*- coding: utf-8 -*-
"""
系统级底层支持模块 (System Integration)
包含：Win32 内核级单实例互斥锁 (Zero-leak Kernel Mutex)、跨平台终端 VT100 控制
100% 绿色便携，零注册表修改，零多余文件残留
"""

import sys
import os

class SingleInstance:
    """
    进程单实例互斥锁
    Windows: 基于 Win32 内核命名互斥体 (CreateMutexW)，由操作系统监管生命周期，进程退出自动释放，绝无死锁文件残留。
    Linux/macOS: 基于本地回环套接字独占绑定。
    """
    def __init__(self, name="ClashAIWatchdog_Mutex"):
        self.name = name
        self.handle = None
        self.sock = None
        self.is_running = False

    def acquire(self):
        """尝试获取单实例锁。若已有实例在运行，返回 False；成功获取返回 True。"""
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            
            # 尝试创建本地会话命名互斥体
            mutex_name = f"Local\\{self.name}"
            handle = kernel32.CreateMutexW(None, False, mutex_name)
            last_error = kernel32.GetLastError()
            
            ERROR_ALREADY_EXISTS = 183
            if last_error == ERROR_ALREADY_EXISTS:
                if handle:
                    kernel32.CloseHandle(handle)
                self.is_running = True
                return False
            
            self.handle = handle
            self.is_running = False
            return True
        else:
            import socket
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.bind(('127.0.0.1', 29099))
                self.sock.listen(1)
                self.is_running = False
                return True
            except (socket.error, OSError):
                self.is_running = True
                return False

    def release(self):
        """释放锁资源"""
        if sys.platform == "win32" and self.handle:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None
        elif self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

def enable_vt100_support():
    """
    开启 Windows 控制台的原生 VT100 / ANSI 虚拟终端序列支持
    支持光标无闪烁复位与 24 位真彩色
    """
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_out = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        if h_out:
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(h_out, ctypes.byref(mode)):
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                kernel32.SetConsoleMode(h_out, mode.value | 0x0004)
