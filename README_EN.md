# POI Boundary Matcher

[中文](README.md) | English

A powerful tool for matching POI (Points of Interest) with administrative boundary data, featuring spatial point-in-polygon matching with a friendly graphical user interface.

## ✨ Features

- 📁 **Multi-format Support**: Read CSV and Excel (.xlsx) files
- 🔍 **Smart Encoding Detection**: Automatically detect file encoding (UTF-8, GBK, GB18030, etc.)
- 🎯 **Flexible Matching Modes**:
  - One-to-one matching: Each POI matches only one boundary
  - One-to-many matching: POI can match multiple boundaries (e.g., cross-region POIs)
- ⚙️ **Customizable Fields**: Freely select POI and boundary fields to preserve
- 🚀 **High Performance**:
  - Uses Shapely STRtree spatial index for acceleration
  - Uses PreparedGeometry for optimized spatial queries
  - Multi-threaded matching, UI remains responsive
- 💾 **Multiple Output Formats**: Save as CSV or Excel
- 📊 **Real-time Progress**: Display matching progress and statistics

## 📦 Installation

### Dependencies

```bash
pip install pandas shapely chardet
# If you need Excel support, also install:
pip install openpyxl
```

### System Requirements

- Python 3.7+
- Windows / macOS / Linux

## 🚀 Quick Start

### Method 1: Run Python Script Directly

```bash
python POI_Boundary_Matcher.py
```

### Method 2: Use Packaged Executable

If you have a packaged .exe file, you can double-click to run it (Windows).

## 📖 User Guide

### Step 1: Prepare Data

#### POI Data File
Must contain longitude and latitude fields, for example:

**CSV format (supports multiple encodings):**
```csv
id,name,longitude,latitude,address
1,Starbucks,116.404,39.905,Beijing Chaoyang District
2,McDonald's,121.473,31.230,Shanghai Huangpu District
```

**Excel format (.xlsx):**
Same as above, but saved as Excel file.

#### Boundary Data File
Must contain WKT format geometry field, or a field with coordinate point strings.

**WKT format example:**
```csv
id,name,boundary_wkt
1,Chaoyang District,"POLYGON ((116.4 39.9, 116.5 39.9, 116.5 40.0, 116.4 40.0, 116.4 39.9))"
2,Haidian District,"POLYGON ((116.3 39.9, 116.4 39.9, 116.4 40.0, 116.3 40.0, 116.3 39.9))"
```

**Coordinate point string format (auto-converted):**
```csv
id,name,boundaries
1,Chaoyang District,"116.4_39.9;116.5_39.9;116.5_40.0;116.4_40.0;116.4_39.9"
2,Haidian District,"116.3_39.9;116.4_39.9;116.4_40.0;116.3_40.0;116.3_39.9"
```

⚠️ **Coordinate Format Note:**
- Supports `longitude_latitude` format (underscore separated)
- The program will automatically convert coordinate point strings to WKT format

### Step 2: Run the Program

1. Launch the program
2. Click the "Upload" button to select POI data file
3. Click the "Upload" button to select boundary data file
4. The program will automatically detect longitude/latitude fields and boundary geometry fields

### Step 3: Configure Matching Options

- **Longitude/Latitude Fields**: Confirm the auto-detected fields are correct
- **Boundary Geometry Field**: Confirm the boundary geometry field is correct (supports auto-conversion)
- **Field Selection**:
  - Select POI fields to preserve
  - Select boundary fields to preserve
  - Supports select all, deselect all, invert selection
- **Matching Mode**:
  - One-to-one: Each POI matches only one boundary (default)
  - One-to-many: POI can match multiple boundaries
- **Keep Unmatched Records**: If checked, unmatched POIs will appear in results (boundary fields will be empty)

### Step 4: Start Matching

1. Click the "Start Matching" button
2. View progress bar and status information
3. Wait for matching to complete

### Step 5: Save Results

1. After matching completes, click the "Save Results" button
2. Select save format (CSV or Excel)
3. Select CSV encoding (UTF-8 with BOM or GBK)
4. Choose save path

## 📊 Output Results

The result file contains the following fields:

- All selected POI fields
- All selected boundary fields (with `bd_` prefix)
- `matched_boundary_idx`: Matched boundary index

**Example output (CSV):**
```csv
id,name,longitude,latitude,bd_name,bd_id,matched_boundary_idx
1,Starbucks,116.404,39.905,Chaoyang District,1,0
2,McDonald's,121.473,31.230,Huangpu District,2,5
```

## 🔧 Advanced Features

### 1. Data Preview

- After uploading files, click the "Preview" button to view the first 10 rows of data
- Convenient for confirming data format and field names

### 2. Cancel Matching

- You can click the "Cancel" button during matching
- Matched results will be saved (if any)

### 3. Batch Processing

- Supports processing large-scale data (10K+ POIs + 1K+ boundaries)
- Uses spatial index for superior performance

## ⚠️ Notes

1. **Coordinate System**: Ensure POI coordinates are in WGS84 coordinate system (GPS coordinates)
2. **Boundary Orientation**: Polygon coordinates need to be arranged in clockwise or counterclockwise order
3. **Closure Check**: Polygon start and end coordinates need to be the same (program handles this automatically)
4. **Memory Usage**: Ensure sufficient memory when processing large amounts of data
5. **Encoding Issues**: If CSV file reading fails, try saving with a different encoding

## 🐛 Common Issues

### Q1: Program won't start?

**A:** Ensure all dependencies are installed:
```bash
pip install pandas shapely chardet openpyxl
```

### Q2: Excel file cannot be read?

**A:** Need to install `openpyxl` library:
```bash
pip install openpyxl
```

### Q3: Matching results are empty?

**A:** Possible reasons:
- POI coordinates are not within boundary ranges
- Coordinate system mismatch (needs WGS84 coordinates)
- Boundary data format error

### Q4: Program freezes or becomes unresponsive?

**A:**
- Large data volume, wait for some time
- Check if data format is correct
- View error messages in command line output

### Q5: How to improve efficiency?

**A:**
- Use one-to-one matching mode (faster than one-to-many)
- Reduce number of fields to preserve
- Ensure boundary data is in WKT format (avoid real-time conversion)

## 📄 File Structure

```
POI_Boundary_Matcher/
├── POI_Boundary_Matcher.py   # Main program
├── README.md                  # Project documentation (Chinese)
├── README_EN.md               # English README (this file)
├── requirements.txt           # Dependencies list
├── .gitignore                 # Git ignore file
├── LICENSE                    # Open source license
└── examples/                 # Example data (optional)
    ├── poi_example.csv
    └── boundary_example.csv
```

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Shapely](https://shapely.readthedocs.io/) - Spatial geometry processing
- [Pandas](https://pandas.pydata.org/) - Data processing
- [chardet](https://chardet.readthedocs.io/) - Encoding detection

## 📧 Contact

If you have any questions or suggestions, please submit an Issue.

---

**⭐ If this project helps you, please give it a star!**
