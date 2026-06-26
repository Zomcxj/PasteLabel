#!/bin/bash

# ==============================================================================
#  PasteLabel 构建脚本（PasteY）
#  贴图标注工具主应用
#  支持: Linux / Windows (MSYS2 / Git Bash / Cygwin) / macOS
#  用法: ./build.sh [options]
#  选项:
#    --clean       : 强制清理缓存，从头构建（默认）
#    --no-clean    : 使用缓存，加快重复构建速度（推荐日常开发）
#
#  快捷方式:
#    ./build.sh           # 完整构建（发布版本）
#    ./build.sh fast      # 快速构建（日常开发）= --no-clean
# ==============================================================================

# 记录项目根目录（build.sh 所在目录的上级）
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 解析命令行参数
CLEAN_BUILD=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        --no-clean)
            CLEAN_BUILD=false
            shift
            ;;
        fast)
            CLEAN_BUILD=false
            shift
            ;;
        *)
            echo "未知参数: $1"
            echo "用法: $0 [--clean|--no-clean] | fast"
            echo ""
            echo "示例:"
            echo "  $0           # 完整构建（发布版本）"
            echo "  $0 fast      # 快速构建（日常开发）"
            exit 1
            ;;
    esac
done

set -e  # 任何命令失败时立即退出

# ==================== 颜色输出定义 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC}  $(date '+%H:%M:%S') $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $(date '+%H:%M:%S') $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $(date '+%H:%M:%S') $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; }

# ==================== 检测操作系统 ====================
log_info "检测操作系统..."
OS="$(uname -s)"
case "$OS" in
    Linux*)     PLATFORM="linux" ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT) PLATFORM="windows" ;;
    Darwin*)    PLATFORM="macos" ;;
    *)
        log_error "不支持的操作系统: $OS"
        exit 1
        ;;
esac
log_ok "当前平台: $PLATFORM (uname: $OS)"

# ==================== 平台相关配置 ====================
if [ "$PLATFORM" = "windows" ]; then
    PYINSTALLER_CMD="python -m PyInstaller"
    PYTHON_OPTIMIZE=2
    SEP="\\\\"
    # Git Bash/MSYS2 下需将 Unix 路径转为 Windows 路径（否则 Python 不认识）
    PROJECT_ROOT="$(cygpath -w "$PROJECT_ROOT" 2>/dev/null || echo "$PROJECT_ROOT")"
    OUTPUT_FILE="${PROJECT_ROOT}\\dist\\PasteLabel.exe"
else
    PYINSTALLER_CMD="pyinstaller"
    PYTHON_OPTIMIZE=0
    SEP="/"
    OUTPUT_FILE="${PROJECT_ROOT}/dist/PasteLabel"
fi

log_info "PyInstaller 命令: $PYINSTALLER_CMD"
log_info "Python optimize:  $PYTHON_OPTIMIZE"

# ==================== 前置检查 ====================
log_info "执行前置检查..."

# 检查 PyInstaller 是否可用
if ! command -v $PYINSTALLER_CMD &> /dev/null; then
    if [ "$PLATFORM" = "windows" ]; then
        if ! command -v python &> /dev/null; then
            log_error "未找到 python，请确保 Python 已安装并加入 PATH"
            exit 1
        fi
        if ! python -m PyInstaller --version &> /dev/null; then
            log_error "未找到 PyInstaller，请执行: pip install pyinstaller"
            exit 1
        fi
    else
        log_error "未找到 pyinstaller，请执行: pip install pyinstaller"
        exit 1
    fi
fi
log_ok "PyInstaller 可用"

# 检查主脚本是否存在
MAIN_SCRIPT_PATH="${PROJECT_ROOT}${SEP}PasteY${SEP}main.py"
if [ ! -f "$MAIN_SCRIPT_PATH" ]; then
    log_error "主脚本 '$MAIN_SCRIPT_PATH' 不存在"
    exit 1
fi
log_ok "主脚本 '$MAIN_SCRIPT_PATH' 存在"

# 检查图标文件
ICON_FILE="${PROJECT_ROOT}${SEP}ico_image${SEP}icoo.png"
if [ ! -f "$ICON_FILE" ]; then
    log_warn "图标文件 '$ICON_FILE' 不存在，构建将继续但可能缺少图标"
else
    log_ok "图标文件 '$ICON_FILE' 存在"
fi

# 检查资源目录
RESOURCE_DIR="${PROJECT_ROOT}${SEP}ico_image"
if [ ! -d "$RESOURCE_DIR" ]; then
    log_warn "资源目录 '$RESOURCE_DIR' 不存在，构建将继续但可能缺少资源"
else
    log_ok "资源目录 '$RESOURCE_DIR' 存在"
fi

# ==================== 生成 spec 文件 ====================
# 策略：动态生成 spec 文件，与 Windows 已验证的方案一致
# 确保 pathex 指向项目根目录，让 PyInstaller 能正确发现 PasteY 包结构

SPEC_FILE="${PROJECT_ROOT}${SEP}PasteY${SEP}PasteLabel_build.spec"

log_info "生成 spec 文件..."

cat > "$SPEC_FILE" << 'SPECEOF'
# -*- mode: python ; coding: utf-8 -*-
# 自动生成 - 请勿手动修改

SPECEOF

# 用追加方式写入 Python 列表和 Analysis 块（需要变量展开的部分）
cat >> "$SPEC_FILE" << SPECEOF

a = Analysis(
    ['${MAIN_SCRIPT_PATH}'],
    pathex=['${PROJECT_ROOT}'],
    binaries=[],
    datas=[('${RESOURCE_DIR}', 'ico_image')],
    hiddenimports=[
        'PasteY', 'PasteY.ui', 'PasteY.ui.main_window', 'PasteY.ui.ui_builder',
        'PasteY.ui.settings_dialog', 'PasteY.ui.theme', 'PasteY.ui.dwm',
        'PasteY.ui.dialogs', 'PasteY.ui.widgets', 'PasteY.ui.i18n', 'PasteY.ui.styles',
        'PasteY.engine', 'PasteY.engine.save_manager',
        'PasteY.engine.undo_manager', 'PasteY.engine.label_manager',
        'PasteY.engine.image_loader', 'PasteY.engine.paste_engine',
        'PasteY.engine.event_handler',
        'PasteY.canvas', 'PasteY.canvas.canvas', 'PasteY.canvas.canvas_renderer',
        'PasteY.canvas.canvas_interaction', 'PasteY.canvas.canvas_drawing',
        'PasteY.canvas.canvas_menu',
        'PasteY.core', 'PasteY.core.config', 'PasteY.core.config_manager',
        'PasteY.core.utils', 'PasteY.core.models', 'PasteY.core.editor_protocol',
        'PasteY.core.exception_hook',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pandas', 'numpy', 'pytest'],
    noarchive=False,
    optimize=${PYTHON_OPTIMIZE},
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
$(if [ "$PLATFORM" = "windows" ]; then echo "    [('-O2', None, 'OPTION')],"; else echo "    [],"; fi)
    name='PasteLabel',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['${ICON_FILE}'],
)
SPECEOF

log_ok "spec 文件已生成: $SPEC_FILE"

# ==================== 执行打包 ====================
log_info "开始打包 ${PLATFORM} 应用程序..."

log_info "执行命令:"
echo "─────────────────────────────────────────"
echo "$PYINSTALLER_CMD \\"
echo "    $SPEC_FILE \\"
echo "    --distpath \"${PROJECT_ROOT}/dist\" \\"
echo "    --workpath \"${PROJECT_ROOT}/build\" \\"
[ "$CLEAN_BUILD" = true ] && echo "    --clean \\"
echo "    --noconfirm"
echo "─────────────────────────────────────────"

PYINSTALLER_SPEC_CMD="$PYINSTALLER_CMD \
    \"$SPEC_FILE\" \
    --distpath \"${PROJECT_ROOT}/dist\" \
    --workpath \"${PROJECT_ROOT}/build\" \
    --noconfirm"

if [ "$CLEAN_BUILD" = true ]; then
    log_info "清理模式：重新分析所有依赖（适合发布版本）"
    eval "$PYINSTALLER_SPEC_CMD --clean"
else
    log_info "快速模式：使用缓存构建（适合日常开发）"
    eval "$PYINSTALLER_SPEC_CMD"
fi

BUILD_EXIT_CODE=$?

# 清理临时 spec 文件
rm -f "$SPEC_FILE"

# ==================== 结果处理 ====================
echo ""
if [ $BUILD_EXIT_CODE -eq 0 ]; then
    if [ -f "$OUTPUT_FILE" ]; then
        FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
        log_ok "打包成功！"
        log_ok "可执行文件: ${OUTPUT_FILE} (${FILE_SIZE})"
    else
        log_warn "打包命令执行成功，但未找到输出文件: ${OUTPUT_FILE}"
        log_warn "请检查 ${PROJECT_ROOT}/dist/ 目录"
    fi
    echo ""
    log_info "应用程序特性："
    log_info "  - 无控制台窗口 (-w)"
    log_info "  - 单文件打包 (-F)"
    log_info "  - 应用图标: ${ICON_FILE}"
    log_info "  - 资源目录: ${RESOURCE_DIR}/"
    log_info "  - 包含所有必要依赖"
    exit 0
else
    log_error "打包失败 (退出码: $BUILD_EXIT_CODE)，请检查上方错误信息"
    exit 1
fi
