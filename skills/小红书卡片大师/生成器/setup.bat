@echo off
echo ========================================
echo  小红书卡片生成器 - 安装依赖
echo ========================================
echo.

cd /d "%~dp0"

echo 正在安装依赖...
call npm install

echo.
echo ========================================
echo  安装完成！
echo ========================================
echo.
echo 使用方法:
echo   node generate-cards.js ^<json文件路径^>
echo.
echo 示例:
echo   node generate-cards.js data.json
echo.
pause
