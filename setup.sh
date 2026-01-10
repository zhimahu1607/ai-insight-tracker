#!/bin/bash
#
# AI Insight Tracker - 项目初始化脚本
#
# 此脚本用于快速设置开发环境：
# 1. 检查并创建 Conda 环境
# 2. 安装 Python 依赖
# 3. 创建配置文件
# 4. 交互式配置 LLM 提供商
#
# Usage:
#   ./setup.sh          # 交互式安装
#   ./setup.sh --skip   # 跳过交互式配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                   AI Insight Tracker Setup                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================
# Step 1: 检查 Conda
# ============================================================
echo -e "${BLUE}[1/5]${NC} 检查 Conda 环境..."

if ! command -v conda &> /dev/null; then
    echo -e "${RED}❌ 未检测到 Conda，请先安装 Miniconda 或 Anaconda${NC}"
    echo ""
    echo "安装 Miniconda:"
    echo "  macOS: brew install --cask miniconda"
    echo "  Linux: wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && bash Miniconda3-latest-Linux-x86_64.sh"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Conda 已安装${NC}"

# ============================================================
# Step 2: 创建/更新 Conda 环境
# ============================================================
echo -e "${BLUE}[2/5]${NC} 创建 Conda 环境..."

ENV_NAME="ai-insight-tracker"

if conda env list | grep -q "^${ENV_NAME} "; then
    echo -e "${YELLOW}  环境 ${ENV_NAME} 已存在，更新依赖...${NC}"
    conda env update -f environment.yml --prune
else
    echo -e "  创建新环境 ${ENV_NAME}..."
    conda env create -f environment.yml
fi

echo -e "${GREEN}✓ Conda 环境就绪${NC}"

# ============================================================
# Step 3: 激活环境并安装依赖
# ============================================================
echo -e "${BLUE}[3/5]${NC} 安装 Python 依赖..."

# 激活环境
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"

# 确保 pip 依赖是最新的
pip install -r requirements.txt --quiet

# 安装 Playwright 浏览器（Crawler 需要）
playwright install chromium --with-deps

echo -e "${GREEN}✓ 依赖安装完成${NC}"

# ============================================================
# Step 4: 创建配置文件
# ============================================================
echo -e "${BLUE}[4/5]${NC} 配置文件..."

CONFIG_FILE="config/settings.yaml"
EXAMPLE_FILE="config/settings.example.yaml"

if [ -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}  配置文件已存在，跳过创建${NC}"
else
    cp "$EXAMPLE_FILE" "$CONFIG_FILE"
    echo -e "${GREEN}✓ 配置文件已创建: ${CONFIG_FILE}${NC}"
fi

# ============================================================
# Step 5: 交互式配置 (可选)
# ============================================================
if [ "$1" == "--skip" ]; then
    echo -e "${BLUE}[5/5]${NC} 跳过交互式配置"
else
    echo -e "${BLUE}[5/5]${NC} 配置 LLM 提供商..."
    echo ""
    echo -e "${CYAN}请选择 LLM 提供商:${NC}"
    echo "  1) DeepSeek (推荐，性价比高)"
    echo "  2) OpenAI"
    echo "  3) Anthropic Claude"
    echo "  4) 阿里云 Qwen"
    echo "  5) Google Gemini"
    echo "  6) 智谱 AI"
    echo "  7) OpenRouter"
    echo "  8) Grok"
    echo "  9) 跳过配置"
    echo ""

    read -p "请输入选项 (1-9): " choice

    case $choice in
        1) PROVIDER="deepseek" ;;
        2) PROVIDER="openai" ;;
        3) PROVIDER="anthropic" ;;
        4) PROVIDER="qwen" ;;
        5) PROVIDER="gemini" ;;
        6) PROVIDER="zhipu" ;;
        7) PROVIDER="openrouter" ;;
        8) PROVIDER="grok" ;;
        9)
            echo -e "${YELLOW}跳过 LLM 配置，请稍后手动编辑 config/settings.yaml${NC}"
            PROVIDER=""
            ;;
        *)
            echo -e "${YELLOW}无效选项，跳过配置${NC}"
            PROVIDER=""
            ;;
    esac

    if [ -n "$PROVIDER" ]; then
        echo ""
        read -p "请输入 ${PROVIDER} 的 API Key: " API_KEY

        if [ -n "$API_KEY" ]; then
            # 使用 Python 脚本更新配置
            python scripts/update_config.py "$PROVIDER" "$API_KEY"
            echo ""
        else
            echo -e "${YELLOW}未输入 API Key，跳过配置${NC}"
        fi
    fi
fi

# ============================================================
# 验证配置
# ============================================================
echo ""
echo -e "${CYAN}验证配置...${NC}"
python scripts/validate_config.py || true

# ============================================================
# 完成
# ============================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                       设置完成！                                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}后续步骤:${NC}"
echo ""
echo "  1. 激活环境:"
echo -e "     ${GREEN}conda activate ${ENV_NAME}${NC}"
echo ""
echo "  2. 编辑配置 (如需修改):"
echo -e "     ${GREEN}vim config/settings.yaml${NC}"
echo ""
echo "  3. 验证配置:"
echo -e "     ${GREEN}python scripts/validate_config.py${NC}"
echo ""
echo "  4. 运行每日任务 (开发完成后):"
echo -e "     ${GREEN}python scripts/daily_crawl.py${NC}"
echo ""
echo -e "${CYAN}GitHub Actions 配置:${NC}"
echo ""
echo "  在仓库 Settings > Secrets and variables > Actions 中添加:"
echo "    - LLM_PROVIDER (Variables)"
echo "    - LLM_MODEL (Variables)"
echo "    - LLM_API_KEY (Secrets)"
echo "    - FEISHU_WEBHOOK_URL (Secrets, 可选)"
echo ""

