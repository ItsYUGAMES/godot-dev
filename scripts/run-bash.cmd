@echo off
REM Windows launcher for the bash entry scripts, for hosts that run hook commands through cmd.exe
REM with the Windows PATH (Codex commandWindows). Git for Windows normally puts only Git\cmd
REM (git.exe) on that PATH, so a bare "bash" fails with exit code 1.
REM Bash lookup adapted from obra/superpowers hooks/run-hook.cmd (MIT). No labels: cmd.exe
REM misparses labels in LF files.
REM Usage: run-bash.cmd <script in this folder> [args...]
setlocal
set "BASH_EXE="

REM Standard system-wide and per-user Git for Windows installs.
if exist "C:\Program Files\Git\bin\bash.exe" set "BASH_EXE=C:\Program Files\Git\bin\bash.exe"
if not defined BASH_EXE if exist "C:\Program Files (x86)\Git\bin\bash.exe" set "BASH_EXE=C:\Program Files (x86)\Git\bin\bash.exe"
if not defined BASH_EXE if defined LOCALAPPDATA if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" set "BASH_EXE=%LOCALAPPDATA%\Programs\Git\bin\bash.exe"

REM Git installed elsewhere: git.exe on PATH lives in Git\cmd, bash.exe in Git\bin next to it.
if not defined BASH_EXE if defined SystemRoot for /f "delims=" %%G in ('"%SystemRoot%\System32\where.exe" $PATH:git.exe 2^>nul') do if not defined BASH_EXE if exist "%%~dpG..\bin\bash.exe" set "BASH_EXE=%%~dpG..\bin\bash.exe"

REM bash on PATH (MSYS2, Cygwin), skipping the WSL launchers, which fail without a Linux distro.
if not defined BASH_EXE if defined SystemRoot for /f "delims=" %%B in ('"%SystemRoot%\System32\where.exe" $PATH:bash 2^>nul') do if not defined BASH_EXE if not "%%~xB"=="" if /i not "%%~dpB"=="%SystemRoot%\System32\" if /i not "%%~dpB"=="%SystemRoot%\Sysnative\" if /i not "%%~dpB"=="%LOCALAPPDATA%\Microsoft\WindowsApps\" set "BASH_EXE=%%B"

REM No bash: exit quietly. The hook runs in every workspace, most of them not Godot projects, and
REM the skill works without it; only the automatic add-on install is skipped.
if not defined BASH_EXE exit /b 0

REM Outside any parenthesized block, so %ERRORLEVEL% is read after bash exits.
"%BASH_EXE%" "%~dp0%~1" %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%
