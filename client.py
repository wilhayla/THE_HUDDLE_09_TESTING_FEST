import socket
import threading
import time

cliente_activo = True

def main():
    global cliente_activo

    host = '127.0.0.1'
    port = 3000

    socket_cliente = None

    try:
        socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        print(f"Intentando conectar a {host}:{port}...")
        socket_cliente.connect((host, port))
        print("¡Conectado al servidor!")

        recibir_thread = threading.Thread(target=recibir_mensaje, args=(socket_cliente,), daemon=True)
        recibir_thread.start()

        enviar_mensajes(socket_cliente)

    except ConnectionRefusedError: 
        print(f"Error: Conexión rechazada. Asegúrate de que el servidor esté ejecutándose en {host}:{port}.")
    except Exception as e:
        print(f"Ocurrió un error inesperado en el cliente: {e}")
    finally:
        
        cliente_activo = False   

        if socket_cliente: 
            print("Cerrando conexión del cliente...")
            try:
                socket_cliente.shutdown(socket.SHUT_RDWR)  
            except OSError:  
                pass 
            except Exception as e:
                print(f"Advertencia al apagar el socket: {e}")
            finally:
                socket_cliente.close()  
            
        time.sleep(0.1)
                        
        print("Cliente finalizado.")

def enviar_mensajes(client_socket):
    print("Escribe tus mensajes. Escribe 'salir' para desconectarte.")
    while True:
        try:
            mensaje_usuario = input("> ")
            if mensaje_usuario.lower() == 'salir':
                print("Desconectando...")
                break
            client_socket.sendall(mensaje_usuario.encode('utf-8'))

        except OSError as e:
            print(f"Error de conexión al enviar: {e}")
            break
        except Exception as e:
            print(f"Error inesperado al enviar: {e}")
            break
    
    print("Hilo de envío terminado.")

def recibir_mensaje(socket_cliente):

    global cliente_activo

    socket_cliente.settimeout(0.5) 

    while cliente_activo:
        try:
            data = socket_cliente.recv(1024) 

            if not data: 
                print(f"El servidor se desconecto.")
                break 

            mensaje = data.decode('utf-8').strip()
            print(f"\r{mensaje}\n> ", end="")
        
        except socket.timeout:
            continue
        except OSError as e: 
            if cliente_activo: 
                print(f"Error al recibir mensaje: {e}")
            break 
            
        except Exception as e:
            if cliente_activo: 
                print(f"Error inesperado al recibir mensaje: {e}")
            break

    print("Saliendo del cliente...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nCliente detenido por el usuario (Ctrl+C).")
    except Exception as e:
        print(f"Ha ocurrido un error inesperado en el programa principal del cliente: {e}")
