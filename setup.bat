@echo off
:: Banking Security Training Application - Windows Docker Setup Script
:: This script helps you run the application with either PostgreSQL

setlocal enabledelayedexpansion

:: Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)
echo ✅ Docker is running

:: Check for docker-compose
docker-compose version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo ❌ docker-compose or 'docker compose' is not available
        pause
        exit /b 1
    ) else (
        set DOCKER_COMPOSE=docker compose
    )
) else (
    set DOCKER_COMPOSE=docker-compose
)
echo ✅ Using: !DOCKER_COMPOSE!

:: Create necessary directories
if not exist docker mkdir docker
if not exist logs mkdir logs

:menu
echo.
echo ============================================================
echo 🏦 BANKING SECURITY TRAINING - DOCKER SETUP
echo ============================================================
echo Choose your setup option:
echo.
echo 1) 🐘 Start full platform
echo 2) 📊 Show status
echo 3) 📝 Show logs
echo 4) 🛑 Stop all services
echo 5) 🧹 Cleanup (remove all data)
echo 6) ❓ Help
echo 7) 🚪 Exit
echo.

set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto start_platform
if "%choice%"=="2" goto show_status
if "%choice%"=="3" goto show_logs
if "%choice%"=="4" goto stop_services
if "%choice%"=="5" goto cleanup
if "%choice%"=="6" goto show_help
if "%choice%"=="7" goto exit_script
echo ❌ Invalid option. Please choose 1-7.
goto menu

:start_platform
echo.
echo ============================================================
echo 🐘 STARTING PLATFORM
echo ============================================================

:: Copy PostgreSQL environment file
if exist .env.postgres (
    copy .env.postgres .env >nul
    echo ✅ Using PostgreSQL environment configuration
) else (
    echo ⚠️ .env.postgres not found, using default values
)

echo 🚀 Starting PostgreSQL and Banking Application...
!DOCKER_COMPOSE! -f docker-compose.yml up -d

echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

:: Show service status
!DOCKER_COMPOSE! -f docker-compose.yml ps

echo 📊 Initialize database and populate with sample data
timeout /t 5 /nobreak >nul
docker exec banking-app flask db upgrade

echo 📊 Populating database with sample data...
timeout /t 5 /nobreak >nul
docker exec banking-app python python/populate_db.py

echo.
echo ============================================================
echo 🎉 FULL PLATFORM SETUP COMPLETE
echo ============================================================
echo Banking Application: http://localhost:5000

echo.
pause
goto menu


:show_status
echo.
echo ============================================================
echo 📊 DOCKER SERVICES STATUS
echo ============================================================

:: Check which configuration is active
if exist .env (
    findstr "postgresql" .env >nul 2>&1
    if not errorlevel 1 (
        echo Active Configuration: PostgreSQL
        !DOCKER_COMPOSE! -f docker-compose.yml ps
    )
) else (
    echo No active configuration found
)

echo.
echo All Banking App Containers:
docker ps --filter "name=banking" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.
pause
goto menu

:show_logs
echo.
set /p service="Which service logs? (banking-app, banking-postgres, evilcorp-server or Enter for all): "
if "%service%"=="" (
    echo Showing logs for all services...
    if exist .env (
        findstr "postgresql" .env >nul 2>&1
        if not errorlevel 1 (
            !DOCKER_COMPOSE! -f docker-compose.yml logs
        )
    )
) else (
    echo Showing logs for %service%...
    docker logs %service%
)
pause
goto menu

:stop_services
echo.
echo ============================================================
echo 🛑 STOPPING ALL SERVICES
echo ============================================================

if exist docker-compose.yml (
    echo Stopping full platform...
    !DOCKER_COMPOSE! -f docker-compose.yml down
)

echo ✅ All services stopped
pause
goto menu

:cleanup
echo.
echo ============================================================
echo 🧹 CLEANING UP
echo ============================================================
echo ⚠️ This will remove all containers, data volumes, and banking-app images!
echo ⚠️ The application will need to rebuild images on next startup.
set /p confirm="Are you sure? (y/N): "

if /i "%confirm%"=="y" (
    echo 🛑 Stopping and removing containers and volumes...
    if exist docker-compose.yml (
        !DOCKER_COMPOSE! -f docker-compose.yml down -v
    )

    echo 🗑️ Removing banking-app and evilcorp-server images...
    :: Remove images that contain "banking" in the name
    for /f "tokens=*" %%i in ('docker images --format "{{.Repository}}:{{.Tag}}" 2^>nul ^| findstr /i banking-app 2^>nul') do (
        echo Removing image: %%i
        docker rmi -f "%%i" >nul 2>&1
    )
    for /f "tokens=*" %%i in ('docker images --format "{{.Repository}}:{{.Tag}}" 2^>nul ^| findstr /i evilcorp 2^>nul') do (
        echo Removing image: %%i
        docker rmi -f "%%i" >nul 2>&1
    )

    docker container prune -f
    docker volume prune -f
    
    echo ✅ Cleanup complete - images will be rebuilt on next startup
) else (
    echo Cleanup cancelled
)
pause
goto menu

:show_help
echo.
echo ============================================================
echo ❓ HELP ^& TROUBLESHOOTING
echo ============================================================
echo 🐘 PostgreSQL Option:
echo    - Uses PostgreSQL 15 Alpine image
echo    - Lighter weight, faster startup
echo    - Good for development and testing
echo.
echo 📁 Important Files:
echo    - .env.postgres: PostgreSQL configuration
echo    - docker/: Database initialization scripts
echo.
echo 🔧 Troubleshooting:
echo    - Check Docker is running: docker info
echo    - View logs: Choose option 3 from menu
echo    - Reset everything: Choose option 5 from menu
echo    - Ports in use: 5000 (app), 5432 (db)
echo.
echo 🌐 Access Points:
echo    - Banking App: http://localhost:5000
echo    - Database Admin: http://localhost:8080
echo.
pause
goto menu

:exit_script
echo 👋 Goodbye!
exit /b 0