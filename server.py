import socket      
import threading   
import sys  
from utils import validar_mensaje       

# Variables globales
sockets_clientes = []  
clientes_lock = threading.Lock()   

def main():
    global sockets_clientes
    global clientes_lock

    host = '127.0.0.1'   
    port = 3001          

    socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
    socket_servidor.bind((host,port))  

    socket_servidor.listen(5)   

    socket_servidor.settimeout(1.0)  

    print(f"Servidor escuchando en {host}:{port}")
    
    try:
        while True:
            try:
                conex, direc = socket_servidor.accept()  
                                                         
                print(f"Se ha conectado el cliente desde {direc[0]}:{direc[1]}")

                with clientes_lock: 
                    sockets_clientes.append(conex)  
                
                thread = threading.Thread(target=manejo_de_cliente, args=(conex,direc)) 
                thread.daemon = True  
                thread.start() 

            except socket.timeout:
                pass
            except Exception as e:
                print(f"Error inesperado en el servidor principal: {e}")
            
    except KeyboardInterrupt:
                print("Servidor detenido por el usuario (Ctrl + C)")
    except Exception as e:
                print(f"Error inesperado en el servidor principal: {e}")
    finally:
                print("Cerrando sockets de clientes.....")
                with clientes_lock:
                    for s in list(sockets_clientes):
                        remover_cliente(s)


def manejo_de_cliente(conex, direc):
    """
    Función que se ejecuta en un hilo separado para manejar la comunicación
    con un cliente específico.
    """
    
    print(f"Hilo de manejo de cliente iniciado para {direc[0]}:{direc[1]}")

    try:
        while True:  
            
            datos = conex.recv(1024) 

            mensaje = datos.decode('utf-8').strip()

            if not validar_mensaje(mensaje):  
                print(f"Cliente en {direc[0]}:{direc[1]} se ha desconectado.")
                continue

            mensaje_para_broadcast = f"[{direc[0]}:{direc[1]}] {mensaje}\n"

            Broadcast_mensajes(mensaje_para_broadcast.encode('utf-8'), conex)

    except (ConnectionResetError, BrokenPipeError) as e:
        print(f"Cliente {direc[0]}:{direc[1]} se desconectó abruptamente: {e}")
    except Exception as e:
        print(f"Error inesperado con el cliente {direc[0]}:{direc[1]}: {e}")
    finally:
        remover_cliente(conex) 

def Broadcast_mensajes(bytes_mensajes, socket_envio):
    global sockets_clientes
    global clientes_lock

    clientes_para_enviar = []

    with clientes_lock:
        clientes_para_enviar = list(sockets_clientes)
    
    for socket_cliente in clientes_para_enviar:
        if socket_cliente != socket_envio:  
            try:
                socket_cliente.send(bytes_mensajes)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                print(f"Error al enviar mensaje a {socket_cliente.getpeername()}: {e}")
                remover_cliente(socket_cliente)
            except Exception as e:
                print(f"Error inesperado al enviar mensaje a {socket_cliente.getpeername()}: {e}")
                remover_cliente(socket_cliente)

def remover_cliente(socket_cliente):
    global sockets_clientes
    global clientes_lock

    try:
        nombre_cliente = socket_cliente.getpeername()

    except OSError:
        nombre_cliente = "<desconocido>"
    with clientes_lock:
        if socket_cliente in sockets_clientes:
            sockets_clientes.remove(socket_cliente)
            print(f"Cliente {nombre_cliente} desconectado y removido de la lista. Clientes activos: {len(sockets_clientes)}")
        else:
            print(f"Intento de remover cliente {nombre_cliente} que ya no esta en la lista.")
    
    try:
        socket_cliente.shutdown(socket.SHUT_RDWR)

    except OSError as e:
        print(f"Error al intentar apagar el socket {nombre_cliente}: {e}")

    finally:
        socket_cliente.close()
        print(f"Socket {nombre_cliente} cerrado.")
        
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nPrograma principal terminado por (Ctrl+C).")
    except Exception as e:
        print(f"Ha ocurrido un error inesperado en el servidor principal: {e}")
    sys.exit(0)
