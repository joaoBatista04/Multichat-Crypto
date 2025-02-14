import unittest
import socket
import threading
import time
from server import create_room, handle_client, save_users, handle_room_client

HOST = "127.0.0.1"
PORT = 5000

class TestChatServer(unittest.TestCase):
    def test_create_room(self):
        """Testa se uma sala pode ser criada corretamente."""
        response = create_room("sala_teste")
        self.assertIn("Sala 'sala_teste' criada", response)
    
    def test_register_and_login(self):
        """Testa o registro e login de usuários."""
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST, PORT))
        
        client.sendall(b"REGISTER usuario_teste senha123")
        response = client.recv(1024).decode()
        self.assertEqual(response, "Registro bem-sucedido!")
        
        client.sendall(b"LOGIN usuario_teste senha123")
        response = client.recv(1024).decode()
        self.assertEqual(response, "LOGIN_OK")
        
        client.close()
    
    def test_join_nonexistent_room(self):
        """Testa se um usuário recebe erro ao tentar entrar em uma sala inexistente."""
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST, PORT))
        
        client.sendall(b"JOIN sala_inexistente")
        response = client.recv(1024).decode()
        self.assertIn("ERRO: Sala", response)
        
        client.close()
    
if __name__ == "__main__":
    unittest.main()