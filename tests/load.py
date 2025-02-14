import socket
import threading
from crypto import *
from time import sleep

global server_socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.connect(("127.0.0.1", 5000))

current_socket = None
running = False
in_room = False  # Variável para controlar se o usuário já está em uma sala
logged_in = False  # Variável para controlar se o usuário está logado
client_name = ""
current_room = ""

def send_command(command):
    """Envia comandos ao servidor central."""
    server_socket.sendall(command.encode())
    return server_socket.recv(1024).decode()

def register():
        response = send_command(f"REGISTER anna anna123")

def login():
    """Faz o login do usuário."""
    global logged_in, client_name

    response = send_command(f"LOGIN anna anna123")
    if response == "LOGIN_OK":
        logged_in = True
        client_name = "anna"

def logout():
    """Desloga o usuário."""
    global logged_in, in_room, current_socket, running, client_name
    if logged_in:
        logged_in = False
        client_name = ""
        if in_room:
            running = False
            current_socket.close()
            current_socket = None
            in_room = False

def create_room():
    """Cria uma nova sala, se o usuário estiver logado."""
    response = send_command(f"CREATE futebol")

def join_room():
    """Lista salas disponíveis e permite escolher uma para entrar."""
    global current_socket, running, in_room, current_room

    if in_room:
        return
    
    response = send_command("LIST_ROOMS")
    salas = response.split("\n") if response else []
    
    if len(salas) == 1 and salas[0] == " ":
        return
        

    response = send_command(f"JOIN futebol")

    if response.startswith("JOIN_OK"):
        port = int(response.split()[1])
        current_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        current_socket.connect(("127.0.0.1", port))
        running = True
        in_room = True
        current_room = "futebol"
        threading.Thread(target=receive_messages, daemon=True).start()

    else:
        return

def leave_room():
    """Sai da sala atual e libera o usuário para entrar em outra."""
    global current_socket, running, in_room, current_room
    
    if current_socket:
        running = False
        current_socket.close()
        current_socket = None
        in_room = False  # Agora o usuário pode entrar em outra sala
        current_room = ""

def send_message():
    try:
        global current_socket, current_room
        if current_socket:
            msg = "olar"
            msgsend = client_name + ": "
            msgsend += msg + "\n"

            key = generate_key_from_string(current_room)

            msgsend = encrypt_message(key, msgsend)

            if msg:
                current_socket.sendall(msgsend)
    except Exception as e:
        return

def receive_messages():
    """Recebe mensagens da sala."""
    global current_socket, running, current_room
    while running:
        try:
            msg = current_socket.recv(1024)
            
            key = generate_key_from_string(current_room)

            msg = decrypt_message(key, msg)
        except Exception as e:
            break

def generate_client_genesis():
    register()
    sleep(1)
    login()
    sleep(1)
    create_room()
    sleep(1)
    join_room()
    sleep(1)
    send_message()

def simulate_client(client_num):
    login()
    sleep(1)
    join_room()
    sleep(1)
    send_message()
    sleep(1)

def generate_clients(num_clients):
    threads = []

    # Criar e iniciar as threads para simular clientes
    for i in range(num_clients):
        thread = threading.Thread(target=simulate_client, args=(i,))
        threads.append(thread)
        thread.start()

    # Espera todas as threads terminarem
    for thread in threads:
        thread.join()

generate_client_genesis()
generate_clients(57)