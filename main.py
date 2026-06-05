# Punto de entrada del agente CFO de AIXO.
# Los agentes se registran e inicializan acá a medida que se construyen.
# Ningún provider se instancia directamente acá — cada agente usa build_llm_provider con su config.

if __name__ == "__main__":
    print("Agente CFO iniciado.")
