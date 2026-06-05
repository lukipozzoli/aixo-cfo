from abc import ABC, abstractmethod
from typing import Callable


class Scheduler(ABC):
    # Interfaz genérica para cualquier motor de scheduling.
    # Permite cambiar APScheduler, Railway cron, o cualquier otro sin tocar la lógica.

    @abstractmethod
    def register_job(self, job_id: str, func: Callable, cron_expr: str, **kwargs) -> None:
        # Registra un job con un identificador único y una expresión cron.
        # cron_expr usa formato estándar: "0 9 * * *" = todos los días a las 9am.
        pass

    @abstractmethod
    def run(self) -> None:
        # Inicia el scheduler y bloquea la ejecución (o corre en background según impl).
        pass
