# Auto Printer

一个基于 Python 的本地自动打印工具。启动后会在系统托盘驻留一个 HTTP 服务，网页可通过上传 PDF 文件调用本地默认打印机进行静默打印。

## 功能特性

- 本地 HTTP 服务接收 PDF 打印请求
- 调用系统默认打印机静默打印，不弹系统打印对话框
- 支持 Windows 10+ 和 macOS 12+
- 打包为 Windows 单文件 `.exe` 和 macOS `.app`
- 系统托盘图标，支持打开 Demo 页面和退出程序
- 自带美观的网页调用 Demo

## 目录结构

```
auto-printer/
├── src/
│   ├── main.py              # 程序入口
│   ├── app.py               # Flask 服务与 API
│   ├── printer.py           # 跨平台静默打印逻辑
│   ├── config.py            # 配置
│   ├── tasks.py             # 打印任务管理
│   ├── tray.py              # 系统托盘
│   ├── templates/demo.html  # 前端 Demo 页面
│   └── static/              # 前端样式与脚本
├── scripts/
│   ├── build_win.ps1        # Windows 打包脚本
│   └── build_mac.sh         # macOS 打包脚本
├── auto-printer.spec        # PyInstaller 规格文件
├── requirements.txt         # Python 依赖
└── README.md                # 本文件
```

## 快速开始

### 1. 安装依赖

确保已安装 Python 3.11+，然后执行：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 运行开发服务

```bash
python src/main.py
```

程序启动后会自动打开浏览器访问 Demo 页面：http://127.0.0.1:5000/demo

### 3. API 调用

#### 上传 PDF 打印

```bash
curl -X POST -F "file=@document.pdf" http://127.0.0.1:5000/api/print
```

返回示例：

```json
{
  "job_id": "a1b2c3d4",
  "status": "pending",
  "message": "Print job accepted"
}
```

#### 查询任务状态

```bash
curl http://127.0.0.1:5000/api/tasks/a1b2c3d4
```

#### 查询服务状态

```bash
curl http://127.0.0.1:5000/api/status
```

## 打包为可执行文件

### Windows

以管理员身份打开 PowerShell，执行：

```powershell
.\scripts\build_win.ps1
```

打包完成后，产物位于 `dist/auto-printer.exe`。双击即可运行。

### macOS

在终端执行：

```bash
chmod +x scripts/build_mac.sh
./scripts/build_mac.sh
```

打包完成后，产物位于 `dist/AutoPrinter.app`。双击即可运行。

## 配置项

可通过环境变量调整服务配置：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `AUTO_PRINTER_HOST` | 服务监听地址 | `127.0.0.1` |
| `AUTO_PRINTER_PORT` | 服务监听端口 | `5000` |
| `AUTO_PRINTER_DEBUG` | 是否开启调试日志 | `0` |

## 注意事项

- 服务默认只监听 `127.0.0.1`，不会暴露到局域网。
- 仅支持上传 PDF 文件，大小限制为 50MB。
- 打印时使用系统默认打印机，请确保已正确安装并设置默认打印机。
- macOS 通过 `lpr` 命令提交打印任务；Windows 通过 `win32print` 绘制位图到打印机 DC。
- 打包后的程序首次启动可能需要几秒加载时间。

## 许可证

MIT
