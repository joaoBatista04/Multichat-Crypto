# Importação das bibliotecas
import socket
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
from dotenv import load_dotenv
import logging

from crypto import *

#Carregando o arquivo .env com as variáveis de ambiente
load_dotenv()

SERVER_IP = os.getenv("SERVER_IP")
SERVER_PORT = int(os.getenv("SERVER_PORT"))

#Configuração do arquivo de log dos clientes
logging.basicConfig(
    filename=os.getenv("CLIENT_LOG"),        # Nome do arquivo de log
    filemode='a',                  # Modo de abertura do arquivo (a para append)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Formato da mensagem de log
    level=logging.ERROR             # Nível de log (INFO ou superior)
)

#Definição inicial de variáveis globais de clientes
current_socket = None
running = False
in_room = False  # Variável para controlar se o usuário já está em uma sala
logged_in = False  # Variável para controlar se o usuário está logado
client_name = ""
current_room = ""

#Conexão com o servidor por meio de socker
def connect_to_server():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((SERVER_IP, SERVER_PORT))

#Envio de comandos ao servidor (sendall) e recebimento de resposta (recv)
def send_command(command):
    """Envia comandos ao servidor central."""
    server_socket.sendall(command.encode())
    return server_socket.recv(1024).decode()

#Registro de novos usuários
def register():
    #Solicita ao usuário um nome e uma senha
    username = simpledialog.askstring("Registro", "Usuário:")
    password = simpledialog.askstring("Registro", "Senha:", show="*")

    #Se o usuário fornecer corretamente, é solicitada a criação de um novo usuário ao servidor, que irá responder
    if username and password:
        response = send_command(f"REGISTER {username} {password}")
        messagebox.showinfo("Registro", response)

#Efetua o login do usuário
def login():
    #Solicita ao usuário um nome e uma senha
    global logged_in, client_name
    username = simpledialog.askstring("Login", "Usuário:")
    password = simpledialog.askstring("Login", "Senha:", show="*")

    #Se o usuário fornecer corretamente, é solicitada o login do usuário ao servidor, que irá responder
    if username and password:
        response = send_command(f"LOGIN {username} {password}")

        #Se o login foi efetuado com sucesso, o sistema informa ao usuário
        if response == "LOGIN_OK":
            logged_in = True
            chat_box.delete("1.0", tk.END)
            chat_box.insert(tk.END, "Escolha alguma sala para entrar ou crie sua própria sala!\n")
            messagebox.showinfo("Login", "Login bem-sucedido!")
            client_name = username
        
        #Se nao, uma mensagem de erro é exibida
        else:
            messagebox.showerror("Erro", response)

#Faz o logout do usuário
def logout():
    global logged_in, in_room, current_socket, running, client_name
    
    #Se o usuário estiver logado, faz outros testes
    if logged_in:
        logged_in = False
        client_name = ""
        
        #Se o usuário está em uma sala no momento do logout, primeiro ele é retirado da sala e a conexão com o socket da sala é encerrado
        if in_room:
            running = False
            current_socket.close()
            current_socket = None
            in_room = False

        #Informa ao usuário que o logout foi efetuado com sucesso
        chat_box.delete("1.0", tk.END)
        chat_box.insert(tk.END, "Você foi deslogado. Faça login novamente para continuar o bate-papo ou registre-se!\n")
        messagebox.showinfo("Deslogar", "Você foi deslogado com sucesso!")
    
    #Se não, avisa ao usuário que ele já não está logado
    else:
        messagebox.showwarning("Atenção", "Você não está logado.")

#Cria uma nova sala
def create_room():
    #Se o usuário não estiver logado, informa o erro
    if not logged_in:
        messagebox.showwarning("Atenção", "Você precisa estar logado para criar uma sala.")
        return
    
    #Se estiver logado, o sistema solicita o nome da nova sala
    room_name = simpledialog.askstring("Criar Sala", "Nome da sala:")
    if room_name:
        response = send_command(f"CREATE {room_name}")

        #Se a sala foi criada corretamente, uma mensagem é exibida
        if(response.startswith("ERRO")):
            messagebox.showerror("Erro na criação da sala", response)
        
        #Se não, uma mensagem de erro é exibida. Provavelmente o erro está no alcance do limite máximo de salas criadas
        else:
            messagebox.showinfo("Resposta", response)

#Entrar em uma sala
def join_room():
    global current_socket, running, in_room, current_room
    
    #Se o usuário não estiver logado, informa o erro
    if not logged_in:
        messagebox.showwarning("Atenção", "Você precisa estar logado para entrar em uma sala.")
        return
    
    #Se o usuário já estiver em uma sala o sistema pedirá para se desconectar da antiga sala primeiro
    if in_room:
        messagebox.showwarning("Atenção", "Você já está em uma sala! Saia primeiro antes de entrar em outra.")
        return
    
    #Solicita a lista de salas disponíveis ao servidor
    response = send_command("LIST_ROOMS")
    salas = response.split("\n") if response else []
    
    #Se não existir nenhuma sala, uma mensagem é exibida convidando o usuário a criar uma
    if len(salas) == 1 and salas[0] == " ":
        messagebox.showinfo("Salas", "Não há salas disponíveis no momento. Sinta-se livre para criar uma!")
        return
    
    #Se existirem, as salas são listadas e o usuário poderá escolher em qual deseja entrar
    room_name = simpledialog.askstring("Entrar na Sala", "Escolha uma sala:\n\n" + "\n".join(salas) + "\n\n" + "Caso não encontre a sala desejada, sinta-se livre para criá-la\n")
    
    #Se a sala escolhida foi digitada corretamente e existe, cria uma conexão do cliente com o socket da sala
    if room_name and room_name in salas:
        response = send_command(f"JOIN {room_name}")
        
        #Se o servidor permitiu a entrada na sala, é criada uma conexão com o socket daquela sala específica, que passa a ser executada em uma thread
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

        #Se a entrada foi recusada pelo servidor, uma mensagem de erro é exibida
        else:
            messagebox.showerror("Erro", response)
    
    #Se o usuário digitou erroneamente o nome da sala ou a sala não existe, uma mensagem de erro é enviada
    else:
        messagebox.showwarning("Salas", "A sala que você selecionou não existe. Sinta-se livre para criá-la!")
        return

#Sair de uma sala
def leave_room():
    global current_socket, running, in_room, current_room

    #Se o usuário não está em uma sala, uma mensagem é exibida
    if in_room == False:
        messagebox.showwarning("Sair da Sala", "Você não está conectado a uma sala!")
        return
    
    #Se está em uma sala, o socket de conexão com aquela sala é encerrado, as variáveis globais são atualizadas e uma mensagem é exibida
    if current_socket:
        running = False
        current_socket.close()
        current_socket = None
        in_room = False
        current_room = ""
        chat_box.delete("1.0", tk.END)
        chat_box.insert(tk.END, "Você saiu da sala. Entre em alguma sala para continuar o bate-papo\n")

#Envia uma mensagem
def send_message():
    try:
        #Se o usuário não estiver logado, informa o erro
        if not logged_in:
            messagebox.showwarning("Atenção", "Você precisa estar logado para enviar mensagens.")
            return

        #Se o usuário não estiver em uma sala, informa o erro
        if not in_room:
            messagebox.showwarning("Atenção", "Você precisa entrar em uma sala para enviar mensagens.")
            return

        global current_socket, current_room
        
        #Se o usuário está conectado corretamente no socket de comunicação com a sala, a mensagem é enviada
        if current_socket:
            #Preparação da mensagem com o nome do cliente e o texto enviado
            msg = message_entry.get("1.0", tk.END).strip()
            msgsend = client_name + ": "
            msgsend += msg + "\n"

            #O nome da sala é utilizado para gerar uma chave de criptografia simétrica
            key = generate_key_from_string(current_room)

            #A mensagem é então criptografada
            msgsend = encrypt_message(key, msgsend)

            #E enviada ao servidor para repasse aos demais clientes daquele sala, bem como inscrição da mensagem na própria tela do usuário que a enviou
            if msg:
                current_socket.sendall(msgsend)
                chat_box.insert(tk.END, f"\nVocê: {msg}\n", "right")
                message_entry.delete("1.0", tk.END)
    
    #Trata a exceção se o servidor recusou a conexão e coloca o tratamento em um log
    except ConnectionRefusedError:
        logging.error("Conexão recusada pelo servidor.")
    #Trata a exceção se a conexão com o servidor apresentou tempo máximo de execução (timeout) e coloca o tratamento em um log
    except socket.timeout:
        logging.error("Tempo de conexão esgotado")
    #Trata uma exceção diversa e coloca o tratamento em um log
    except Exception as e:
        logging.error(f"Exceção: {e}")

#Realiza o recebimento de mensagens
def receive_messages():
    global current_socket, running, current_room
    while running:
        try:
            #A mensagem é recebida pelo socket de comunicação com a sala
            msg = current_socket.recv(1024)
            
            #O nome da sala é utilizado para gerar uma chave de criptografia simétrica.
            key = generate_key_from_string(current_room)
            
            #A mensagem é então descriptografada
            msg = decrypt_message(key, msg)

            #E se ela estiver correta, é inserida na caixa de mensagens do usuário
            if msg:
                chat_box.insert(tk.END, msg + "\n", "left")
        
        #Trata a exceção se o servidor recusou a conexão e coloca o tratamento em um log
        except ConnectionRefusedError:
            logging.error("Conexão recusada pelo servidor.")
            break
        #Trata a exceção se a conexão com o servidor apresentou tempo máximo de execução (timeout) e coloca o tratamento em um log
        except socket.timeout:
            logging.error("Tempo de conexão esgotado")
            break
        #Trata uma exceção diversa e coloca o tratamento em um log
        except Exception as e:
            logging.error(f"Exceção: {e}")
            break

#Cria a interface gráfica do usuário
root = tk.Tk()
root.title("UFES Chat")

#Realiza a conexão com o servidor
connect_to_server()

#Caixa de mensagens
chat_box = tk.Text(root, width=120, height=30)
chat_box.grid(row=0, column=0, columnspan=6, padx=5, pady=5)
chat_box.tag_configure("right", justify="right")
chat_box.tag_configure("left", justify="left")

chat_box.insert(tk.END, "Faça login ou registre-se para utilizar o UFES Chat")

#Campo de entrada da mensagem digitada
message_entry = tk.Text(root, height=5, width=80)
message_entry.grid(row=1, column=0, columnspan=4, padx=5, pady=5)

#Botão de enviar mensagem
send_button = tk.Button(root, text="Enviar", command=send_message, width=20, height=4)
send_button.grid(row=1, column=4, columnspan=2, padx=5, pady=5)

#Botões de ações do usuário (logar, registrar, criar sala, entrar em sala, sair da sala e deslogar)
login_button = tk.Button(root, text="Login", command=login)
login_button.grid(row=2, column=0, padx=5, pady=5)

register_button = tk.Button(root, text="Registrar", command=register)
register_button.grid(row=2, column=1, padx=5, pady=5)

create_button = tk.Button(root, text="Criar Sala", command=create_room)
create_button.grid(row=2, column=2, padx=5, pady=5)

join_button = tk.Button(root, text="Entrar na Sala", command=join_room)
join_button.grid(row=2, column=3, padx=5, pady=5)

leave_button = tk.Button(root, text="Sair da Sala", command=leave_room)
leave_button.grid(row=2, column=4, padx=5, pady=5)

logout_button = tk.Button(root, text="Deslogar", command=logout)
logout_button.grid(row=2, column=5, padx=5, pady=5)

#Loop principal da interface gráfica
root.mainloop()