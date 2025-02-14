import socket
import threading
import bcrypt
import pickle
import os
import tkinter as tk
from dotenv import load_dotenv
import logging

load_dotenv()

SERVER_IP = os.getenv("SERVER_IP")
PORT = int(os.getenv("SERVER_PORT"))
USER_DB_FILE = os.getenv("USER_DB_FILE")
MAX_ROOMS_AMOUNT = 15

logging.basicConfig(
    filename=os.getenv("SERVER_LOG"),        # Nome do arquivo de log
    filemode='a',                  # Modo de abertura do arquivo (a para append)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Formato da mensagem de log
    level=logging.ERROR             # Nível de log (INFO ou superior)
)

salas = {}

try:
    # Carregar ou criar banco de dados de usuários
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "rb") as f:
            users = pickle.load(f)
    else:
        users = {}
except FileNotFoundError:
    logging.error("Não foi possível manipular o arquivo {USER_DB_FILE}")

def save_users():
    """Salva usuários no banco de dados."""
    try:
        with open(USER_DB_FILE, "wb") as f:
            pickle.dump(users, f)
    except FileNotFoundError:
        logging.error("Não foi possível manipular o arquivo {USER_DB_FILE}.")

def handle_client(client_socket):
    """Gerencia comandos de login e registro."""
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break

            command, *args = data.split()

            if command == "REGISTER":
                username, password = args
                if username in users:
                    client_socket.sendall("ERRO: Usuário já existe.".encode())
                else:
                    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                    users[username] = hashed_pw
                    save_users()
                    client_socket.sendall("Registro bem-sucedido!".encode())

            elif command == "LOGIN":
                username, password = args
                if username in users and bcrypt.checkpw(password.encode(), users[username]):
                    client_socket.sendall("LOGIN_OK".encode())
                else:
                    client_socket.sendall("ERRO: Credenciais inválidas.".encode())

            elif command == "CREATE":
                if(len(salas) < MAX_ROOMS_AMOUNT):
                    sala = args[0]
                    response = create_room(sala)
                    client_socket.sendall(response.encode())
                else:
                    client_socket.sendall("ERRO: Número máximo de salas atingido.".encode())

            elif command == "JOIN":
                sala = args[0]
                if sala in salas:
                    sala_port = salas[sala][0].getsockname()[1]
                    response = f"JOIN_OK {sala_port}"
                else:
                    response = f"ERRO: Sala '{sala}' não existe."
                client_socket.sendall(response.encode())

            elif command == "LIST_ROOMS":
                response = "\n".join(salas.keys()) if salas else " "
                client_socket.sendall(response.encode())

    except ConnectionResetError:
        logging.error("A conexão foi recusada.")
        pass
    except socket.timeout:
        logging.error("Tempo de execução esgotado.")
        pass
    except Exception as e:
        logging.error(f"Exceção: {e}")
        pass
    finally:
        client_socket.close()

def create_room(sala):
    """Cria um socket para a sala."""
    try:
        if sala in salas:
            return f"Sala '{sala}' já existe."

        sala_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sala_socket.bind(("0.0.0.0", 0))
        sala_socket.listen(5)

        _, sala_port = sala_socket.getsockname()
        salas[sala] = (sala_socket, [])

        threading.Thread(target=listen_room, args=(sala, sala_socket), daemon=True).start()
        return f"Sala '{sala}' criada na porta {sala_port}."
    except Exception as e:
        logging.error(f"Exceção: {e}")

def listen_room(sala, sala_socket):
    """Gerencia conexões de clientes na sala."""
    while True:
        client_socket, addr = sala_socket.accept()
        salas[sala][1].append(client_socket)
        threading.Thread(target=handle_room_client, args=(client_socket, sala), daemon=True).start()

def handle_room_client(client_socket, sala):
    while True:
        try:
            msg = client_socket.recv(1024)
            if not msg:
                break

            for client in salas[sala][1]:
                if client != client_socket:
                    client.sendall(msg)
        except ConnectionResetError:
            logging.error("A conexão foi recusada.")
            break
        except socket.timeout:
            logging.error("Tempo de execução esgotado.")
            break
        except Exception as e:
            logging.error(f"Exceção: {e}")
            break

    salas[sala][1].remove(client_socket)
    client_socket.close()

def main_server():
    """Servidor central."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_IP, PORT))
    server_socket.listen(5)
    print(f"Servidor rodando na porta {PORT}...")

    while True:
        client_socket, _ = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == "__main__":
    main_server()