
MAX_LEN_MENSAJE = 1024 # Limite para el mensaje

def validar_mensaje(contenido: str) -> bool:
    """
    Valida que el contenido del mensaje no esté vacío ni exceda el límite de bytes.
    """
    if not contenido or contenido.strip() == "":
        return False
        
    # Asumimos que el tamaño del contenido se acerca al número de bytes
    if len(contenido.encode('utf-8')) > MAX_LEN_MENSAJE:
        return False
        
    return True
