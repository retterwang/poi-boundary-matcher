"""
GUI资源管理工具
功能：统一管理Tkinter实例的生命周期
      提供文件选择、消息显示、对话框管理等通用GUI功能
      解决多个工具中重复创建Tk实例导致的内存泄漏问题

使用方式：
    from GUIManager import GUIManager
    gui = GUIManager()
    file_path = gui.select_file(title="选择文件", filetypes=[("CSV", "*.csv")])
    gui.show_info("处理完成！")
    gui.cleanup()
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional, List, Tuple, Dict, Any
import threading


class GUIManager:
    """
    统一的GUI管理工具类

    采用单例模式确保全局只有一个Tk实例，避免重复创建导致的内存泄漏。
    提供统一的文件选择、消息显示、对话框管理等接口。

    Attributes:
        _instance: 单例实例
        _lock: 线程安全锁
        _root: Tk根窗口实例
    """

    _instance: Optional['GUIManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> 'GUIManager':
        """单例模式实现，确保全局只有一个GUIManager实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """初始化GUIManager"""
        if self._initialized:
            return
        self._root: Optional[tk.Tk] = None
        self._initialized: bool = True

    def _ensure_root(self) -> tk.Tk:
        """
        获取或创建Tk根窗口实例

        Returns:
            tk.Tk: Tk根窗口实例
        """
        try:
            if self._root is None or not self._root.winfo_exists():
                self._root = tk.Tk()
                self._root.withdraw()  # 默认隐藏主窗口
        except tk.TclError:
            # 当Tk实例被销毁后重新创建
            self._root = tk.Tk()
            self._root.withdraw()
        return self._root

    def select_file(
        self,
        title: str = "选择文件",
        filetypes: Optional[List[Tuple[str, str]]] = None
    ) -> Optional[str]:
        """
        统一的单文件选择接口

        Args:
            title: 对话框标题
            filetypes: 文件类型过滤器，格式为[("描述", "*.ext"), ...]

        Returns:
            Optional[str]: 选择的文件路径，取消则返回None
        """
        try:
            root = self._ensure_root()
            file_path = filedialog.askopenfilename(
                parent=root,
                title=title,
                filetypes=filetypes or [("所有文件", "*.*")]
            )
            return file_path if file_path else None
        except Exception as e:
            print(f"文件选择失败: {str(e)}")
            return None

    def select_files(
        self,
        title: str = "选择文件",
        filetypes: Optional[List[Tuple[str, str]]] = None
    ) -> List[str]:
        """
        统一的多文件选择接口

        Args:
            title: 对话框标题
            filetypes: 文件类型过滤器

        Returns:
            List[str]: 选择的文件路径列表
        """
        try:
            root = self._ensure_root()
            file_paths = filedialog.askopenfilenames(
                parent=root,
                title=title,
                filetypes=filetypes or [("所有文件", "*.*")]
            )
            return list(file_paths) if file_paths else []
        except Exception as e:
            print(f"文件选择失败: {str(e)}")
            return []

    def save_file(
        self,
        title: str = "保存文件",
        defaultextension: str = "",
        initialfile: str = "",
        filetypes: Optional[List[Tuple[str, str]]] = None
    ) -> Optional[str]:
        """
        统一的文件保存接口

        Args:
            title: 对话框标题
            defaultextension: 默认扩展名
            initialfile: 默认文件名
            filetypes: 文件类型过滤器

        Returns:
            Optional[str]: 保存的文件路径，取消则返回None
        """
        try:
            root = self._ensure_root()
            file_path = filedialog.asksaveasfilename(
                parent=root,
                title=title,
                defaultextension=defaultextension,
                initialfile=initialfile,
                filetypes=filetypes or [("所有文件", "*.*")]
            )
            return file_path if file_path else None
        except Exception as e:
            print(f"文件保存失败: {str(e)}")
            return None

    def show_info(self, message: str, title: str = "提示") -> None:
        """
        显示信息消息

        Args:
            message: 消息内容
            title: 消息标题
        """
        try:
            root = self._ensure_root()
            messagebox.showinfo(title, message, parent=root)
        except Exception as e:
            print(f"[INFO] {title}: {message}")
            print(f"显示消息失败: {str(e)}")

    def show_warning(self, message: str, title: str = "警告") -> None:
        """
        显示警告消息

        Args:
            message: 消息内容
            title: 消息标题
        """
        try:
            root = self._ensure_root()
            messagebox.showwarning(title, message, parent=root)
        except Exception as e:
            print(f"[WARNING] {title}: {message}")
            print(f"显示警告失败: {str(e)}")

    def show_error(self, message: str, title: str = "错误") -> None:
        """
        显示错误消息

        Args:
            message: 消息内容
            title: 消息标题
        """
        try:
            root = self._ensure_root()
            messagebox.showerror(title, message, parent=root)
        except Exception as e:
            print(f"[ERROR] {title}: {message}")
            print(f"显示错误失败: {str(e)}")

    def show_result_dialog(
        self,
        title: str,
        results: Dict[str, Any],
        on_close: Optional[callable] = None
    ) -> None:
        """
        显示结果对话框（非阻塞）

        Args:
            title: 对话框标题
            results: 结果字典，格式为 {"标签": "值", ...}
            on_close: 对话框关闭时的回调函数
        """
        try:
            root = self._ensure_root()
            dialog = tk.Toplevel(root)
            dialog.title(title)
            dialog.geometry("400x300")
            dialog.resizable(True, True)

            main_frame = tk.Frame(dialog, padx=20, pady=20)
            main_frame.pack(fill=tk.BOTH, expand=True)

            title_label = tk.Label(
                main_frame,
                text=title,
                font=("Arial", 12, "bold")
            )
            title_label.pack(pady=(0, 15))

            for label, value in results.items():
                line_frame = tk.Frame(main_frame)
                line_frame.pack(fill=tk.X, pady=3, anchor=tk.W)
                tk.Label(
                    line_frame,
                    text=f"{label}:",
                    font=("Arial", 10, "bold"),
                    width=15,
                    anchor=tk.W
                ).pack(side=tk.LEFT)
                tk.Label(
                    line_frame,
                    text=str(value),
                    font=("Arial", 10),
                    anchor=tk.W
                ).pack(side=tk.LEFT, fill=tk.X, expand=True)

            def close_dialog():
                if on_close:
                    on_close()
                dialog.destroy()

            tk.Button(
                main_frame,
                text="关闭",
                command=close_dialog,
                font=("Arial", 10),
                width=10
            ).pack(pady=(15, 0))

            dialog.protocol("WM_DELETE_WINDOW", close_dialog)
        except Exception as e:
            print(f"显示结果对话框失败: {str(e)}")
            for label, value in results.items():
                print(f"  {label}: {value}")

    def select_csv_files(
        self,
        count: int = 2,
        title_template: str = "选择第{index}个CSV文件"
    ) -> List[Optional[str]]:
        """
        批量选择CSV文件的便捷接口

        Args:
            count: 需要选择的文件数量
            title_template: 标题模板，使用{index}作为占位符

        Returns:
            List[Optional[str]]: 选择的文件路径列表
        """
        results = []
        for i in range(1, count + 1):
            file_path = self.select_file(
                title=title_template.format(index=i),
                filetypes=[("CSV files", "*.csv"), ("所有文件", "*.*")]
            )
            results.append(file_path)
            if file_path is None:
                # 用户取消，停止后续选择
                break
        return results

    def show_processing_dialog(
        self,
        title: str = "处理中",
        message: str = "正在处理，请稍候..."
    ) -> Tuple[tk.Toplevel, tk.Label]:
        """
        显示处理中对话框（用于长时间操作）

        Args:
            title: 对话框标题
            message: 显示的消息

        Returns:
            Tuple[tk.Toplevel, tk.Label]: 对话框和消息标签的引用
        """
        root = self._ensure_root()
        dialog = tk.Toplevel(root)
        dialog.title(title)
        dialog.geometry("300x100")
        dialog.resizable(False, False)

        msg_label = tk.Label(
            dialog,
            text=message,
            font=("Arial", 10),
            padx=20,
            pady=20
        )
        msg_label.pack(expand=True)

        dialog.update()
        return dialog, msg_label

    def cleanup(self) -> None:
        """清理GUI资源，销毁Tk实例"""
        if self._root is not None:
            try:
                if self._root.winfo_exists():
                    self._root.destroy()
            except tk.TclError:
                pass
            except Exception as e:
                print(f"清理GUI资源时出错: {str(e)}")
            finally:
                self._root = None

    def get_root(self) -> tk.Tk:
        """
        获取Tk根窗口实例（供需要自定义界面的场景使用）

        Returns:
            tk.Tk: Tk根窗口实例
        """
        return self._ensure_root()

    def __del__(self) -> None:
        """析构函数，确保资源清理"""
        try:
            self.cleanup()
        except Exception:
            pass


# 提供模块级别的便捷函数
_default_manager: Optional[GUIManager] = None


def get_gui_manager() -> GUIManager:
    """
    获取默认的GUIManager实例

    Returns:
        GUIManager: 默认的GUIManager实例
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = GUIManager()
    return _default_manager


def select_file(title: str = "选择文件", **kwargs) -> Optional[str]:
    """便捷函数：选择单个文件"""
    return get_gui_manager().select_file(title=title, **kwargs)


def show_info(message: str, title: str = "提示") -> None:
    """便捷函数：显示信息"""
    get_gui_manager().show_info(message, title)


def show_error(message: str, title: str = "错误") -> None:
    """便捷函数：显示错误"""
    get_gui_manager().show_error(message, title)


def show_warning(message: str, title: str = "警告") -> None:
    """便捷函数：显示警告"""
    get_gui_manager().show_warning(message, title)
