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
    ADD_DATA_SEP=";"
    EXTRA_ARGS="--python-option=-O2"
    # Git Bash/MSYS2 下需将 Unix 路径转为 Windows 路径（否则 Python 不认识）
    PROJECT_ROOT="$(cygpath -w "$PROJECT_ROOT" 2>/dev/null || echo "$PROJECT_ROOT")"
    OUTPUT_FILE="${PROJECT_ROOT}\\dist\\PasteLabel.exe"
else
    PYINSTALLER_CMD="pyinstaller"
    ADD_DATA_SEP=":"
    EXTRA_ARGS=""
    OUTPUT_FILE="${PROJECT_ROOT}/dist/PasteLabel"
fi

log_info "PyInstaller 命令: $PYINSTALLER_CMD"
log_info "资源路径分隔符:   '$ADD_DATA_SEP'"
log_info "额外参数:         ${EXTRA_ARGS:-<无>}"

# ==================== 前置检查 ====================
log_info "执行前置检查..."

# 检查 PyInstaller 是否可用
if ! command -v $PYINSTALLER_CMD &> /dev/null; then
    # Windows 下 python -m 不能直接用 command -v 检查，改为检查 python
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
MAIN_SCRIPT="main.py"
if [ ! -f "$MAIN_SCRIPT" ]; then
    log_error "主脚本 '$MAIN_SCRIPT' 不存在于 $(pwd)"
    exit 1
fi
log_ok "主脚本 '$MAIN_SCRIPT' 存在"

# 检查图标文件（从 PasteY/ 看，ico_image 在上级目录）
ICON_FILE="${PROJECT_ROOT}/ico_image/icoo.png"
if [ ! -f "$ICON_FILE" ]; then
    log_warn "图标文件 '$ICON_FILE' 不存在，构建将继续但可能缺少图标"
else
    log_ok "图标文件 '$ICON_FILE' 存在"
fi

# 检查资源目录
RESOURCE_DIR="${PROJECT_ROOT}/ico_image"
DEST_DIR="ico_image"  # PyInstaller 打包后的目标路径（相对于临时目录）
if [ ! -d "$RESOURCE_DIR" ]; then
    log_warn "资源目录 '$RESOURCE_DIR' 不存在，构建将继续但可能缺少资源"
else
    if [ "$CLEAN_BUILD" = true ]; then
        FILE_COUNT=$(find "$RESOURCE_DIR" -type f 2>/dev/null | wc -l)
        log_ok "资源目录 '$RESOURCE_DIR' 存在，包含 $FILE_COUNT 个文件"
    else
        log_ok "资源目录 '$RESOURCE_DIR' 存在"
    fi
fi

# ==================== 执行打包 ====================
log_info "开始打包 ${PLATFORM} 应用程序..."

log_info "执行命令:"
echo "─────────────────────────────────────────"
echo "$PYINSTALLER_CMD \\"
echo "    -F \\"
echo "    -w \\"
echo "    -n PasteLabel \\"
echo "    --distpath \"${PROJECT_ROOT}/dist\" \\"
echo "    --workpath \"${PROJECT_ROOT}/build\" \\"
echo "    --icon=\"${ICON_FILE}\" \\"
echo "    --add-data \"${RESOURCE_DIR}${ADD_DATA_SEP}${DEST_DIR}\" \\"
[ "$CLEAN_BUILD" = true ] && echo "    --clean \\"
echo "    --noconfirm \\"
echo "    --hidden-import PasteY \\"
echo "    --hidden-import PasteY.ui \\"
echo "    --hidden-import PasteY.ui.main_window \\"
echo "    --hidden-import PasteY.ui.ui_builder \\"
echo "    --hidden-import PasteY.ui.settings_dialog \\"
echo "    --hidden-import PasteY.ui.theme \\"
echo "    --hidden-import PasteY.ui.dwm \\"
echo "    --hidden-import PasteY.ui.dialogs \\"
echo "    --hidden-import PasteY.ui.widgets \\"
echo "    --hidden-import PasteY.ui.i18n \\"
echo "    --hidden-import PasteY.ui.styles \\"
echo "    --hidden-import PasteY.engine \\"
echo "    --hidden-import PasteY.engine.save_manager \\"
echo "    --hidden-import PasteY.engine.undo_manager \\"
echo "    --hidden-import PasteY.engine.label_manager \\"
echo "    --hidden-import PasteY.engine.image_loader \\"
echo "    --hidden-import PasteY.engine.paste_engine \\"
echo "    --hidden-import PasteY.engine.event_handler \\"
echo "    --hidden-import PasteY.canvas \\"
echo "    --hidden-import PasteY.canvas.canvas \\"
echo "    --hidden-import PasteY.canvas.canvas_renderer \\"
echo "    --hidden-import PasteY.canvas.canvas_interaction \\"
echo "    --hidden-import PasteY.canvas.canvas_drawing \\"
echo "    --hidden-import PasteY.canvas.canvas_menu \\"
echo "    --hidden-import PasteY.core \\"
echo "    --hidden-import PasteY.core.config \\"
echo "    --hidden-import PasteY.core.config_manager \\"
echo "    --hidden-import PasteY.core.utils \\"
echo "    --hidden-import PasteY.core.models \\"
echo "    --hidden-import PasteY.core.editor_protocol \\"
echo "    --hidden-import PasteY.core.exception_hook \\"
echo "    --exclude-module tkinter \\"
echo "    --exclude-module matplotlib \\"
echo "    --exclude-module pandas \\"
echo "    --exclude-module numpy \\"
echo "    --exclude-module pytest \\"
[ -n "$EXTRA_ARGS" ] && echo "    $EXTRA_ARGS \\"
echo "    $MAIN_SCRIPT"
echo "─────────────────────────────────────────"

# 构建基础命令
PYINSTALLER_BASE_CMD="$PYINSTALLER_CMD \
    -F \
    -w \
    -n PasteLabel \
    --distpath \"${PROJECT_ROOT}/dist\" \
    --workpath \"${PROJECT_ROOT}/build\" \
    --icon=\"${ICON_FILE}\" \
    --add-data \"${RESOURCE_DIR}${ADD_DATA_SEP}${DEST_DIR}\" \
    --noconfirm \
    --hidden-import PasteY \
    --hidden-import PasteY.ui \
    --hidden-import PasteY.ui.main_window \
    --hidden-import PasteY.ui.ui_builder \
    --hidden-import PasteY.ui.settings_dialog \
    --hidden-import PasteY.ui.theme \
    --hidden-import PasteY.ui.dwm \
    --hidden-import PasteY.ui.dialogs \
    --hidden-import PasteY.ui.widgets \
    --hidden-import PasteY.ui.i18n \
    --hidden-import PasteY.ui.styles \
    --hidden-import PasteY.engine \
    --hidden-import PasteY.engine.save_manager \
    --hidden-import PasteY.engine.undo_manager \
    --hidden-import PasteY.engine.label_manager \
    --hidden-import PasteY.engine.image_loader \
    --hidden-import PasteY.engine.paste_engine \
    --hidden-import PasteY.engine.event_handler \
    --hidden-import PasteY.canvas \
    --hidden-import PasteY.canvas.canvas \
    --hidden-import PasteY.canvas.canvas_renderer \
    --hidden-import PasteY.canvas.canvas_interaction \
    --hidden-import PasteY.canvas.canvas_drawing \
    --hidden-import PasteY.canvas.canvas_menu \
    --hidden-import PasteY.core \
    --hidden-import PasteY.core.config \
    --hidden-import PasteY.core.config_manager \
    --hidden-import PasteY.core.utils \
    --hidden-import PasteY.core.models \
    --hidden-import PasteY.core.editor_protocol \
    --hidden-import PasteY.core.exception_hook \
    --exclude-module tkinter \
    --exclude-module matplotlib \
    --exclude-module pandas \
    --exclude-module numpy \
    --exclude-module pytest \
    $EXTRA_ARGS \
    \"$MAIN_SCRIPT\""

# 根据参数决定是否清理
if [ "$CLEAN_BUILD" = true ]; then
    log_info "清理模式：重新分析所有依赖（适合发布版本）"
    eval "$PYINSTALLER_BASE_CMD --clean"
else
    log_info "快速模式：使用缓存构建（适合日常开发）"
    eval "$PYINSTALLER_BASE_CMD"
fi

BUILD_EXIT_CODE=$?

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
