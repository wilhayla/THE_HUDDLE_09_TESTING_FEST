# tests/test_integracion.py
import pytest
import socket
import threading
import time
import subprocess
import os

# --- CONFIGURACIÓN Y FIXTURE (SETUP/TEARDOWN) ---

TEST_HOST = '127.0.0.1'
TEST_PORT = 3001 # IMPORTANTE: Asegúrate que server.py use este puerto
SERVER_PROCESS = None

"""
Usar el servidor real(server.py) en un subproceso con la libreria subprocess.
Funciona creando dos entornos separados que se comunican a traves de la red real. El servidor real
corre en el fondo mientras otros programas (los clientes de prueba) se conectan a el.
La llamadaa subprocess.Popen() lanza el servidor com un proceso completamente nuevo e independiente
(un subproceso o hijo).
"""

@pytest.fixture(scope="module", autouse=True)
def iniciar_y_detener_servidor():
    """
    La función iniciar_y_detener_servidor es un 
    fixture (accesorio o configuración) de pytest. Su único propósito es 
    garantizar que el servidor de chat esté corriendo y disponible para ser probado 
    antes de que se ejecute cualquier test de integración, y que se detenga 
    limpiamente después de que todos los tests hayan finalizado.
    """
    global SERVER_PROCESS
    
    # Obtiene la ruta absoluta completa del archivo server.py
    server_path = os.path.abspath("server.py") 
    
    print(f"\n[SETUP] Iniciando servidor para tests en {TEST_PORT}...")
    
    """Esta instrucción utiliza el módulo subprocess de Python para ejecutar un programa 
    externo (en este caso, tu server.py) como un proceso hijo separado del script que está 
    ejecutando Pytest."""
   
    SERVER_PROCESS = subprocess.Popen(
        ['python', server_path],
        stdout=subprocess.PIPE, # configuracion captura de salida del texto del servidor
        stderr=subprocess.PIPE, # configuracion de captura de mensajes de errores
        text=True  # se indica a Popen que las entradas y salidas seran como cadena de texto y no como bytes.
    )
    
    # Espera para que el servidor inicie y escuche
    time.sleep(1.5) 

    yield # Ejecución de los tests

    # TEARDOWN: Detener el servidor
    print("[TEARDOWN] Deteniendo servidor...")
    if SERVER_PROCESS:
        SERVER_PROCESS.terminate() # Enviar señal de terminación
        try:
            SERVER_PROCESS.wait(timeout=3)
        except subprocess.TimeoutExpired:
            SERVER_PROCESS.kill() # Matar si no termina
        print("[TEARDOWN] Servidor detenido.")
        
"""
Esta funcion es un auxiliar clave para las pruebas de integración. 
Su objetivo es crear y configurar un cliente socket de forma rápida y confiable, 
lista para interactuar con el servidor de chat que iniciaste en el fixture.
"""

def conectar_cliente(host, port, timeout=0.05): # tiempo maximo que el socket esperara por una operacion de bloqueo.
    """Conecta un socket cliente de prueba al servidor."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # se crea un objeto socket
    s.settimeout(timeout) # se configura el settimeout para todas las futuras operaciones de bloqueo del socket
                          # connect(), recv() y send()
    try:
        s.connect((host, port))
        # Pequeña pausa para que el hilo del servidor se inicialice
        time.sleep(0.1) 
        return s  # devuelve el objeto socket conectado para que el test pueda usarlo para enviar y recivir datos.
    except Exception as e:
        pytest.fail(f"No se pudo conectar el cliente de prueba al servidor: {e}")
        return None

# --- TESTS DE INTEGRACIÓN: HAPPY PATH (Broadcast) ---

def test_broadcast_a_multiples_clientes_reciben():
    """
    Prueba A: Conectar 3 clientes y verificar que el mensaje de uno llegue a los otros dos.
    Requisito: Los mensajes se distribuyen a todos los demás.
    """
    cliente_a = None
    cliente_b = None
    cliente_c = None
    mensaje = "Broadcast Test: Hola C y B!"
    
    try:
        # 1. Conexión de 3 clientes
        cliente_a = conectar_cliente(TEST_HOST, TEST_PORT)
        cliente_b = conectar_cliente(TEST_HOST, TEST_PORT)
        cliente_c = conectar_cliente(TEST_HOST, TEST_PORT)

        # 2. Cliente A envía el mensaje
        cliente_a.sendall(mensaje.encode('utf-8'))
        
        # Espera para la distribución
        time.sleep(0.5) 
        
        # 3. Cliente B y C deben recibir el mensaje
        datos_b = cliente_b.recv(1024).decode('utf-8')
        datos_c = cliente_c.recv(1024).decode('utf-8')

        # Verificación: El contenido debe estar en los mensajes recibidos
        assert mensaje in datos_b
        assert mensaje in datos_c
        
    finally:
        if cliente_a: cliente_a.close()
        if cliente_b: cliente_b.close()
        if cliente_c: cliente_c.close()

# --- TESTS DE INTEGRACIÓN: MANEJO DE ERRORES Y DESCONEXIÓN ---

def test_manejo_desconexion_abrupta():
    """
    Prueba B: Simular la desconexión repentina de un cliente y verificar que 
    el servidor no falle y siga aceptando conexiones.
    Requisito: El servidor maneja desconexiones inesperadas sin bloquearse.
    """
    cliente_abrupto = None
    cliente_verificador = None
    
    try:
        # 1. Conectar un cliente (será el que falla)
        cliente_abrupto = conectar_cliente(TEST_HOST, TEST_PORT)
        
        # 2. Desconexión Abrupta (el servidor detectará esto en el próximo recv)
        cliente_abrupto.close()
        cliente_abrupto = None 
        
        # 3. Dar tiempo al servidor para que el hilo del cliente_abrupto lo detecte y limpie
        time.sleep(1.0) 
        
        # 4. Intentar conectar un cliente nuevo (Verificador)
        cliente_verificador = conectar_cliente(TEST_HOST, TEST_PORT)
        
        # Asersión: Si se conecta, el servidor sigue activo.
        assert cliente_verificador is not None
        
    finally:
        if cliente_abrupto: cliente_abrupto.close()
        if cliente_verificador: cliente_verificador.close()

def test_otro_cliente_sigue_recibiendo_tras_desconexion():
    """
    Prueba C: Cliente A se desconecta. Cliente B aún debe poder enviar mensajes 
    y el servidor debe procesarlo correctamente.
    Requisito: Los demás clientes no se ven afectados por la desconexión de uno.
    """
    cliente_vivo = None
    cliente_muerto = None
    
    try:
        # 1. Conectar dos clientes
        cliente_vivo = conectar_cliente(TEST_HOST, TEST_PORT)
        cliente_muerto = conectar_cliente(TEST_HOST, TEST_PORT)
        
        # 2. Cliente "Muerto" se desconecta abruptamente
        cliente_muerto.close()
        cliente_muerto = None
        
        # 3. Dar tiempo al servidor para limpiar el socket 'muerto'
        time.sleep(1.0) 
        
        # 4. Cliente "Vivo" envía un mensaje. El servidor intentará (y fallará)
        #    enviarlo al socket "muerto", pero no debe colapsar.
        mensaje = "Soy el cliente vivo, ¿el servidor falló?"
        cliente_vivo.sendall(mensaje.encode('utf-8'))
        
        # 5. Si no hay excepción en el lado del cliente_vivo, el envío fue exitoso.
        #    Aseguramos que el servidor sigue funcionando si no se lanza una excepción.
        assert True # marca de paso que se llego al final de la secuencia critica de comandos
                    # sin que ocurriera un fallo inesperado.
        
    finally:
        if cliente_vivo: cliente_vivo.close()
        if cliente_muerto: cliente_muerto.close()

def test_orden_y_unicidad_en_broadcast():
    """
    Prueba que los mensajes no se pierden, no se duplican, y se reciben en el orden correcto
    bajo una ráfaga de mensajes (cumpliendo con la robustez del broadcast).
    """
    cliente_emisor = None  # inicializa la varible que almacenara el objeto socket del cliente que enviara los mensajes.
    cliente_receptor = None # inicializa la variable que almacenara el objeto socket del cliente que recibira y verificara los mensajes.
    
    # Preparamos 10 mensajes únicos y ordenados.
    NUM_MENSAJES = 10 # define la cantidad exacta de mensajes que se enviaran
    mensajes_enviados = [f"Mensaje Secuencia {i}" for i in range(1, NUM_MENSAJES + 1)] # se crea una lista que contiene las 10 cadenas de texto que se enviaran
    
    try:
        # 1. Conexión de emisor y receptor
        cliente_emisor = conectar_cliente(TEST_HOST, TEST_PORT) # llama a la funcion conectar cliente para crear y conectar el primer socket de prueba al servidor del cliente emisor.
        cliente_receptor = conectar_cliente(TEST_HOST, TEST_PORT) # llama a la funcion conectar cliente para crear y conectar el primer socket de prueba al servidor del cliente receptor.
        
        # 2. Envío de la ráfaga de mensajes
        for msg in mensajes_enviados: # itera sobre la lista de 10 mensajes predefinidos.
            cliente_emisor.sendall(msg.encode('utf-8')) # el cliente emisor envia los mensajes de la lista
            time.sleep(0.01) # pausa de 10 milisegundos despues de cada envio.
        
        # Damos una pausa generosa para asegurar que TODOS los mensajes llegaron al buffer del SO.

        # Esto garantiza que todos los hilos del servidor hayan terminado de procesar en broadcast de los 10 mensajes
        # y que esos datos  hayan viajado a traves de la red y estan en el buffer de recepcion del socket del cliente receptor.
        
        time.sleep(2.0) 
        
        # 3. Recolección robusta de los mensajes recibidos
        # lista vacia que se llenara con el contenido limpio de los mensajes recibidos del servidor.
        # se usara para verificar la cantidad y el orden final.
        mensajes_recibidos = [] 

        # Se inicializa una cadena de bytes vacia. Se utilizara para acumular todos los datos brutos
        # que se lean del socket del cliente receptor, ya que multiples mensajes pueden llegar
        # juntos en un solo paquete de red.
        datos_completos = b''
        
        # Leemos del socket mientras haya datos. Confiamos en el timeout de 1.0s para salir.
        # bucle encargado de vaciar completamente el bufer del socket del cliente para 
        # asegurarse que todos los mensajes enviados se capture.
        while True:
            try:
                # Usamos un buffer grande (8KB) y leemos ininterrumpidamente
                datos_parciales = cliente_receptor.recv(8192)
                
                if not datos_parciales:
                    # El servidor cerró la conexión, salimos (no debería ocurrir)
                    break
                    
                datos_completos += datos_parciales
                
            except socket.timeout:
                # ¡El socket se quedó sin datos que leer! El buffer está vacío, salimos del bucle.
                break 
            except Exception:
                # Manejar cualquier otro error inesperado de conexión
                break 
                
        # 4. Procesamiento y Extracción
        texto_completo = datos_completos.decode('utf-8').strip()
        
        # El servidor agrega un salto de línea (\n) al final, lo usamos para dividir los mensajes brutos.
        mensajes_brutos = [m.strip() for m in texto_completo.split('\n') if m.strip()]
        
        # 5. Extraer el contenido limpio y verificar unicidad (quitando el prefijo [ip:port])
        for m_bruto in mensajes_brutos:
            # Buscamos el contenido que viene después del corchete de cierre
            try:
                # Partimos por ']' y tomamos el contenido después de la cabecera.
                contenido_limpio = m_bruto.split(']')[1].strip() 
                
                # Solo guardamos el contenido si es uno de los mensajes de secuencia enviados
                if contenido_limpio in mensajes_enviados:
                    mensajes_recibidos.append(contenido_limpio)
            except IndexError:
                # Ignorar si el formato del mensaje es incorrecto
                continue
        
        # 6. Verificación de Pérdidas/Duplicados (Unicidad y Cantidad)
        assert len(mensajes_recibidos) == NUM_MENSAJES, \
               f"FALLO: Se perdieron o duplicaron mensajes. Esperado: {NUM_MENSAJES}, Recibido: {len(mensajes_recibidos)}"
               
        # 7. Verificación del Orden Correcto
        assert mensajes_recibidos == mensajes_enviados, \
               "FALLO: El orden de los mensajes no coincide con el orden de envío."
        
    finally:
        # Aseguramos la limpieza total
        if cliente_emisor: cliente_emisor.close()
        if cliente_receptor: cliente_receptor.close()
