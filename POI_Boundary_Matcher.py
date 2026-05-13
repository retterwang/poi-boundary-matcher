"""
POI与边界数据关联工具
功能：GUI工具，将POI数据和边界数据按位置进行关联
      支持Excel/CSV多种编码格式自动识别
      支持一对一和一对多关联模式
      可选择保留的字段
      多线程匹配，界面不卡顿
      空间索引 + prepared几何加速
"""
import logging
import threading
import queue
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import chardet
from shapely import wkt
from shapely.geometry import Point
from shapely.strtree import STRtree
from shapely.prepared import prep

try:
    import openpyxl
    HAS_EXCEL_SUPPORT = True
except ImportError:
    HAS_EXCEL_SUPPORT = False


logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def detect_encoding(file_path):
    max_bytes = 1024 * 1024
    with open(file_path, 'rb') as f:
        raw_data = f.read(max_bytes)
    result = chardet.detect(raw_data)
    encoding = result.get('encoding')
    return encoding.lower() if isinstance(encoding, str) else None


def read_csv_with_fallback(file_path, detected_encoding=None):
    encodings_to_try = []
    if detected_encoding:
        encodings_to_try.append(detected_encoding)
    encodings_to_try.extend(['utf-8-sig', 'utf-8', 'gb18030', 'gbk', 'latin1'])

    last_exc = None
    for enc in encodings_to_try:
        try:
            try:
                return pd.read_csv(file_path, encoding=enc)
            except pd.errors.ParserError as e:
                if 'Expected' in str(e) and 'fields' in str(e) and 'saw' in str(e):
                    logger.debug(f"尝试处理不一致的字段数量: {e}")
                    try:
                        return pd.read_csv(file_path, encoding=enc, on_bad_lines='skip')
                    except TypeError:
                        return pd.read_csv(file_path, encoding=enc, error_bad_lines=False)
                raise
        except UnicodeDecodeError as e:
            last_exc = e
            logger.debug(f"Encoding {enc} failed with UnicodeDecodeError: {e}")
            continue
        except Exception as e:
            last_exc = e
            logger.debug(f"Encoding {enc} failed with Exception: {e}")
            continue

    if last_exc:
        raise last_exc
    return pd.read_csv(file_path)


def read_file(file_path):
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext == '.xlsx':
        if not HAS_EXCEL_SUPPORT:
            raise Exception("未安装Excel支持库。请先安装openpyxl: pip install openpyxl")
        try:
            return pd.read_excel(file_path)
        except Exception as e:
            raise Exception(f"读取Excel文件失败: {str(e)}")
    else:
        detected = detect_encoding(file_path)
        return read_csv_with_fallback(file_path, detected_encoding=detected)


def is_wkt_format(data):
    if data is None:
        return False
    data_str = str(data).strip()
    if not data_str or data_str.lower() == 'nan':
        return False
    wkt_prefixes = ('POLYGON', 'MULTIPOLYGON', 'POINT', 'LINESTRING', 'MULTIPOINT', 'MULTILINESTRING', 'GEOMETRYCOLLECTION')
    return data_str.startswith(wkt_prefixes)


def boundaries_to_wkt(points_data):
    if pd.isna(points_data):
        return 'POLYGON EMPTY'

    points_str = str(points_data).strip()
    if not points_str or points_str.lower() == 'nan':
        return 'POLYGON EMPTY'

    points = points_str.split(';')
    wkt_points = []
    for point in points:
        point = point.strip()
        if not point:
            continue
        if '_' not in point:
            raise ValueError(f"经纬度格式错误: {point}（应为'经度_纬度'格式）")

        lon, lat = point.split('_', 1)
        try:
            float(lon)
            float(lat)
        except ValueError:
            raise ValueError(f"经纬度值错误: {point}（应为数字）")

        wkt_points.append(f'{lon.strip()} {lat.strip()}')

    if len(wkt_points) < 3:
        raise ValueError("多边形至少需要3个点")

    if wkt_points[0] != wkt_points[-1]:
        wkt_points.append(wkt_points[0])

    return f'POLYGON ((' + ', '.join(wkt_points) + '))'


def validate_coordinates(lon, lat):
    try:
        lon_f = float(lon)
        lat_f = float(lat)
    except (ValueError, TypeError):
        return None, None
    if not (-180 <= lon_f <= 180 and -90 <= lat_f <= 90):
        return None, None
    return lon_f, lat_f


class POIBoundaryMatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("POI与边界数据关联工具")
        self.root.geometry("920x600")
        self.root.minsize(800, 500)

        self.setup_styles()

        self.poi_df = None
        self.boundary_df = None
        self.poi_geometry_col = None
        self.boundary_geometry_col = None
        self.poi_lon_col = None
        self.poi_lat_col = None
        self.result_df = None
        self.cancel_flag = False
        self._matching_running = False
        self._msg_queue = queue.Queue()

        self.poi_field_vars = {}
        self.boundary_field_vars = {}

        self.create_widgets()

    def setup_styles(self):
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 10, 'bold'))
        style.configure('Field.TLabel', font=('Arial', 9))
        style.configure('Primary.TButton', font=('Arial', 10))
        style.configure('Status.TLabel', font=('Arial', 9), relief=tk.SUNKEN, anchor=tk.W)
        style.configure('Small.TButton', font=('Arial', 8), padding=2)

        style.configure('TFrame', padding=5)
        style.configure('TLabelframe', padding=8)
        style.configure('TLabelframe.Label', font=('Arial', 10, 'bold'))

    def _get_filetypes(self):
        filetypes = [("所有支持的文件", "*.csv;*.xlsx")]
        if HAS_EXCEL_SUPPORT:
            filetypes.extend([("CSV文件", "*.csv"), ("Excel文件", "*.xlsx")])
        else:
            filetypes.append(("CSV文件", "*.csv"))
        filetypes.append(("所有文件", "*.*"))
        return filetypes

    def create_widgets(self):
        self.canvas = tk.Canvas(self.root, bg='#f0f0f0', highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, padding=0)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas_window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ========== 文件上传区域 - 左右并排 ==========
        file_frame = ttk.LabelFrame(self.scrollable_frame, text="数据文件上传", padding="10")
        file_frame.pack(fill=tk.X, pady=(10, 5), padx=10)

        # POI文件上传区 - 左侧
        poi_file_frame = ttk.Frame(file_frame)
        poi_file_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        ttk.Label(poi_file_frame, text="POI数据:", style='Header.TLabel').pack(anchor=tk.W)
        poi_input_frame = ttk.Frame(poi_file_frame)
        poi_input_frame.pack(fill=tk.X, pady=5)
        self.poi_path_var = tk.StringVar()
        ttk.Entry(poi_input_frame, textvariable=self.poi_path_var, width=30).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(poi_input_frame, text="上传", command=self.upload_poi).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(poi_input_frame, text="预览", command=lambda: self._preview_data('poi'), style='Small.TButton').pack(side=tk.LEFT)
        self.poi_status_label = ttk.Label(poi_file_frame, text="未上传", foreground='gray')
        self.poi_status_label.pack(anchor=tk.W)

        # 边界文件上传区 - 右侧
        boundary_file_frame = ttk.Frame(file_frame)
        boundary_file_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(boundary_file_frame, text="边界数据:", style='Header.TLabel').pack(anchor=tk.W)
        boundary_input_frame = ttk.Frame(boundary_file_frame)
        boundary_input_frame.pack(fill=tk.X, pady=5)
        self.boundary_path_var = tk.StringVar()
        ttk.Entry(boundary_input_frame, textvariable=self.boundary_path_var, width=30).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(boundary_input_frame, text="上传", command=self.upload_boundary).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(boundary_input_frame, text="预览", command=lambda: self._preview_data('boundary'), style='Small.TButton').pack(side=tk.LEFT)
        self.boundary_status_label = ttk.Label(boundary_file_frame, text="未上传", foreground='gray')
        self.boundary_status_label.pack(anchor=tk.W)

        # ========== 经纬度选择区域 ==========
        lat_lon_frame = ttk.LabelFrame(self.scrollable_frame, text="经纬度字段配置", padding="10")
        lat_lon_frame.pack(fill=tk.X, pady=5, padx=10)

        # POI经纬度 - 左侧
        poi_latlon_frame = ttk.Frame(lat_lon_frame)
        poi_latlon_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 20))

        ttk.Label(poi_latlon_frame, text="POI经纬度:", style='Header.TLabel').pack(anchor=tk.W)
        poi_latlon_input = ttk.Frame(poi_latlon_frame)
        poi_latlon_input.pack(fill=tk.X, pady=5)
        ttk.Label(poi_latlon_input, text="经度:").pack(side=tk.LEFT)
        self.poi_lon_combo = ttk.Combobox(poi_latlon_input, width=18, state='readonly')
        self.poi_lon_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(poi_latlon_input, text="纬度:").pack(side=tk.LEFT, padx=(10, 0))
        self.poi_lat_combo = ttk.Combobox(poi_latlon_input, width=18, state='readonly')
        self.poi_lat_combo.pack(side=tk.LEFT, padx=5)

        # 边界几何字段 - 右侧
        boundary_geom_frame = ttk.Frame(lat_lon_frame)
        boundary_geom_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(boundary_geom_frame, text="边界几何字段:", style='Header.TLabel').pack(anchor=tk.W)
        boundary_geom_input = ttk.Frame(boundary_geom_frame)
        boundary_geom_input.pack(fill=tk.X, pady=5)
        self.boundary_geom_combo = ttk.Combobox(boundary_geom_input, width=22, state='readonly')
        self.boundary_geom_combo.pack(side=tk.LEFT, padx=5)
        self.boundary_geom_combo.bind('<<ComboboxSelected>>', self.on_boundary_geom_selected)

        # ========== 字段选择区域 - 带全选/反选按钮 ==========
        field_selection_frame = ttk.Frame(self.scrollable_frame)
        field_selection_frame.pack(fill=tk.X, pady=5, padx=10)

        # POI字段选择 - 左侧
        poi_field_frame = ttk.LabelFrame(field_selection_frame, text="POI字段选择", padding="10")
        poi_field_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        poi_btn_frame = ttk.Frame(poi_field_frame)
        poi_btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(poi_btn_frame, text="全选", command=lambda: self._toggle_all_fields(self.poi_field_vars, True),
                   style='Small.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(poi_btn_frame, text="全不选", command=lambda: self._toggle_all_fields(self.poi_field_vars, False),
                   style='Small.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(poi_btn_frame, text="反选", command=lambda: self._invert_fields(self.poi_field_vars),
                   style='Small.TButton').pack(side=tk.LEFT, padx=2)

        self.poi_fields_container = ttk.Frame(poi_field_frame)
        self.poi_fields_container.pack(fill=tk.BOTH, expand=True)
        self.poi_field_placeholder = ttk.Label(self.poi_fields_container, text="请先上传POI数据文件", foreground='gray')
        self.poi_field_placeholder.pack(pady=20)

        # 边界字段选择 - 右侧
        boundary_field_frame = ttk.LabelFrame(field_selection_frame, text="边界字段选择", padding="10")
        boundary_field_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        boundary_btn_frame = ttk.Frame(boundary_field_frame)
        boundary_btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(boundary_btn_frame, text="全选", command=lambda: self._toggle_all_fields(self.boundary_field_vars, True),
                   style='Small.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(boundary_btn_frame, text="全不选", command=lambda: self._toggle_all_fields(self.boundary_field_vars, False),
                   style='Small.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(boundary_btn_frame, text="反选", command=lambda: self._invert_fields(self.boundary_field_vars),
                   style='Small.TButton').pack(side=tk.LEFT, padx=2)

        self.boundary_fields_container = ttk.Frame(boundary_field_frame)
        self.boundary_fields_container.pack(fill=tk.BOTH, expand=True)
        self.boundary_field_placeholder = ttk.Label(self.boundary_fields_container, text="请先上传边界数据文件", foreground='gray')
        self.boundary_field_placeholder.pack(pady=20)

        # ========== 关联选项区域 ==========
        options_frame = ttk.LabelFrame(self.scrollable_frame, text="关联选项", padding="10")
        options_frame.pack(fill=tk.X, pady=5, padx=10)

        mode_frame = ttk.Frame(options_frame)
        mode_frame.pack(fill=tk.X)
        ttk.Label(mode_frame, text="关联模式:").pack(side=tk.LEFT)
        self.match_mode_var = tk.StringVar(value="one_to_one")
        ttk.Radiobutton(mode_frame, text="一对一关联", variable=self.match_mode_var,
                        value="one_to_one").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="一对多关联", variable=self.match_mode_var,
                        value="one_to_many").pack(side=tk.LEFT)

        self.keep_unmatched_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="保留未匹配的POI记录（boundary字段留空）",
                        variable=self.keep_unmatched_var).pack(anchor=tk.W, pady=(5, 0))

        # ========== 按钮区域 ==========
        btn_frame = ttk.Frame(self.scrollable_frame)
        btn_frame.pack(fill=tk.X, pady=10, padx=10)

        self.match_btn = ttk.Button(btn_frame, text="开始关联", command=self.start_matching,
                                    state='disabled', style='Primary.TButton')
        self.match_btn.pack(side=tk.LEFT, padx=5)

        self.cancel_btn = ttk.Button(btn_frame, text="取消", command=self.cancel_matching,
                                     state='disabled', style='Primary.TButton')
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = ttk.Button(btn_frame, text="保存结果", command=self.save_results,
                                   state='disabled', style='Primary.TButton')
        self.save_btn.pack(side=tk.LEFT, padx=5)

        # ========== 进度条区域 ==========
        progress_frame = ttk.Frame(self.scrollable_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10), padx=10)

        self.progress_label = ttk.Label(progress_frame, text="", width=35)
        self.progress_label.pack(side=tk.LEFT, padx=(0, 10))

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=300)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress_bar['value'] = 0

        # ========== 状态栏 ==========
        self.status_label = ttk.Label(self.scrollable_frame, text="就绪", style='Status.TLabel')
        self.status_label.pack(fill=tk.X, pady=(0, 10), padx=10)

        self._bind_mousewheel()

    def _on_canvas_configure(self, event):
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window_id, width=canvas_width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_mousewheel(self):
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_shift_mousewheel(event):
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_enter(event):
            self.canvas.bind_all("<MouseWheel>", on_mousewheel)
            self.canvas.bind_all("<Shift-MouseWheel>", on_shift_mousewheel)

        def on_leave(event):
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Shift-MouseWheel>")

        self.canvas.bind("<Enter>", on_enter)
        self.canvas.bind("<Leave>", on_leave)

    def _toggle_all_fields(self, field_vars, value):
        for var in field_vars.values():
            var.set(value)

    def _invert_fields(self, field_vars):
        for var in field_vars.values():
            var.set(not var.get())

    def _create_checkbox_grid(self, container, field_vars, columns=3):
        for widget in container.winfo_children():
            widget.destroy()

        fields = list(field_vars.keys())

        for idx, field in enumerate(fields):
            row = idx // columns
            col = idx % columns
            var = field_vars[field]
            cb = tk.Checkbutton(container, text=field, variable=var)
            cb.grid(row=row, column=col, sticky=tk.W, padx=10, pady=3)

    def _preview_data(self, data_type):
        df = self.poi_df if data_type == 'poi' else self.boundary_df
        if df is None:
            messagebox.showinfo("提示", "请先上传数据文件")
            return

        preview_df = df.head(10)
        title = "POI数据预览" if data_type == 'poi' else "边界数据预览"

        preview_win = tk.Toplevel(self.root)
        preview_win.title(title)
        preview_win.geometry("800x400")

        frame = ttk.Frame(preview_win)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        info_label = ttk.Label(frame, text=f"共 {len(df)} 行，显示前 {len(preview_df)} 行 | 列: {', '.join(df.columns.tolist())}",
                               style='Field.TLabel')
        info_label.pack(anchor=tk.W, pady=(0, 5))

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        cols = list(preview_df.columns)
        tree = ttk.Treeview(tree_frame, columns=cols, show='headings',
                            yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        tree_scroll_y.config(command=tree.yview)
        tree_scroll_x.config(command=tree.xview)

        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(fill=tk.BOTH, expand=True)

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=100, minwidth=60)

        for _, row in preview_df.iterrows():
            values = [str(row[col])[:80] for col in cols]
            tree.insert('', tk.END, values=values)

    def upload_poi(self):
        file_path = filedialog.askopenfilename(title="选择POI数据文件", filetypes=self._get_filetypes())
        if not file_path:
            return

        try:
            self.poi_df = read_file(file_path)
            self.poi_path_var.set(file_path)

            cols = list(self.poi_df.columns)
            self.poi_lon_combo['values'] = cols
            self.poi_lat_combo['values'] = cols

            self.poi_field_vars.clear()
            for col in cols:
                var = tk.BooleanVar(value=True)
                self.poi_field_vars[col] = var
            self._create_checkbox_grid(self.poi_fields_container, self.poi_field_vars, columns=3)

            lon_candidates = ['lon', 'longitude', 'lng', 'x', '经度', 'lon_col', 'longitude_col']
            lat_candidates = ['lat', 'latitude', 'y', '纬度', 'lat_col', 'latitude_col']

            lon_idx = None
            lat_idx = None
            for i, col in enumerate(cols):
                col_lower = col.lower()
                if lon_idx is None and any(c in col_lower for c in lon_candidates):
                    lon_idx = i
                if lat_idx is None and any(c in col_lower for c in lat_candidates):
                    lat_idx = i

            if lon_idx is not None:
                self.poi_lon_combo.current(lon_idx)
            if lat_idx is not None:
                self.poi_lat_combo.current(lat_idx)

            if lon_idx is None or lat_idx is None:
                messagebox.showinfo("提示", "未自动检测到经纬度字段，请手动选择")

            self.poi_status_label.config(text=f"已上传 ({len(self.poi_df)} 行)", foreground='green')
            self.poi_lon_col = self.poi_lon_combo.get()
            self.poi_lat_col = self.poi_lat_combo.get()
            self.update_ui_state()

        except Exception as e:
            messagebox.showerror("错误", f"读取POI文件失败: {str(e)}")
            self.poi_status_label.config(text="上传失败", foreground='red')

    def upload_boundary(self):
        file_path = filedialog.askopenfilename(title="选择边界数据文件", filetypes=self._get_filetypes())
        if not file_path:
            return

        try:
            self.boundary_df = read_file(file_path)
            self.boundary_path_var.set(file_path)

            cols = list(self.boundary_df.columns)

            self.boundary_field_vars.clear()
            for col in cols:
                var = tk.BooleanVar(value=True)
                self.boundary_field_vars[col] = var
            self._create_checkbox_grid(self.boundary_fields_container, self.boundary_field_vars, columns=3)

            if 'boundaries' in cols:
                self.status_label.config(text="检测到boundaries字段，正在转换...")
                self.root.update()
                try:
                    self.boundary_df['boundary_wkt'] = self.boundary_df['boundaries'].apply(boundaries_to_wkt)
                    self.boundary_geometry_col = 'boundary_wkt'
                    self.boundary_geom_combo['values'] = ['boundaries (自动)', 'boundary_wkt']
                    self.boundary_geom_combo.current(1)
                    self.boundary_status_label.config(text=f"已上传并转换WKT ({len(self.boundary_df)} 行)", foreground='green')
                except Exception as e:
                    messagebox.showerror("错误", f"boundaries字段转换失败: {str(e)}")
                    self.boundary_status_label.config(text="转换失败", foreground='red')
                    return
            else:
                wkt_col_idx = None
                for i, col in enumerate(cols):
                    if len(self.boundary_df) > 0 and is_wkt_format(self.boundary_df[col].iloc[0]):
                        wkt_col_idx = i
                        break

                if wkt_col_idx is not None:
                    self.boundary_geom_combo['values'] = list(cols)
                    self.boundary_geom_combo.current(wkt_col_idx)
                    self.on_boundary_geom_selected()
                    self.boundary_status_label.config(text=f"已自动检测到WKT字段: {cols[wkt_col_idx]}", foreground='green')
                else:
                    self.boundary_geom_combo['values'] = list(cols)
                    if len(cols) > 0:
                        self.boundary_geom_combo.current(0)
                        self.on_boundary_geom_selected()
                    self.boundary_status_label.config(text="请选择边界几何字段", foreground='orange')

            self.update_ui_state()

        except Exception as e:
            messagebox.showerror("错误", f"读取边界文件失败: {str(e)}")
            self.boundary_status_label.config(text="上传失败", foreground='red')

    def on_boundary_geom_selected(self, event=None):
        selected_geom_col = self.boundary_geom_combo.get()
        if not selected_geom_col or self.boundary_df is None:
            return

        if selected_geom_col == 'boundaries (自动)':
            try:
                self.boundary_df['boundary_wkt'] = self.boundary_df['boundaries'].apply(boundaries_to_wkt)
                self.boundary_geometry_col = 'boundary_wkt'
                self.boundary_status_label.config(text="边界几何转换成功", foreground='green')
            except Exception as e:
                messagebox.showerror("错误", f"boundaries字段转换失败: {str(e)}")
                self.boundary_status_label.config(text="转换失败", foreground='red')
                return
        elif selected_geom_col in self.boundary_df.columns:
            geom_data = self.boundary_df[selected_geom_col].iloc[0] if len(self.boundary_df) > 0 else None
            if is_wkt_format(geom_data):
                self.boundary_df['boundary_wkt'] = self.boundary_df[selected_geom_col]
                self.boundary_geometry_col = 'boundary_wkt'
                self.boundary_status_label.config(text=f"使用已有WKT字段: {selected_geom_col}", foreground='green')
            else:
                try:
                    self.boundary_df['boundary_wkt'] = self.boundary_df[selected_geom_col].apply(boundaries_to_wkt)
                    self.boundary_geometry_col = 'boundary_wkt'
                    self.boundary_status_label.config(text=f"已将 {selected_geom_col} 转换为WKT", foreground='green')
                except Exception as e:
                    messagebox.showerror("错误", f"字段 {selected_geom_col} 转换失败: {str(e)}")
                    self.boundary_status_label.config(text="转换失败", foreground='red')
                    return

        self.update_ui_state()

    def update_ui_state(self):
        if self.poi_df is not None and self.boundary_df is not None:
            if 'boundary_wkt' in self.boundary_df.columns:
                self.match_btn.config(state='normal')
                self.status_label.config(text="数据已就绪，可以开始关联")

    def get_selected_fields(self):
        poi_selected = [col for col, var in self.poi_field_vars.items() if var.get()]
        boundary_selected = [col for col, var in self.boundary_field_vars.items() if var.get()]
        return poi_selected, boundary_selected

    def _validate_matching_params(self):
        lon_col = self.poi_lon_combo.get()
        lat_col = self.poi_lat_combo.get()

        if not lon_col or not lat_col:
            messagebox.showerror("错误", "请选择经度和纬度字段")
            return None

        if lon_col not in self.poi_df.columns or lat_col not in self.poi_df.columns:
            messagebox.showerror("错误", "选择的经纬度字段不存在")
            return None

        poi_selected_fields, boundary_selected_fields = self.get_selected_fields()

        if not poi_selected_fields:
            messagebox.showerror("错误", "请选择至少一个POI字段")
            return None

        if not boundary_selected_fields:
            messagebox.showerror("错误", "请选择至少一个边界字段")
            return None

        if 'boundary_wkt' not in self.boundary_df.columns:
            messagebox.showerror("错误", "边界数据缺少boundary_wkt字段")
            return None

        match_mode = self.match_mode_var.get()
        keep_unmatched = self.keep_unmatched_var.get()

        return {
            'lon_col': lon_col,
            'lat_col': lat_col,
            'poi_selected_fields': poi_selected_fields,
            'boundary_selected_fields': boundary_selected_fields,
            'match_mode': match_mode,
            'keep_unmatched': keep_unmatched,
        }

    def start_matching(self):
        params = self._validate_matching_params()
        if params is None:
            return

        self.cancel_flag = False
        self._matching_running = True
        self.match_btn.config(state='disabled')
        self.cancel_btn.config(state='normal')
        self.save_btn.config(state='disabled')
        self.progress_bar['value'] = 0
        self.progress_label.config(text="准备中...")
        self.status_label.config(text="正在关联...")

        self._msg_queue = queue.Queue()

        thread = threading.Thread(target=self._do_matching, args=(params,), daemon=True)
        thread.start()

        self._poll_queue()

    def _poll_queue(self):
        try:
            while True:
                msg = self._msg_queue.get_nowait()
                msg_type = msg.get('type')

                if msg_type == 'progress':
                    self.progress_bar['value'] = msg['value']
                    self.progress_label.config(text=msg['text'])
                elif msg_type == 'status':
                    self.status_label.config(text=msg['text'])
                elif msg_type == 'done':
                    self._matching_running = False
                    self.result_df = msg.get('result_df')
                    self.match_btn.config(state='normal')
                    self.cancel_btn.config(state='disabled')
                    if self.result_df is not None and len(self.result_df) > 0:
                        self.save_btn.config(state='normal')
                    self.progress_bar['value'] = 100
                    self.progress_label.config(text=msg.get('progress_text', '完成'))
                    self.status_label.config(text=msg.get('status_text', '完成'))
                    messagebox.showinfo("成功", msg.get('message', '关联完成'))
                    return
                elif msg_type == 'done_empty':
                    self._matching_running = False
                    self.match_btn.config(state='normal')
                    self.cancel_btn.config(state='disabled')
                    self.progress_bar['value'] = 100
                    self.progress_label.config(text="完成")
                    self.status_label.config(text=msg.get('status_text', '没有找到匹配结果'))
                    messagebox.showwarning("结果", msg.get('message', '没有找到任何匹配结果'))
                    return
                elif msg_type == 'error':
                    self._matching_running = False
                    self.match_btn.config(state='normal')
                    self.cancel_btn.config(state='disabled')
                    messagebox.showerror("错误", msg.get('message', '关联过程出错'))
                    return
                elif msg_type == 'cancelled':
                    self._matching_running = False
                    self.match_btn.config(state='normal')
                    self.cancel_btn.config(state='disabled')
                    if msg.get('result_df') is not None and len(msg['result_df']) > 0:
                        self.result_df = msg['result_df']
                        self.save_btn.config(state='normal')
                    self.progress_bar['value'] = 0
                    self.progress_label.config(text="已取消")
                    self.status_label.config(text=msg.get('status_text', '已取消'))
                    return
        except queue.Empty:
            pass

        if self._matching_running:
            self.root.after(150, self._poll_queue)

    def _do_matching(self, params):
        try:
            lon_col = params['lon_col']
            lat_col = params['lat_col']
            poi_selected_fields = params['poi_selected_fields']
            boundary_selected_fields = params['boundary_selected_fields']
            match_mode = params['match_mode']
            keep_unmatched = params['keep_unmatched']

            total_poi = len(self.poi_df)
            total_boundaries = len(self.boundary_df)

            self._msg_queue.put({'type': 'status', 'text': f"正在解析 {total_boundaries} 个边界..."})
            self._msg_queue.put({'type': 'progress', 'value': 0, 'text': "解析边界数据..."})

            valid_geoms = []
            prepared_geoms = []
            valid_idx_to_boundary_idx = []
            for idx, row in self.boundary_df.iterrows():
                try:
                    geom_wkt = row['boundary_wkt']
                    if geom_wkt != 'POLYGON EMPTY':
                        geom = wkt.loads(geom_wkt)
                        valid_geoms.append(geom)
                        prepared_geoms.append(prep(geom))
                        valid_idx_to_boundary_idx.append(idx)
                except Exception as e:
                    logger.debug(f"解析边界几何失败 idx={idx}: {e}")

            self._msg_queue.put({'type': 'status', 'text': f"正在构建空间索引 ({len(valid_geoms)} 个有效边界)..."})
            self._msg_queue.put({'type': 'progress', 'value': 5, 'text': "构建空间索引..."})

            tree = STRtree(valid_geoms)

            self._msg_queue.put({'type': 'progress', 'value': 10, 'text': "解析完成，开始关联..."})
            self._msg_queue.put({'type': 'status', 'text': "正在进行空间关联..."})

            boundary_df_cols = set(self.boundary_df.columns)
            boundary_selected_in_df = [col for col in boundary_selected_fields if col in boundary_df_cols]

            needed_cols = list(set(poi_selected_fields + [lon_col, lat_col]))
            poi_subset = self.poi_df[needed_cols]

            results = []
            matched_count = 0
            invalid_coord_count = 0
            last_progress_pct = 10

            for row in poi_subset.itertuples():
                if self.cancel_flag:
                    result_df = pd.DataFrame(results) if results else None
                    self._msg_queue.put({
                        'type': 'cancelled',
                        'result_df': result_df,
                        'status_text': f"已取消关联，已处理部分结果"
                    })
                    return

                poi_idx = row.Index
                try:
                    lon_val = getattr(row, lon_col)
                    lat_val = getattr(row, lat_col)
                    lon, lat = validate_coordinates(lon_val, lat_val)
                    if lon is None or lat is None:
                        invalid_coord_count += 1
                        continue
                except (ValueError, TypeError, AttributeError):
                    invalid_coord_count += 1
                    continue

                point = Point(lon, lat)
                matched_boundaries = []

                candidate_indices = tree.query(point)
                for valid_idx in candidate_indices:
                    try:
                        if prepared_geoms[valid_idx].contains(point) or valid_geoms[valid_idx].touches(point):
                            matched_boundaries.append(valid_idx_to_boundary_idx[valid_idx])
                            if match_mode == "one_to_one":
                                break
                    except Exception as e:
                        logger.debug(f"判断点是否在多边形内失败: {e}")
                        continue

                poi_row_dict = {col: getattr(row, col) for col in poi_selected_fields}

                if match_mode == "one_to_one":
                    if matched_boundaries:
                        boundary_idx = matched_boundaries[0]
                        row_data = dict(poi_row_dict)
                        row_data.update({f"bd_{col}": self.boundary_df.loc[boundary_idx, col]
                                         for col in boundary_selected_in_df})
                        row_data['matched_boundary_idx'] = boundary_idx
                        results.append(row_data)
                        matched_count += 1
                    elif keep_unmatched:
                        row_data = dict(poi_row_dict)
                        row_data.update({f"bd_{col}": None for col in boundary_selected_fields})
                        row_data['matched_boundary_idx'] = None
                        results.append(row_data)
                else:
                    if matched_boundaries:
                        for boundary_idx in matched_boundaries:
                            row_data = dict(poi_row_dict)
                            row_data.update({f"bd_{col}": self.boundary_df.loc[boundary_idx, col]
                                             for col in boundary_selected_in_df})
                            row_data['matched_boundary_idx'] = boundary_idx
                            results.append(row_data)
                        matched_count += len(matched_boundaries)
                    elif keep_unmatched:
                        row_data = dict(poi_row_dict)
                        row_data.update({f"bd_{col}": None for col in boundary_selected_fields})
                        row_data['matched_boundary_idx'] = None
                        results.append(row_data)

                current_pct = 10 + int((poi_idx / total_poi) * 90)
                if current_pct >= last_progress_pct + 2:
                    last_progress_pct = current_pct
                    self._msg_queue.put({
                        'type': 'progress',
                        'value': current_pct,
                        'text': f"关联进度: {poi_idx}/{total_poi} ({current_pct}%)"
                    })

            if invalid_coord_count > 0:
                logger.warning(f"共 {invalid_coord_count} 条POI经纬度无效或超出范围，已跳过")

            if results:
                result_df = pd.DataFrame(results)
                self._msg_queue.put({
                    'type': 'done',
                    'result_df': result_df,
                    'progress_text': f"完成! 共 {len(result_df)} 条结果",
                    'status_text': f"关联完成: {len(result_df)} 条结果，已匹配 {matched_count} 条",
                    'message': f"关联完成！\n共生成 {len(result_df)} 条关联结果"
                               + (f"\n（{invalid_coord_count} 条POI经纬度无效已跳过）" if invalid_coord_count > 0 else "")
                })
            else:
                msg = "没有找到任何匹配结果"
                if invalid_coord_count > 0:
                    msg += f"\n（{invalid_coord_count} 条POI经纬度无效已跳过）"
                self._msg_queue.put({
                    'type': 'done_empty',
                    'status_text': '没有找到匹配结果',
                    'message': msg
                })

        except Exception as e:
            logger.exception("关联过程出错")
            self._msg_queue.put({'type': 'error', 'message': f"关联过程出错: {str(e)}"})

    def cancel_matching(self):
        if self._matching_running:
            self.cancel_flag = True
            self.status_label.config(text="正在取消关联...")
            self.cancel_btn.config(state='disabled')

    def save_results(self):
        if self.result_df is None or len(self.result_df) == 0:
            messagebox.showwarning("警告", "没有可保存的结果")
            return

        save_dialog = tk.Toplevel(self.root)
        save_dialog.title("保存设置")
        save_dialog.geometry("350x200")
        save_dialog.resizable(False, False)
        save_dialog.transient(self.root)
        save_dialog.grab_set()

        ttk.Label(save_dialog, text="文件格式:", style='Header.TLabel').pack(anchor=tk.W, padx=15, pady=(15, 5))
        format_var = tk.StringVar(value="csv")
        format_frame = ttk.Frame(save_dialog)
        format_frame.pack(fill=tk.X, padx=15)
        ttk.Radiobutton(format_frame, text="CSV", variable=format_var, value="csv").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="Excel (.xlsx)", variable=format_var, value="xlsx").pack(side=tk.LEFT, padx=5)

        ttk.Label(save_dialog, text="CSV编码:", style='Header.TLabel').pack(anchor=tk.W, padx=15, pady=(10, 5))
        encoding_var = tk.StringVar(value="utf-8-sig")
        encoding_frame = ttk.Frame(save_dialog)
        encoding_frame.pack(fill=tk.X, padx=15)
        ttk.Radiobutton(encoding_frame, text="UTF-8 (BOM)", variable=encoding_var, value="utf-8-sig").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(encoding_frame, text="GBK", variable=encoding_var, value="gbk").pack(side=tk.LEFT, padx=5)

        def do_save():
            fmt = format_var.get()
            enc = encoding_var.get()

            ext = ".xlsx" if fmt == "xlsx" else ".csv"
            filetypes = [("Excel文件", "*.xlsx")] if fmt == "xlsx" else [("CSV文件", "*.csv")]
            filetypes.append(("所有文件", "*.*"))

            save_path = filedialog.asksaveasfilename(
                title="保存关联结果",
                defaultextension=ext,
                filetypes=filetypes,
                parent=save_dialog
            )

            if not save_path:
                return

            try:
                file_ext = os.path.splitext(save_path)[1].lower()
                if file_ext == '.xlsx':
                    self.result_df.to_excel(save_path, index=False)
                else:
                    self.result_df.to_csv(save_path, index=False, encoding=enc)
                messagebox.showinfo("成功", f"结果已保存至:\n{save_path}", parent=save_dialog)
                self.status_label.config(text=f"已保存至: {save_path}")
                save_dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}", parent=save_dialog)

        btn_frame = ttk.Frame(save_dialog)
        btn_frame.pack(fill=tk.X, pady=15, padx=15)
        ttk.Button(btn_frame, text="选择路径并保存", command=do_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=save_dialog.destroy).pack(side=tk.LEFT, padx=5)


def main():
    root = tk.Tk()
    app = POIBoundaryMatcherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
