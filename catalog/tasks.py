"""Update task registry and single-task runner."""

import threading

from .brands import BRANDS_BY_ID
from .files import backup_files, run_step
from .history import append_update_history, now_iso
from .summaries import load_update_summary, reset_update_summary


class UpdateManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.running = False
        self.last_log = ""
        self.current_brand_id = None
        self.last_brand_id = None
        self.last_summary = {}

    def status(self):
        return {
            "running": self.running,
            "log": self.last_log,
            "brandId": self.current_brand_id or self.last_brand_id,
            "summary": self.last_summary,
        }

    def start(self, brand_id):
        task = BRANDS_BY_ID[brand_id]
        with self._lock:
            if self.running:
                return {
                    "status": "running",
                    "message": "更新任务正在执行中，请耐心等待...",
                    "log": self.last_log,
                }
            self.running = True
            self.current_brand_id = brand_id
            self.last_brand_id = brand_id
            self.last_summary = {}
            self.last_log = task["start_log"]

        thread = threading.Thread(target=self._run_task, args=(task,), daemon=True)
        thread.start()
        return {"status": "started", "message": f"{task['name']}更新任务已启动，请等待完成..."}

    def _run_task(self, task):
        started_at = now_iso()
        status = "success"
        error = ""
        try:
            reset_update_summary(task["summary_path"])
            for log_message, step_name, script_name in task["steps"]:
                self.last_log = log_message
                if script_name is None:
                    backup_files()
                else:
                    run_step(step_name, script_name)
            self.last_summary = load_update_summary(task["summary_path"])
            self.last_log = task["summary"]()
        except Exception as exc:
            status = "failed"
            error = str(exc)
            self.last_log = f"❌ 更新出错：{exc}"
        finally:
            append_update_history({
                "brandId": task["id"],
                "brandName": task["name"],
                "status": status,
                "startedAt": started_at,
                "endedAt": now_iso(),
                "summary": self.last_summary,
                "log": self.last_log,
                "error": error,
            })
            self.running = False
            self.current_brand_id = None
