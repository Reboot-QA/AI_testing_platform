@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set ROOT=%~dp0

echo ========================================
echo   AI质量平台 - 一键启动
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

:: 检查 Node
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

:: 后端依赖
echo [1/4] 检查后端依赖...
cd /d "%ROOT%backend"
if not exist ".env" copy /Y .env.example .env >nul
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [提示] 依赖安装未完全成功，若服务可正常启动可忽略
)

:: 前端依赖
echo [2/4] 检查前端依赖...
cd /d "%ROOT%frontend"
if not exist "node_modules" call npm install

:: 启动后端
echo [3/4] 启动后端 (http://127.0.0.1:8000)...
cd /d "%ROOT%backend"
start "AI质量平台-后端" cmd /k "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: 等待后端就绪
timeout /t 3 /nobreak >nul

:: 启动前端
echo [4/4] 启动前端 (http://127.0.0.1:5173)...
cd /d "%ROOT%frontend"
start "AI质量平台-前端" cmd /k "npm run dev"

echo.
echo ========================================
echo   部署完成！
echo   前端: http://127.0.0.1:5173
echo   后端: http://127.0.0.1:8000
echo   API文档: http://127.0.0.1:8000/docs
echo   账号: admin / admin123
echo ========================================
echo.
pause
