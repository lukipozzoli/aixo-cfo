import os

# Servicios que convierten audio e imágenes en texto.
#
# Van juntos porque cumplen el mismo rol dentro del sistema: los usa el
# Preprocessor para que al Router siempre le llegue texto, sin importar en qué
# formato haya escrito el usuario.

# Audio hablado → texto.
TRANSCRIPTION_PROVIDER: str = os.environ["TRANSCRIPTION_PROVIDER"]
TRANSCRIPTION_MODEL: str = os.environ["TRANSCRIPTION_MODEL"]

# Imágenes (fotos de comprobantes, capturas) → descripción en texto.
VISION_PROVIDER: str = os.environ["VISION_PROVIDER"]
VISION_MODEL: str = os.environ["VISION_MODEL"]
