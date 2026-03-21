#!/bin/bash

# AI设计任务管理系统 - 快速启动脚本

echo "🚀 AI设计任务管理系统 - 后端服务启动脚本"
echo "========================================"

# Python 版本配置
PYTHON_VERSION="3.9.18"  # 可以改为其他 3.9.x 版本
PYTHON_MINOR="3.9"

# 检查并安装 pyenv（如果未安装）
if ! command -v pyenv &> /dev/null; then
    echo "📦 检测到未安装 pyenv，正在安装..."
    
    # 检查是否安装了 Homebrew
    if ! command -v brew &> /dev/null; then
        echo "❌ 需要先安装 Homebrew"
        echo "请运行: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    echo "📥 使用 Homebrew 安装 pyenv..."
    brew install pyenv
    
    # 配置 shell 环境（如果还没有配置）
    SHELL_CONFIG=""
    if [ -f ~/.zshrc ]; then
        SHELL_CONFIG=~/.zshrc
    elif [ -f ~/.bash_profile ]; then
        SHELL_CONFIG=~/.bash_profile
    elif [ -f ~/.bashrc ]; then
        SHELL_CONFIG=~/.bashrc
    fi
    
    if [ -n "$SHELL_CONFIG" ] && ! grep -q 'pyenv init' "$SHELL_CONFIG" 2>/dev/null; then
        echo "🔧 配置 pyenv 环境变量到 $SHELL_CONFIG..."
        echo '' >> "$SHELL_CONFIG"
        echo '# pyenv configuration' >> "$SHELL_CONFIG"
        echo 'export PYENV_ROOT="$HOME/.pyenv"' >> "$SHELL_CONFIG"
        echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> "$SHELL_CONFIG"
        echo 'eval "$(pyenv init -)"' >> "$SHELL_CONFIG"
    fi
    
    # 初始化 pyenv（当前会话）
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)" 2>/dev/null || true
    
    echo "✅ pyenv 安装完成"
    echo "⚠️  请重新运行脚本，或执行: source $SHELL_CONFIG"
fi

# 初始化 pyenv（确保在当前会话中可用）
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)" 2>/dev/null || true

# 检查 Python 3.9 是否已安装
if ! pyenv versions --bare 2>/dev/null | grep -q "^${PYTHON_MINOR}\."; then
    echo "📦 正在安装 Python ${PYTHON_VERSION}..."
    echo "⏳ 这可能需要几分钟时间，请耐心等待..."
    pyenv install ${PYTHON_VERSION}
    if [ $? -ne 0 ]; then
        echo "❌ Python ${PYTHON_VERSION} 安装失败"
        echo "💡 提示: 如果安装失败，可能需要安装编译依赖:"
        echo "   brew install openssl readline sqlite3 xz zlib tcl-tk"
        exit 1
    fi
    echo "✅ Python ${PYTHON_VERSION} 安装完成"
else
    echo "✅ Python ${PYTHON_MINOR}.x 已安装"
    # 获取已安装的 3.9.x 版本
    PYTHON_VERSION=$(pyenv versions --bare | grep "^${PYTHON_MINOR}\." | head -1)
fi

# 设置项目本地 Python 版本
echo "🔧 设置项目使用 Python ${PYTHON_VERSION}..."
pyenv local ${PYTHON_VERSION} 2>/dev/null || true

# 验证 Python 版本
PYTHON_CMD=$(pyenv which python3 2>/dev/null || which python3)
if [ -z "$PYTHON_CMD" ]; then
    echo "❌ 无法找到 Python 3 命令"
    exit 1
fi

PYTHON_VER=$(${PYTHON_CMD} --version 2>&1 | awk '{print $2}')
echo "✅ 当前使用的 Python 版本: ${PYTHON_VER}"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 使用 Python ${PYTHON_VER} 创建虚拟环境..."
    ${PYTHON_CMD} -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ 虚拟环境创建失败"
        exit 1
    fi
    echo "✅ 虚拟环境创建成功"
else
    # 检查现有虚拟环境是否使用正确的 Python 版本
    if [ -f "venv/bin/python3" ]; then
        VENV_PYTHON_VER=$(venv/bin/python3 --version 2>&1 | awk '{print $2}')
        if [[ ! "$VENV_PYTHON_VER" =~ ^3\.9\. ]]; then
            echo "⚠️  现有虚拟环境使用 Python ${VENV_PYTHON_VER}，需要重新创建..."
            echo "🗑️  删除旧虚拟环境..."
            rm -rf venv
            echo "📦 使用 Python ${PYTHON_VER} 创建新虚拟环境..."
            ${PYTHON_CMD} -m venv venv
            if [ $? -ne 0 ]; then
                echo "❌ 虚拟环境创建失败"
                exit 1
            fi
            echo "✅ 虚拟环境重新创建成功"
        else
            echo "✅ 虚拟环境已存在，使用 Python ${VENV_PYTHON_VER}"
        fi
    else
        echo "⚠️  虚拟环境目录存在但 Python 不可用，重新创建..."
        rm -rf venv
        ${PYTHON_CMD} -m venv venv
    fi
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo "⬆️  升级 pip..."
pip install --upgrade pip > /dev/null 2>&1

# 安装依赖
if [ ! -f "venv/.deps_installed" ]; then
    echo "📥 安装依赖包..."
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
    touch venv/.deps_installed
        echo "✅ 依赖安装完成"
    else
        echo "❌ 依赖安装失败"
        exit 1
    fi
else
    echo "✅ 依赖已安装"
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，复制示例配置..."
    if [ -f ".env.example" ]; then
    cp .env.example .env
    echo "📝 请编辑 .env 文件配置必要参数（特别是邮件配置）"
    read -p "是否现在编辑 .env 文件？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
        fi
    else
        echo "⚠️  未找到 .env.example 文件"
    fi
fi

# 检查数据库是否初始化
if [ ! -f "app.db" ]; then
    echo "🔧 初始化数据库..."
    python scripts/init_admin.py
else
    echo "✅ 数据库已存在"
fi

# 创建上传目录
mkdir -p uploads

echo ""
echo "🎉 准备工作完成！"
echo "📌 当前 Python 版本: $(python --version)"
echo ""
echo "启动服务器..."
echo "API 文档: http://localhost:8000/docs"
echo ""

# 启动服务器
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
