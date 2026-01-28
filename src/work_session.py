"""
Gestión de sesiones de trabajo (clock in/out)
"""
from datetime import datetime
from typing import Optional, Dict


class WorkSession:
    """Gestiona las sesiones de trabajo (clock in/out)"""

    def __init__(self):
        self.active_sessions: Dict[int, dict] = {}  # user_id -> session data

    def clock_in(self, user_id: int, project: str, task: Optional[str] = None) -> Dict:
        """Registrar entrada"""
        self.active_sessions[user_id] = {
            "start_time": datetime.now(),
            "project": project,
            "task": task,
            "breaks": []
        }
        return self.active_sessions[user_id]

    def clock_out(self, user_id: int, description: str = "") -> Optional[Dict]:
        """Registrar salida y calcular horas"""
        if user_id not in self.active_sessions:
            return None

        session = self.active_sessions[user_id]
        end_time = datetime.now()
        duration = end_time - session["start_time"]

        # Restar tiempo de breaks
        total_break_time = sum(
            (b["end"] - b["start"]).total_seconds()
            for b in session["breaks"] if "end" in b
        )

        total_hours = (duration.total_seconds() - total_break_time) / 3600

        result = {
            "start_time": session["start_time"],
            "end_time": end_time,
            "total_hours": round(total_hours, 2),
            "project": session["project"],
            "task": session["task"],
            "description": description
        }

        del self.active_sessions[user_id]
        return result

    def start_break(self, user_id: int) -> bool:
        """Iniciar pausa"""
        if user_id in self.active_sessions:
            self.active_sessions[user_id]["breaks"].append({
                "start": datetime.now()
            })
            return True
        return False

    def end_break(self, user_id: int) -> bool:
        """Finalizar pausa"""
        if user_id in self.active_sessions:
            breaks = self.active_sessions[user_id]["breaks"]
            if breaks and "end" not in breaks[-1]:
                breaks[-1]["end"] = datetime.now()
                return True
        return False

    def get_session(self, user_id: int) -> Optional[Dict]:
        """Obtener sesión activa"""
        return self.active_sessions.get(user_id)