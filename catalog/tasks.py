"""Update task registry and single-task runner."""

import threading

from .brands import BRANDS_BY_ID
from .config import BASE_DIR
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
        self.current_step = 0
        self.total_steps = 0
        self.current_step_label = ""

    def status(self):
        return {
            "running": self.running,
            "log": self.last_log,
            "brandId": self.current_brand_id or self.last_brand_id,
            "summary": self.last_summary,
            "step": self.current_step,
            "totalSteps": self.total_steps,
            "stepLabel": self.current_step_label,
            "progress": round((self.current_step / self.total_steps) * 100) if self.total_steps else 0,
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
            self.current_step = 0
            self.total_steps = len(task["steps"])
            self.current_step_label = task["start_log"]

        thread = threading.Thread(target=self._run_task, args=(task,), daemon=True)
        thread.start()
        return {"status": "started", "message": f"{task['name']}更新任务已启动，请等待完成..."}

    def preflight(self, brand_id):
        task = BRANDS_BY_ID.get(brand_id)
        if not task:
            return {
                "ok": False,
                "brandId": brand_id,
                "message": "未知更新任务",
                "issues": ["更新任务不存在"],
            }

        issues = []
        if self.running:
            issues.append(f"已有更新任务正在运行：{self.current_brand_id or self.last_brand_id}")

        script_checks = []
        for _log_message, step_name, script_name in task["steps"]:
            if script_name is None:
                continue
            script_path = BASE_DIR / script_name
            exists = script_path.exists()
            script_checks.append({
                "step": step_name or script_name,
                "script": script_name,
                "exists": exists,
            })
            if not exists:
                issues.append(f"缺少脚本：{script_name}")

        summary_parent = task["summary_path"].parent
        if not summary_parent.exists():
            issues.append(f"摘要目录不存在：{summary_parent}")

        return {
            "ok": not issues,
            "brandId": brand_id,
            "brandName": task["name"],
            "endpoint": task["endpoint"],
            "method": "POST",
            "steps": len(task["steps"]),
            "scripts": script_checks,
            "issues": issues,
            "message": "预检通过，可以开始更新。" if not issues else "预检发现问题，已阻止更新。",
        }

    def _run_task(self, task):
        started_at = now_iso()
        status = "success"
        error = ""
        try:
            reset_update_summary(task["summary_path"])
            for index, (log_message, step_name, script_name) in enumerate(task["steps"], 1):
                self.current_step = index
                self.current_step_label = log_message
                self.last_log = log_message
                if script_name is None:
                    backup_files()
                else:
                    run_step(step_name, script_name)
            self.last_summary = load_update_summary(task["summary_path"])
            self.last_log = task["summary"]()
            self.current_step_label = "更新完成"
        except Exception as exc:
            status = "failed"
            error = str(exc)
            self.last_log = f"❌ 更新出错：{exc}"
            self.current_step_label = "更新失败"
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
