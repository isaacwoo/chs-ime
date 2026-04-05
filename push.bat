@echo off
cd /d "%~dp0"

echo ===================================
echo   chs-ime - Push to GitHub
echo ===================================
echo.

:: Check for uncommitted changes
git status --short > nul 2>&1
git diff --quiet --cached 2>nul
git status --porcelain | findstr /r "." >nul 2>&1
if errorlevel 1 goto :push

:: Show changed files
echo [Changed files]
git status --short
echo.

:: Prompt for commit message (ASCII safe)
set COMMIT_MSG=
set /p COMMIT_MSG=Commit message (Enter = "update"):
if "%COMMIT_MSG%"=="" set COMMIT_MSG=update

echo.
echo [1/3] git add ...
git add -A
if errorlevel 1 ( echo ERROR: git add failed & pause & exit /b 1 )

echo [2/3] git commit ...
git commit -m "%COMMIT_MSG%"
if errorlevel 1 ( echo ERROR: git commit failed & pause & exit /b 1 )

:push
echo [3/3] git push ...
git push origin main
if errorlevel 1 (
    echo.
    echo ERROR: push failed.
    echo   - Check network connection
    echo   - Check GitHub credentials in Windows Credential Manager
    echo.
    pause
    exit /b 1
)

echo.
echo ===================================
echo   Done! https://github.com/isaacwoo/chs-ime
echo ===================================
echo.
pause
