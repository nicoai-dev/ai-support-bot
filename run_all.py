import os
import re
import sys
import time
import subprocess
import threading
import http.server
import socketserver
import urllib.request
import urllib.error

# Настройка кодировки для Windows консоли
if sys.platform == "win32":
    import codecs
    sys.stdout.reconfigure(encoding="utf-8")

def kill_port_8000():
    """Принудительное завершение процессов, занимающих порт 8000 (для Windows)."""
    try:
        # Получаем список процессов на порту 8000
        output = subprocess.check_output("netstat -ano | findstr :8000", shell=True, text=True)
        pids = set()
        for line in output.strip().split("\n"):
            if "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    pids.add(parts[-1])
        
        for pid in pids:
            if pid != "0":
                print(f"[INFO] Освобождаем порт 8000: убиваем процесс {pid}...")
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(0.5)
    except Exception:
        # Порт свободен или команда не нашла совпадений
        pass

def kill_orphaned_bots():
    """Принудительное завершение зависших процессов бота и туннеля."""
    try:
        if sys.platform == "win32":
            # Убиваем зависшие main.py
            ps_cmd = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "main.py" } | Select-Object -ExpandProperty ProcessId'
            output = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True)
            for line in output.split('\n'):
                pid = line.strip()
                if pid.isdigit() and int(pid) != os.getpid():
                    print(f"[INFO] Убиваем зависший процесс бота (PID {pid})...")
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Убиваем зависшие ssh.exe (localhost.run)
            ps_cmd_ssh = 'Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "ssh.exe" -and $_.CommandLine -match "localhost.run" } | Select-Object -ExpandProperty ProcessId'
            output_ssh = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd_ssh], text=True)
            for line in output_ssh.split('\n'):
                pid = line.strip()
                if pid.isdigit():
                    print(f"[INFO] Убиваем зависший SSH-туннель (PID {pid})...")
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
    except Exception:
        pass

def start_http_server():
    """Запуск фонового веб-сервера для WebApp на 127.0.0.1:8000."""
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            # Указываем абсолютный путь к папке webapp
            directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp")
            super().__init__(*args, directory=directory, **kwargs)
            
        def log_message(self, format, *args):
            pass  # Отключаем логи сервера

    def run():
        socketserver.TCPServer.allow_reuse_address = True
        try:
            # Биндимся строго на 127.0.0.1 для стабильности маршрутизации
            with socketserver.TCPServer(("127.0.0.1", 8000), QuietHandler) as httpd:
                httpd.serve_forever()
        except Exception as e:
            print(f"[!] Ошибка веб-сервера WebApp: {e}")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    print("[INFO] Локальный сервер WebApp успешно запущен на 127.0.0.1:8000.")

def start_ssh_tunnel():
    """Запуск SSH-туннеля к localhost.run с перенаправлением на 127.0.0.1:8000.
    Использует keep-alive для быстрого обнаружения разрыва соединения."""
    print("[INFO] Подключение к туннелю localhost.run...")
    # Keep-alive каждые 15 сек, макс 3 промаха = разрыв через ~45 сек простоя
    proc = subprocess.Popen(
        [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            "-o", "ExitOnForwardFailure=yes",
            "-R", "80:127.0.0.1:8000",
            "nokey@localhost.run"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        encoding="utf-8"
    )

    ignore_phrases = [
        "authenticated as anonymous user", "tls termination", "create an account",
        "Open your tunnel address", "Welcome to localhost.run", "favourite reverse tunnel",
        "manage custom domains", "More details on custom domains", "permission denied error",
        "free tunnel without a key", "explore using localhost.run", "your connection id is",
        "https://localhost.run/docs", "domain) at https://", "█", "▄", "▀", "═"
    ]

    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def should_print(text):
        if not text: return False
        clean = ansi_escape.sub('', text)
        if any(p in clean for p in ignore_phrases): return False
        # Игнорируем строки, состоящие только из спецсимволов рамки и пробелов
        if set(clean).issubset(set(" \t\r\n█▄▀═░▒▓■≡")): return False
        return True

    url = None
    start_time = time.time()
    while time.time() - start_time < 20:
        line = proc.stdout.readline()
        if not line:
            break
        line_clean = line.strip()
        if should_print(line_clean):
            print(f"[TUNNEL] {line_clean}")
            
        match = re.search(r"https://[a-zA-Z0-9-.]+\.lhr\.life", line)
        if match:
            url = match.group(0)
            break
            
    if not url:
        stderr_output = proc.stderr.read() if proc.poll() is not None else ""
        proc.terminate()
        raise Exception(f"Не удалось получить URL от localhost.run. {stderr_output}")

    # Запускаем потоки для постоянного чтения stdout и stderr,
    # чтобы процесс ssh не зависал из-за переполнения буфера (pipe) и выводил логи
    def stream_logs(pipe, prefix):
        try:
            for log_line in pipe:
                log_clean = log_line.strip()
                if should_print(log_clean):
                    print(f"{prefix} {log_clean}")
        except Exception:
            pass

    threading.Thread(target=stream_logs, args=(proc.stdout, "[TUNNEL]"), daemon=True).start()
    threading.Thread(target=stream_logs, args=(proc.stderr, "[TUNNEL]"), daemon=True).start()
        
    return url, proc

def update_env_file(url):
    """Обновление переменной WEBAPP_URL в файле .env."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"WEBAPP_URL={url}\n")
        return

    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    found = False
    for line in lines:
        if line.strip().startswith("WEBAPP_URL="):
            new_lines.append(f"WEBAPP_URL={url}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"WEBAPP_URL={url}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("[INFO] Файл .env успешно обновлен новым адресом тунлеля.")

def main():
    tunnel_proc = None
    bot_proc = None
    worker_proc = None
    tunnel_url = None
    running = True

    def restart_bot():
        """(Пере)запуск бота в отдельном процессе."""
        nonlocal bot_proc
        if bot_proc and bot_proc.poll() is None:
            try:
                bot_proc.terminate()
                bot_proc.wait(timeout=3)
            except Exception:
                try:
                    bot_proc.kill()
                except Exception:
                    pass

        print("[INFO] Запуск Telegram-бота...")
        bot_proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

    def restart_worker():
        """(Пере)запуск ARQ-воркера в отдельном процессе."""
        nonlocal worker_proc
        if worker_proc and worker_proc.poll() is None:
            try:
                worker_proc.terminate()
                worker_proc.wait(timeout=3)
            except Exception:
                try:
                    worker_proc.kill()
                except Exception:
                    pass

        print("[INFO] Запуск ARQ-воркера...")
        worker_proc = subprocess.Popen(
            [sys.executable, "-m", "arq", "workers.llm_worker.WorkerSettings"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

    def reconnect_tunnel():
        """Переподключение SSH-туннеля и обновление .env."""
        nonlocal tunnel_proc, tunnel_url
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                print(f"\n[TUNNEL] Попытка подключения #{attempt}...")
                new_url, new_proc = start_ssh_tunnel()
                tunnel_url = new_url
                tunnel_proc = new_proc
                update_env_file(tunnel_url)
                print(f"[TUNNEL] ✅ Туннель восстановлен: {tunnel_url}")
                return True
            except Exception as e:
                print(f"[TUNNEL] ❌ Попытка #{attempt} не удалась: {e}")
                wait_time = min(5 * attempt, 30)
                print(f"[TUNNEL] Повторная попытка через {wait_time} сек...")
                time.sleep(wait_time)
        print("[TUNNEL] 🔴 Не удалось восстановить туннель после всех попыток!")
        return False

    try:
        # 0. Очищаем старые процессы, чтобы не было конфликта токена
        kill_port_8000()
        kill_orphaned_bots()
        
        # 1. Запуск веб-сервера
        start_http_server()
        
        # 2. Запуск туннеля
        tunnel_url, tunnel_proc = start_ssh_tunnel()
        
        # 3. Обновление .env файла
        update_env_file(tunnel_url)
        
        # 4. Отображение красивого баннера
        print("\n" + "="*60)
        print(" 🛍️  NICO MARKET WEBAPP ГОТОВ К РАБОТЕ!")
        print(f" 🔗  Динамический адрес каталога: {tunnel_url}")
        print("="*60 + "\n")
        
        # 5. Запуск бота и ARQ-воркера
        restart_bot()
        restart_worker()
        
        # 6. Основной цикл с мониторингом туннеля
        while running:
            time.sleep(5)

            # Проверка бота
            if bot_proc and bot_proc.poll() is not None:
                print("[WARN] Бот-процесс упал. Перезапуск...")
                restart_bot()

            # Проверка воркера
            if worker_proc and worker_proc.poll() is not None:
                print("[WARN] ARQ-воркер упал. Перезапуск...")
                restart_worker()

            # Проверка туннеля (упал ли сам процесс)
            if tunnel_proc and tunnel_proc.poll() is not None:
                exit_code = tunnel_proc.returncode
                print(f"\n[TUNNEL] ⚠️  SSH-туннель упал (exit code: {exit_code}). Переподключение...")
                if reconnect_tunnel():
                    # Перезапускаем бота, чтобы подхватил новый WEBAPP_URL
                    restart_bot()
                else:
                    print("[FATAL] Невозможно восстановить туннель. Завершение.")
                    break
            
            # Активный пинг туннеля, т.к. SSH может висеть, даже если сервер обрубил порт
            elif tunnel_url:
                try:
                    req = urllib.request.Request(tunnel_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        html = response.read().decode('utf-8', errors='ignore')
                        if "no tunnel here" in html.lower() or "tunnel not found" in html.lower():
                            print("\n[TUNNEL] ⚠️ Обнаружена страница ошибки (Туннель закрыт сервером!). Принудительный реконнект...")
                            if tunnel_proc:
                                tunnel_proc.kill()
                except urllib.error.HTTPError as e:
                    if e.code in (404, 502, 503, 504):
                        print(f"\n[TUNNEL] ⚠️ Туннель вернул ошибку HTTP {e.code}. Принудительный реконнект...")
                        if tunnel_proc:
                            tunnel_proc.kill()
                except Exception:
                    # Игнорируем обычные сетевые ошибки (например timeout), чтобы не спамить реконнектами
                    pass
        
    except KeyboardInterrupt:
        print("\n[INFO] Получен сигнал остановки (Ctrl+C). Завершение процессов...")
    except Exception as e:
        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА] {e}")
    finally:
        running = False
        # Корректно завершаем процесс бота
        if bot_proc:
            try:
                bot_proc.terminate()
                bot_proc.wait(timeout=2)
                print("[INFO] Telegram-бот успешно остановлен.")
            except Exception:
                try:
                    bot_proc.kill()
                    print("[INFO] Telegram-бот принудительно завершен.")
                except Exception:
                    pass

        # Корректно завершаем ARQ-воркер
        if worker_proc:
            try:
                worker_proc.terminate()
                worker_proc.wait(timeout=2)
                print("[INFO] ARQ-воркер успешно остановлен.")
            except Exception:
                try:
                    worker_proc.kill()
                    print("[INFO] ARQ-воркер принудительно завершен.")
                except Exception:
                    pass

        # Корректно завершаем туннель
        if tunnel_proc:
            try:
                tunnel_proc.terminate()
                tunnel_proc.wait(timeout=2)
                print("[INFO] SSH-туннель закрыт.")
            except Exception:
                try:
                    tunnel_proc.kill()
                    print("[INFO] SSH-туннель принудительно закрыт.")
                except Exception:
                    pass

if __name__ == "__main__":
    main()

