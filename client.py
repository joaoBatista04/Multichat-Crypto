import socket
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000
current_socket = None
running = False
in_room = False  # Variável para controlar se o usuário já está em uma sala
logged_in = False  # Variável para controlar se o usuário está logado

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
    global logged_in
    username = simpledialog.askstring("Login", "Usuário:")
    password = simpledialog.askstring("Login", "Senha:", show="*")

    if username and password:
        response = send_command(f"LOGIN {username} {password}")
        if response == "LOGIN_OK":
            logged_in = True
            messagebox.showinfo("Login", "Login bem-sucedido!")
        else:
            messagebox.showerror("Erro", response)

def logout():
    """Desloga o usuário."""
    global logged_in, in_room, current_socket, running
    if logged_in:
        logged_in = False
        if in_room:
            running = False
            current_socket.close()
            current_socket = None
            in_room = False
            chat_box.insert(tk.END, "Você foi deslogado e saiu da sala.\n")
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
    """Entra em uma sala, se o usuário estiver logado."""
    global current_socket, running, in_room
    
    if not logged_in:
        messagebox.showwarning("Atenção", "Você precisa estar logado para entrar em uma sala.")
        return
    
    if in_room:
        messagebox.showwarning("Atenção", "Você já está em uma sala! Saia primeiro antes de entrar em outra.")
        return

    room_name = simpledialog.askstring("Entrar na Sala", "Nome da sala:")
    if room_name:
        response = send_command(f"JOIN {room_name}")
        if response.startswith("JOIN_OK"):
            port = int(response.split()[1])
            current_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            current_socket.connect((SERVER_IP, port))
            running = True
            in_room = True  # Marca que o usuário está em uma sala
            threading.Thread(target=receive_messages, daemon=True).start()
            messagebox.showinfo("Sucesso", f"Entrou na sala '{room_name}'!")
        else:
            messagebox.showerror("Erro", response)

def leave_room():
    """Sai da sala atual e libera o usuário para entrar em outra."""
    global current_socket, running, in_room

    if current_socket:
        running = False
        current_socket.close()
        current_socket = None
        in_room = False  # Agora o usuário pode entrar em outra sala
        chat_box.insert(tk.END, "Você saiu da sala.\n")

def send_message():
    """Envia uma mensagem na sala atual, se o usuário estiver logado."""
    if not logged_in:
        messagebox.showwarning("Atenção", "Você precisa estar logado para enviar mensagens.")
        return

    global current_socket
    if current_socket:
        msg = message_entry.get()
        if msg:
            current_socket.sendall(msg.encode())
            chat_box.insert(tk.END, f"Você: {msg}\n")
            message_entry.delete(0, tk.END)

def receive_messages():
    """Recebe mensagens da sala."""
    global current_socket, running
    while running:
        try:
            msg = current_socket.recv(1024).decode()
            if msg:
                chat_box.insert(tk.END, msg + "\n")
        except:
            break

# Criando interface gráfica
root = tk.Tk()
root.title("Chat Multisala")

connect_to_server()

# Área de mensagens (agora no topo)
chat_box = tk.Text(root, width=50, height=15)
chat_box.grid(row=0, column=0, columnspan=6, padx=5, pady=5)

# Campo de entrada da mensagem (logo abaixo das mensagens)
message_entry = tk.Entry(root, width=40)
message_entry.grid(row=1, column=0, columnspan=4, padx=5, pady=5)

# Botão de enviar mensagem
send_button = tk.Button(root, text="Enviar", command=send_message)
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