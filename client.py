import socket
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
from dotenv import load_dotenv
import logging

from crypto import *

load_dotenv()

SERVER_IP = os.getenv("SERVER_IP")
SERVER_PORT = int(os.getenv("SERVER_PORT"))

logging.basicConfig(
    filename=os.getenv("CLIENT_LOG_FILE"),        # Nome do arquivo de log
    filemode='a',                  # Modo de abertura do arquivo (a para append)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Formato da mensagem de log
    level=logging.ERROR             # Nível de log (INFO ou superior)
)

current_socket = None
running = False
in_room = False  # Variável para controlar se o usuário já está em uma sala
logged_in = False  # Variável para controlar se o usuário está logado
client_name = ""
current_room = ""

def connect_to_server():
    """Conecta ao servidor central."""
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((SERVER_IP, SERVER_PORT))

def send_command(command):
    """Envia comandos ao servidor central."""
    server_socket.sendall(command.encode())
    return server_socket.recv(1024).decode()

def register():
    """Faz o registro do usuário."""
    username = simpledialog.askstring("Registro", "Usuário:")
    password = simpledialog.askstring("Registro", "Senha:", show="*")

    if username and password:
        response = send_command(f"REGISTER {username} {password}")
        messagebox.showinfo("Registro", response)

def login():
    """Faz o login do usuário."""
    global logged_in, client_name
    username = simpledialog.askstring("Login", "Usuário:")
    password = simpledialog.askstring("Login", "Senha:", show="*")

    if username and password:
        response = send_command(f"LOGIN {username} {password}")
        if response == "LOGIN_OK":
            logged_in = True
            chat_box.delete("1.0", tk.END)
            chat_box.insert(tk.END, "Escolha alguma sala para entrar ou crie sua própria sala!\n")
            messagebox.showinfo("Login", "Login bem-sucedido!")
            client_name = username
        else:
            messagebox.showerror("Erro", response)

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
        chat_box.delete("1.0", tk.END)
        chat_box.insert(tk.END, "Você foi deslogado. Faça login novamente para continuar o bate-papo ou registre-se!\n")
        messagebox.showinfo("Deslogar", "Você foi deslogado com sucesso!")
    else:
        messagebox.showwarning("Atenção", "Você não está logado.")

def create_room():
    """Cria uma nova sala, se o usuário estiver logado."""
    if not logged_in:
        messagebox.showwarning("Atenção", "Você precisa estar logado para criar uma sala.")
        return
    
    room_name = simpledialog.askstring("Criar Sala", "Nome da sala:")
    if room_name:
        response = send_command(f"CREATE {room_name}")
        messagebox.showinfo("Resposta", response)

def join_room():
    """Lista salas disponíveis e permite escolher uma para entrar."""
    global current_socket, running, in_room, current_room
    
    if not logged_in:
        messagebox.showwarning("Atenção", "Você precisa estar logado para entrar em uma sala.")
        return
    
    if in_room:
        messagebox.showwarning("Atenção", "Você já está em uma sala! Saia primeiro antes de entrar em outra.")
        return
    
    response = send_command("LIST_ROOMS")
    salas = response.split("\n") if response else []
    
    if len(salas) == 1 and salas[0] == " ":
        messagebox.showinfo("Salas", "Não há salas disponíveis no momento. Sinta-se livre para criar uma!")
        return
    
    room_name = simpledialog.askstring("Entrar na Sala", "Escolha uma sala:\n\n" + "\n".join(salas) + "\n\n" + "Caso não encontre a sala desejada, sinta-se livre para criá-la\n")
    
    if room_name and room_name in salas:
        response = send_command(f"JOIN {room_name}")
        if response.startswith("JOIN_OK"):
            port = int(response.split()[1])
            current_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            current_socket.connect((SERVER_IP, port))
            running = True
            in_room = True
            current_room = room_name
            threading.Thread(target=receive_messages, daemon=True).start()
            messagebox.showinfo("Sucesso", f"Entrou na sala '{room_name}'!")
            chat_box.delete("1.0", tk.END)
        else:
            messagebox.showerror("Erro", response)
    else:
        messagebox.showwarning("Salas", "A sala que você selecionou não existe. Sinta-se livre para criá-la!")
        return

def leave_room():
    """Sai da sala atual e libera o usuário para entrar em outra."""
    global current_socket, running, in_room, current_room

    if in_room == False:
        messagebox.showwarning("Sair da Sala", "Você não está conectado a uma sala!")
        return
    
    if current_socket:
        running = False
        current_socket.close()
        current_socket = None
        in_room = False  # Agora o usuário pode entrar em outra sala
        current_room = ""
        chat_box.delete("1.0", tk.END)
        chat_box.insert(tk.END, "Você saiu da sala. Entre em alguma sala para continuar o bate-papo\n")

def send_message():
    try:
        if not logged_in:
            messagebox.showwarning("Atenção", "Você precisa estar logado para enviar mensagens.")
            return

        if not in_room:
            messagebox.showwarning("Atenção", "Você precisa entrar em uma sala para enviar mensagens.")
            return

        global current_socket, current_room
        if current_socket:
            msg = message_entry.get("1.0", tk.END).strip()
            msgsend = client_name + ": "
            msgsend += msg + "\n"

            key = generate_key_from_string(current_room)

            msgsend = encrypt_message(key, msgsend)

            if msg:
                current_socket.sendall(msgsend)
                chat_box.insert(tk.END, f"\nVocê: {msg}\n", "right")
                message_entry.delete("1.0", tk.END)
    except ConnectionRefusedError:
        logging.error("Conexão recusada pelo servidor.")
    except socket.timeout:
        logging.error("Tempo de conexão esgotado")
    except Exception as e:
        logging.error(f"Exceção: {e}")

def receive_messages():
    """Recebe mensagens da sala."""
    global current_socket, running, current_room
    while running:
        try:
            msg = current_socket.recv(1024)
            
            key = generate_key_from_string(current_room)

            msg = decrypt_message(key, msg)

            if msg:
                chat_box.insert(tk.END, msg + "\n", "left")
        except ConnectionRefusedError:
            logging.error("Conexão recusada pelo servidor.")
            break
        except socket.timeout:
            logging.error("Tempo de conexão esgotado")
            break
        except Exception as e:
            logging.error(f"Exceção: {e}")
            break

# Criando interface gráfica
root = tk.Tk()
root.title("UFES Chat")

connect_to_server()

# Área de mensagens (agora no topo)
chat_box = tk.Text(root, width=120, height=30)
chat_box.grid(row=0, column=0, columnspan=6, padx=5, pady=5)
chat_box.tag_configure("right", justify="right")
chat_box.tag_configure("left", justify="left")

chat_box.insert(tk.END, "Faça login ou registre-se para utilizar o UFES Chat")

# Campo de entrada da mensagem (logo abaixo das mensagens)
message_entry = tk.Text(root, height=5, width=80)
message_entry.grid(row=1, column=0, columnspan=4, padx=5, pady=5)

# Botão de enviar mensagem
send_button = tk.Button(root, text="Enviar", command=send_message, width=20, height=4)
send_button.grid(row=1, column=4, columnspan=2, padx=5, pady=5)

# Botões organizados em uma única linha
login_button = tk.Button(root, text="Login", command=login)
login_button.grid(row=2, column=0, padx=5, pady=5)

register_button = tk.Button(root, text="Registrar", command=register)
register_button.grid(row=2, column=1, padx=5, pady=5)

create_button = tk.Button(root, text="Criar Sala", command=create_room)
create_button.grid(row=2, column=2, padx=5, pady=5)

join_button = tk.Button(root, text="Entrar Sala", command=join_room)
join_button.grid(row=2, column=3, padx=5, pady=5)

leave_button = tk.Button(root, text="Sair da Sala", command=leave_room)
leave_button.grid(row=2, column=4, padx=5, pady=5)

logout_button = tk.Button(root, text="Deslogar", command=logout)
logout_button.grid(row=2, column=5, padx=5, pady=5)

root.mainloop()