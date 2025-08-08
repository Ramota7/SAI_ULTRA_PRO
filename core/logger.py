# Logging estructurado, auditable y exportable
import os
import json
from datetime import datetime

class Logger:
    def __init__(self, log_path='sai_ultra_pro/ia/plan_log.txt', json_path='sai_ultra_pro/ia/plan_log.json'):
        self.log_path = log_path
        self.json_path = json_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)

    def log(self, msg, level="INFO", extra=None):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"{ts} | {level} | {msg}"
        print(line)
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
        # Log estructurado en JSON
        log_entry = {"timestamp": ts, "level": level, "msg": msg}
        if extra:
            log_entry.update(extra)
        with open(self.json_path, 'a', encoding='utf-8') as jf:
            jf.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def error(self, msg, extra=None):
        self.log(msg, level="ERROR", extra=extra)

    def warn(self, msg, extra=None):
        self.log(msg, level="WARN", extra=extra)

    def audit(self, msg, extra=None):
        self.log(msg, level="AUDIT", extra=extra)
