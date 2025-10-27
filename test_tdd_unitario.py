import pytest
from utils import validar_mensaje

def test_validar_mensaje_vacio_falla():
    """Caso Negativo: Verifica que un mensaje vacío (solo espacios o None) sea rechazado."""
    
    # Intenta validar un mensaje vacío
    assert validar_mensaje("  ") is False
    
    # Intenta validar un mensaje nulo
    assert validar_mensaje("") is False

def test_validar_mensaje_valido_pasa():
    """Caso Positivo: Verifica que un mensaje con contenido pase la validación."""
    
    # Intenta validar un mensaje correcto
    assert validar_mensaje("Hola mundo!") is True

def test_validar_mensaje_demasiado_largo_falla():
    """Caso Negativo: Verifica que un mensaje muy largo (ej. > 1024) sea rechazado."""
    
    # Creamos un string de 1025 caracteres
    mensaje_largo = "A" * 1025
    
    assert validar_mensaje(mensaje_largo) is False
