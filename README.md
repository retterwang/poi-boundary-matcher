# POI Boundary Matcher

中文 | [English](README_EN.md)

一个强大的 POI（兴趣点）与行政区划边界数据关联工具，支持空间点面匹配，带有友好的图形用户界面。

## ✨ 功能特性

- 📁 **多格式支持**：支持 CSV 和 Excel (.xlsx) 文件读取
- 🔍 **智能编码识别**：自动检测文件编码（UTF-8、GBK、GB18030 等）
- 🎯 **灵活匹配模式**：
  - 一对一关联：每个 POI 只匹配一个边界
  - 一对多关联：POI 可匹配多个边界（如跨区域 POI）
- ⚙️ **字段自定义**：可自由选择需要保留的 POI 和边界字段
- 🚀 **高性能**：
  - 使用 Shapely STRtree 空间索引加速
  - 使用 PreparedGeometry 优化空间查询
  - 多线程匹配，界面不卡顿
- 💾 **多种输出格式**：支持保存为 CSV 或 Excel
- 📊 **实时进度**：显示匹配进度和统计信息

## 📦 安装

### 依赖库

```bash
pip install pandas shapely chardet
# 如果需要 Excel 支持，还需安装：
pip install openpyxl
```

### 系统要求

- Python 3.7+
- Windows / macOS / Linux

## 🚀 快速开始

### 方法 1：直接运行 Python 脚本

```bash
python POI_Boundary_Matcher.py
```

### 方法 2：使用打包好的可执行文件

如果你有打包好的 .exe 文件，可以直接双击运行（Windows）。

## 📖 使用指南

### 步骤 1：准备数据

#### POI 数据文件
需要包含经纬度字段，例如：

**CSV 格式（支持多种编码）：**
```csv
id,name,longitude,latitude,address
1,星巴克,116.404,39.905,北京市朝阳区
2,麦当劳,121.473,31.230,上海市黄浦区
```

**Excel 格式 (.xlsx)：**
同上，但保存为 Excel 文件。

#### 边界数据文件
需要包含 WKT 格式的几何字段，或者包含坐标点字符串的字段。

**WKT 格式示例：**
```csv
id,name,boundary_wkt
1,朝阳区,"POLYGON ((116.4 39.9, 116.5 39.9, 116.5 40.0, 116.4 40.0, 116.4 39.9))"
2,海淀区,"POLYGON ((116.3 39.9, 116.4 39.9, 116.4 40.0, 116.3 40.0, 116.3 39.9))"
```

**坐标点字符串格式（自动转换）：**
```csv
id,name,boundaries
1,朝阳区,"116.4_39.9;116.5_39.9;116.5_40.0;116.4_40.0;116.4_39.9"
2,海淀区,"116.3_39.9;116.4_39.9;116.4_40.0;116.3_40.0;116.3_39.9"
```

⚠️ **坐标格式说明：**
- 支持 `经度_纬度` 格式（下划线分隔）
- 程序会自动将坐标点字符串转换为 WKT 格式

### 步骤 2：运行程序

1. 启动程序
2. 点击「上传」按钮选择 POI 数据文件
3. 点击「上传」按钮选择边界数据文件
4. 程序会自动检测经纬度字段和边界几何字段

### 步骤 3：配置匹配选项

- **经纬度字段**：确认程序自动选择的经纬度字段是否正确
- **边界几何字段**：确认边界几何字段是否正确（支持自动转换）
- **字段选择**：
  - 选择需要保留的 POI 字段
  - 选择需要保留的边界字段
  - 支持全选、全不选、反选
- **关联模式**：
  - 一对一关联：每个 POI 只匹配一个边界（默认）
  - 一对多关联：POI 可匹配多个边界
- **保留未匹配记录**：勾选后，未匹配的 POI 也会出现在结果中（边界字段为空的）

### 步骤 4：开始匹配

1. 点击「开始关联」按钮
2. 查看进度条和状态信息
3. 等待匹配完成

### 步骤 5：保存结果

1. 匹配完成后，点击「保存结果」按钮
2. 选择保存格式（CSV 或 Excel）
3. 选择 CSV 编码（UTF-8 with BOM 或 GBK）
4. 选择保存路径

## 📊 输出结果

结果文件包含以下字段：

- 所有选中的 POI 字段
- 所有选中的边界字段（带 `bd_` 前缀）
- `matched_boundary_idx`：匹配的边界索引

**示例输出（CSV）：**
```csv
id,name,longitude,latitude,bd_name,bd_id,matched_boundary_idx
1,星巴克,116.404,39.905,朝阳区,1,0
2,麦当劳,121.473,31.230,黄浦区,2,5
```

## 🔧 高级功能

### 1. 数据预览

- 上传文件后，点击「预览」按钮可以查看数据前 10 行
- 方便确认数据格式和字段名称

### 2. 取消匹配

- 匹配过程中可以点击「取消」按钮
- 已匹配的结果会保存（如果有的话）

### 3. 批量处理

- 支持处理大规模数据（万级 POI + 千级边界）
- 使用空间索引，性能优越

## ⚠️ 注意事项

1. **坐标系统**：确保 POI 的经纬度是 WGS84 坐标系（GPS 坐标）
2. **边界方向**：多边形坐标需要按顺时针或逆时针顺序排列
3. **闭合检查**：多边形首尾坐标需要相同（程序会自动处理）
4. **内存占用**：处理大量数据时，确保有足够的内存
5. **编码问题**：如果 CSV 文件读取失败，尝试用其他编码保存

## 🐛 常见问题

### Q1：程序无法启动？

**A：** 确保已安装所有依赖库：
```bash
pip install pandas shapely chardet openpyxl
```

### Q2：Excel 文件无法读取？

**A：** 需要安装 `openpyxl` 库：
```bash
pip install openpyxl
```

### Q3：匹配结果为空？

**A：** 可能的原因：
- POI 经纬度坐标不在边界范围内
- 坐标系统不匹配（需要 WGS84 坐标）
- 边界数据格式错误

### Q4：程序卡死或无响应？

**A：** 
- 数据量过大，等待一段时间
- 检查数据格式是否正确
- 查看命令行输出的错误信息

### Q5：如何提高效率？

**A：**
- 使用一对一关联模式（比一对多快）
- 减少保留的字段数量
- 确保边界数据是 WKT 格式（避免实时转换）

## 🧰 附带工具

仓库还包含两个独立的小工具：

### wkt_converter.py — WKT 边界格式双向转换

WKT 格式与 `经度_纬度;经度_纬度;...` 边界坐标串的双向转换工具，纯 Python 实现，无外部依赖，支持 GUI 和命令行两种方式。

```bash
# 图形界面
python wkt_converter.py gui

# 命令行：boundaries 格式转 WKT
python wkt_converter.py to-wkt input.csv -o output.csv
```

### GUIManager.py — 统一 Tkinter 生命周期管理

单例模式的 GUI 管理工具，统一管理 Tk 实例生命周期，避免多工具重复创建 `Tk()` 导致的内存泄漏。提供文件选择、消息对话框等通用接口。

```python
from GUIManager import GUIManager

gui = GUIManager()
file_path = gui.select_file(title="选择文件")
gui.show_info("处理完成！")
gui.cleanup()
```

## 📄 文件结构

```
POI_Boundary_Matcher/
├── POI_Boundary_Matcher.py   # 主程序
├── wkt_converter.py           # WKT <-> Boundaries 双向转换工具
├── GUIManager.py              # 统一 Tkinter 生命周期管理工具
├── README.md                  # 项目说明（本文件）
├── README_EN.md               # English README
├── requirements.txt           # 依赖库列表
├── .gitignore                 # Git 忽略文件
├── LICENSE                    # 开源协议
└── examples/                 # 示例数据（可选）
    ├── poi_example.csv
    └── boundary_example.csv
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Shapely](https://shapely.readthedocs.io/) - 空间几何处理
- [Pandas](https://pandas.pydata.org/) - 数据处理
- [chardet](https://chardet.readthedocs.io/) - 编码检测

## 📧 联系方式

如有问题或建议，欢迎提交 Issue。

---

**⭐ 如果这个项目对你有帮助，请给它一个星标！**
