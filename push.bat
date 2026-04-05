@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ===================================
echo   简体中文输入助手 — 上传到 GitHub
echo ===================================
echo.

:: ── 检查是否有改动 ──────────────────────────────────
git status --short > tmp_status.txt 2>&1
set /p STATUS_FIRST=<tmp_status.txt
del tmp_status.txt

git status --short | findstr /r "." >nul 2>&1
if errorlevel 1 (
    echo [信息] 没有需要提交的改动，直接推送...
    goto :push
)

:: ── 显示改动文件 ─────────────────────────────────────
echo [改动文件]
git status --short
echo.

:: ── 输入提交说明 ─────────────────────────────────────
set /p COMMIT_MSG=请输入提交说明（直接回车使用默认）:
if "%COMMIT_MSG%"=="" set COMMIT_MSG=update

:: ── 暂存 + 提交 ──────────────────────────────────────
echo.
echo [1/3] 暂存改动...
git add -A
if errorlevel 1 ( echo [错误] git add 失败 & pause & exit /b 1 )

echo [2/3] 提交...
git commit -m "%COMMIT_MSG%"
if errorlevel 1 ( echo [错误] git commit 失败 & pause & exit /b 1 )

:push
:: ── 推送 ────────────────────────────────────────────
echo [3/3] 推送到 GitHub...
git push origin main
if errorlevel 1 (
    echo.
    echo [错误] 推送失败，请检查：
    echo   1. 网络连接是否正常
    echo   2. GitHub 账号是否已在 Windows 凭据管理器中登录
    echo.
    pause
    exit /b 1
)

echo.
echo ===================================
echo   完成！代码已上传到 GitHub
echo   https://github.com/isaacwoo/chs-ime
echo ===================================
echo.
pause
