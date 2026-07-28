# AGENTS.md — Reglas de Ejecución

Este archivo define cómo trabajamos en este proyecto. Codex lo lee al inicio de cada sesión y lo respeta en todo momento.

---

## Reglas de Ejecución

### Aprobación obligatoria
- Antes de crear, modificar o eliminar cualquier archivo, explicar QUÉ se va a hacer y POR QUÉ.
- Ningún cambio se ejecuta sin aprobación explícita del usuario.
- Si hay más de una forma de resolver algo, presentar las opciones con sus tradeoffs antes de proceder.
- Ir de a una cosa a la vez. No anticiparse.

### Comunicación
- Cada decisión técnica debe tener un motivo claro y dicho en voz alta.
- Si algo no se entiende, preguntar antes de asumir.
- El usuario tiene que entender el 100% de lo que hay en el repositorio en todo momento.

---

## Principios de Diseño

### SOLID
Todo el código debe respetar los principios SOLID:
- **S** — Una clase, una responsabilidad.
- **O** — Abierto para extensión, cerrado para modificación.
- **L** — Las subclases deben poder reemplazar a sus padres sin romper nada.
- **I** — Interfaces específicas, no generales.
- **D** — Depender de abstracciones, no de implementaciones concretas.

### Reutilizable por diseño
- El core del agente es genérico. Nada específico de AIXO vive en la lógica.
- Todo lo que es específico de una empresa (credenciales, configuración, esquemas) vive en archivos de configuración separados.
- El proyecto está pensado para ser reimplementado en otras empresas sin tocar el core.

### Skills
- En el futuro, este proyecto será la base para skills reutilizables.
- Cada módulo debe estar suficientemente desacoplado para poder ser extraído como skill independiente.

### Independencia del modelo de LLM
- El agente no depende de ningún proveedor específico de LLM.
- Existe una interfaz abstracta `LLMProvider` con métodos `chat()` y `complete()`.
- Las implementaciones concretas (`ClaudeProvider`, `OpenAIProvider`, etc.) se configuran por empresa.
- El core nunca importa directamente ningún SDK de LLM.

### Independencia del scheduler
- Los cron jobs no dependen de ninguna tecnología específica de scheduling.
- Existe una interfaz abstracta `Scheduler` con métodos `register_job()` y `run()`.
- La implementación concreta (APScheduler, Railway, cron del sistema) se configura por empresa.

---

## Convenciones de Código

### Lenguaje
- **Código**: inglés.
- **Comentarios en el código**: español, con detalle. Todo el código tiene que estar comentado. No se omiten comentarios.
- **Documentación**: español.

### Estilo
- Python como lenguaje principal.
- Comentarios explicando el POR QUÉ, no el QUÉ. El QUÉ lo dice el código.
- Sin hardcodeo de valores. Todo configurable.
- Sin features anticipadas. Solo lo que se necesita ahora.

---

## Documentación Viva

- `docs/context.md` — contexto completo del proyecto: arquitectura, agentes, eventos, tools y flujos. Se actualiza cada vez que algo cambia.
- Este archivo (`AGENTS.md`) — reglas de ejecución. Se actualiza si cambian las reglas de trabajo.

### Reglas de actualización
- Cada vez que se agrega, modifica o elimina una tabla, columna o relación en la base de datos, actualizar `docs/context.md`.
- Cada vez que se define o modifica un cron job, agente, conector o flujo, actualizar `docs/context.md`.
- Nunca dejar `docs/context.md` con información desactualizada o incompleta al finalizar una sesión.
- Si algo está "a definir", dejarlo marcado explícitamente como tal. No inventar ni asumir.

---

## Visión a Gran Escala

Este proyecto es un **agente CFO** diseñado para gestionar las finanzas de una empresa de manera autónoma e inteligente. La primera implementación es para AIXO, un estudio de diseño/tecnología argentino.

El agente:
- Lee y procesa eventos financieros desde múltiples fuentes (mail, bancos, otros agentes).
- Registra, clasifica y concilia movimientos financieros en Supabase.
- Genera reportes, proyecciones y alertas de riesgo.
- Se comunica con el usuario por Telegram.
- Está diseñado para ser reutilizado en otras empresas con mínima configuración.

La arquitectura es multi-agente:
- Un **agente financiero central** maneja toda la lógica de negocio.
- **Conectores** (Gmail, Linear, Bancos) normalizan eventos externos.
- Un **Router** clasifica mensajes de Telegram.
- Un **Conversation Agent** y un **Report Agent** presentan la información al usuario.

Todo está documentado en `docs/context.md`.

## Imported Claude Cowork project instructions

proyecto compartido con mi socio, la idea es armar un agente de ia financiero en conjunto
