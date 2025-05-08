import sys

def log_debug(message: str):
    """Функция для отладочного логирования"""
    print(f"[DEBUG] {message}", flush=True)
    sys.stdout.flush()