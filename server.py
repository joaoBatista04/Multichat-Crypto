# Importação das bibliotecas
import socket
import threading
import bcrypt
import pickle
import os
import tkinter as tk
from dotenv import load_dotenv
import logging

#Carregando o arquivo .env com as variáveis de ambiente
load_dotenv()

SERVER_IP = os.getenv("SERVER_IP")
PORT = int(os.getenv("SERVER_PORT"))
USER_DB_FILE = os.getenv("USER_DB_FILE")

#Número máximo de salas permitido
MAX_ROOMS_AMOUNT = 15

#Configuração do arquivo de log do servidor
logging.basicConfig(
    filename=os.getenv("SERVER_LOG"),        
    filemode='a',                  
    format='%(asctime)s - %(levelname)s - %(message)s',  
    level=logging.ERROR             
)

#Definição inicial do conjunto de salas existentes (vazio)
salas = {}

try:
    #Carregar ou criar banco de dados de usuários
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "rb") as f:
            #Carrega os usuários caso o arquivo de usuários já exista
            users = pickle.load(f)
    
    #Se o banco de dados não existe, define a lista de usuários como vazia
    else:
        users = {}

#Trata a exceção caso não seja possível manipular o arquivo de banco de dados
except FileNotFoundError:
    logging.error("Não foi possível manipular o arquivo {USER_DB_FILE}")

#Salva os usuários no banco de dados
def save_users():
    #Realiza a inclusão do usuário no banco de dados
    try:
        with open(USER_DB_FILE, "wb") as f:
            pickle.dump(users, f)
    
    #Trata a exceção caso não seja possível manipular o arquivo de banco de dados
    except FileNotFoundError:
        logging.error("Não foi possível manipular o arquivo {USER_DB_FILE}.")

#Gerencia os comandos dos clientes
def handle_client(client_socket):
    try:
        while True:
            #Recebe comandos advindos dos clientes
            data = client_socket.recv(1024).decode()
            
            #Se houver erro no recebimento, finaliza o loop principal
            if not data:
                break
            
            #Separa os comandos e o payload, isto é, o conteúdo necessário para um determinado comando
            command, *args = data.split()

            #Se o usuário tiver solicitado registro
            if command == "REGISTER":
                username, password = args
                
                #Se o usuário já existir no banco de dados, retorna um erro
                if username in users:
                    client_socket.sendall("ERRO: Usuário já existe.".encode())
                
                #Se não, encripta a senha do usuário, salva seu nome e a senha encriptada no banco de dados e envia uma mensagem de confirmação ao usuário.
                else:
                    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                    users[username] = hashed_pw
                    save_users()
                    client_socket.sendall("Registro bem-sucedido!".encode())

            #Se o usuário tiver solicitado o login
            elif command == "LOGIN":
                username, password = args
                
                #Se o usuário existir no banco de dados, compara a senha fornecida com a senha encriptada do banco de dados para aquele usuário e, em caso de acerto, envia uma mensagem de sucesso
                if username in users and bcrypt.checkpw(password.encode(), users[username]):
                    client_socket.sendall("LOGIN_OK".encode())
                
                #Se não, informa ao cliente que o usuário e/ou a senha foram digitados de forma errada ou o usuário não existe ainda
                else:
                    client_socket.sendall("ERRO: Credenciais inválidas.".encode())

            #Se o comando for criar nova sala
            elif command == "CREATE":
                #Se o número de salas ainda não tiver atingido o valor máximo, cria o socket de comunicação para a nova sala e informa ao cliente.
                if(len(salas) < MAX_ROOMS_AMOUNT):
                    sala = args[0]
                    response = create_room(sala)
                    client_socket.sendall(response.encode())
                
                #Se não, informa ao usuário que o número máximo de salas foi atingido
                else:
                    client_socket.sendall("ERRO: Número máximo de salas atingido.".encode())

            #Se o comando for entrar em uma sala
            elif command == "JOIN":
                sala = args[0]
                
                #Se a sala solicitada existe, envia o usuário a porta do socket de conexão com essa sala
                if sala in salas:
                    sala_port = salas[sala][0].getsockname()[1]
                    response = f"JOIN_OK {sala_port}"

                #Se não, avisa ao usuário que a sala solicitada não existe
                else:
                    response = f"ERRO: Sala '{sala}' não existe."
                client_socket.sendall(response.encode())

            #Se o comando for listar as salas existentes
            elif command == "LIST_ROOMS":
                #Envia o nome das salas existentes ao usuário ou uma string vazia caso não exista nenhuma
                response = "\n".join(salas.keys()) if salas else " "
                client_socket.sendall(response.encode())

    #Trata a exceção de comunicação recusada com o cliente, salva o log e parte para a próxima execução do loop
    except ConnectionRefusedError:
        logging.error("A conexão foi recusada.")
        pass

    #Trata a exceção de tempo de conexão esgotado com o cliente, salva o log e parte para a próxima execução do loop
    except socket.timeout:
        logging.error("Tempo de execução esgotado.")
        pass

    #Trata uma exceção diversa, salva o log e parte para a próxima execução do loop
    except Exception as e:
        logging.error(f"Exceção: {e}")
        pass

    #Se nenhuma tratamento funcionar, então encerra o socket de conexão com aquele cliente
    finally:
        client_socket.close()

#Cria um socket para a nova sala
def create_room(sala):
    try:
        #Se a sala já existe, não faz nada
        if sala in salas:
            return f"Sala '{sala}' já existe."
        
        #Define um socket de comunicação para aquela sala
        sala_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sala_socket.bind(("0.0.0.0", 0))
        sala_socket.listen(5)

        _, sala_port = sala_socket.getsockname()
        salas[sala] = (sala_socket, [])

        #Define a escuta de mensagens no socket daquela sala para uma thread
        threading.Thread(target=listen_room, args=(sala, sala_socket), daemon=True).start()
        return f"Sala '{sala}' criada na porta {sala_port}."
    
    #Trata uma exceção diversa e salva o log
    except Exception as e:
        logging.error(f"Exceção: {e}")

#Escuta as mensagens advindas de uma sala
def listen_room(sala, sala_socket):
    #Fica escutando as conexões dos usuários que desejam entrar naquela sala
    while True:
        #Se um cliente se conecta no socket da sala, define uma thread para escutar as mensagens advindas daquele cliente
        client_socket, addr = sala_socket.accept()
        salas[sala][1].append(client_socket)
        threading.Thread(target=handle_room_client, args=(client_socket, sala), daemon=True).start()

#Escuta as mensagens advindas de um cliente de uma sala
def handle_room_client(client_socket, sala):
    #Fica escutando as mensagens do cliente
    while True:
        try:
            #Recebe a mensagem enviada pelo cliente
            msg = client_socket.recv(1024)
            
            #Se não houver nenhuma mensagem válida, quebra o loop
            if not msg:
                break
            
            #Se a mensagem for válida, a repassa para todos os clientes conectados no socket da sala em que a mensagem foi enviada
            for client in salas[sala][1]:
                if client != client_socket:
                    client.sendall(msg)
        
        #Trata a exceção de comunicação recusada com o cliente, salva o log e quebra o loop principal
        except ConnectionRefusedError:
            logging.error("A conexão foi recusada.")
            break

        #Trata a exceção de tempo de conexão esgotado com o cliente, salva o log e quebra o loop principal
        except socket.timeout:
            logging.error("Tempo de execução esgotado.")
            break

        #Trata uma exceção diversa, salva o log e quebra o loop principal
        except Exception as e:
            logging.error(f"Exceção: {e}")
            break
    
    #Se algum erro acontece e o loop de escuta do cliente é encerrado, o cliente é removido da lista de clientes conectados e sua conexão com o socket da sala é encerrada
    salas[sala][1].remove(client_socket)
    client_socket.close()

#Execução do servidor
def main_server():
    #Realiza a abertura de um socket e fica a espera de clientes para a conexão
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_IP, PORT))
    server_socket.listen(5)
    print(f"Servidor rodando na porta {PORT}...")

    #Fica escutando as conexões dos novos clientes
    while True:
        #Se um novo cliente se conecta com o servidor, é definida uma thread para escutar os comandos vindos desse novo cliente
        client_socket, _ = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

#Execução principal do servidor
if __name__ == "__main__":
    main_server()