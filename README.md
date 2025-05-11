# Z1-Gray Bot

Telegram机器人项目，实现Z1-Gray协议的接入流程。

## 功能模块

### Step 1: 系统初始化与身份锚定
- 生成用户安全ID
- 协议初始化与风险评估

## 环境配置
- Python 3.9+
- python-telegram-bot v20+
- python-dotenv

## 部署
本项目可部署在Render等平台上。

## 许可证
私有项目，保留所有权利。

## 🔹 Key Features

Currently implements:

- **Step 1: SYSTEM INIT**
  - Protocol initialization.
  - Unique user identity hashing via SHA256.
  - System-generated STABILITY RISK alert.
  - Interactive diagnostic scan trigger.

## 📁 Project Structure

- `start_bot.py`: Main entry point to initialize and run the bot.
- `handlers/step_1.py`: Contains `/start` command and full Step 1 flow logic.
- `utils/helpers.py`: Provides `generate_user_secure_id()` and other utility functions.
- `.env`: Runtime configuration file (must be manually created).
- `requirements.txt`: Python dependencies.

## ⚙️ Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- Git (optional but recommended)

## 🚀 Setup & Installation

```bash
# Clone the repo (if remote)
# git clone <repository_url>
# cd z1_gray_bot_v1_dev

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
