import os
import re
import sys
import time
import subprocess
import threading
import http.server
import socketserver

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
    """Запуск SSH-туннеля к localhost.run с перенаправлением на 127.0.0.1:8000."""
    print("[INFO] Подключение к туннелю localhost.run...")
    # Явно указываем 127.0.0.1 вместо localhost для избежания проблем с IPv6 на Windows
    proc = subprocess.Popen(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:127.0.0.1:8000", "nokey@localhost.run"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        encoding="utf-8"
    )

    url = None
    start_time = time.time()
    while time.time() - start_time < 15:
        line = proc.stdout.readline()
        if not line:
            break
        match = re.search(r"https://[a-zA-Z0-9-.]+\.lhr\.life", line)
        if match:
            url = match.group(0)
            break
            
    if not url:
        stderr_output = proc.stderr.read() if proc.poll() is not None else ""
        proc.terminate()
        raise Exception(f"Не удалось получить URL от localhost.run. {stderr_output}")
        
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
    try:
        # 0. Очищаем порт 8000 от зависших серверов
        kill_port_8000()
        
        # 1. Запуск веб-сервера
        start_http_server()
        
        # 2. Запуск туннеля
        url, tunnel_proc = start_ssh_tunnel()
        
        # 3. Обновление .env файла
        update_env_file(url)
        
        # 4. Отображение красивого баннера
        print("\n" + "="*60)
        print(" 🛍️  NICO MARKET WEBAPP ГОТОВ К РАБОТЕ!")
        print(f" 🔗  Динамический адрес каталога: {url}")
        print("="*60 + "\n")
        
        # 5. Запуск бота в текущем процессе
        print("[INFO] Запуск Telegram-бота...")
        bot_proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        # Периодически просыпаемся, чтобы Python мог обрабатывать Ctrl+C
        while bot_proc.poll() is None:
            time.sleep(0.5)
        
    except KeyboardInterrupt:
        print("\n[INFO] Получен сигнал остановки (Ctrl+C). Завершение процессов...")
    except Exception as e:
        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА] {e}")
    finally:
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
