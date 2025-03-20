#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import struct
import threading
import time
import os
import sys

# Configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9090

# Types de messages (doivent correspondre à ceux du serveur)
MSG_TYPE_GAME_STATE = 1
MSG_TYPE_PLAYER_JOIN = 2
MSG_TYPE_PLAYER_MOVE = 3
MSG_TYPE_PLAYER_READY = 4

class PongClient:
    def __init__(self):
        # État du jeu
        self.state = {
            "player1_y": 250,
            "player2_y": 250,
            "ball_x": 400,
            "ball_y": 300,
            "player1_score": 0,
            "player2_score": 0,
        }
        
        # État du client
        self.player_id = 0
        self.player1_ready = False
        self.player2_ready = False
        self.game_started = False
        self.connected = False
        self.running = True
        self.message = "Initialisation..."
        
        # Connexion au serveur
        self.connect_to_server()
        
        # Démarrer la boucle de réception
        self.receive_thread = threading.Thread(target=self.receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        # Boucle principale du jeu
        self.main_loop()
    
    def connect_to_server(self):
        """Établit la connexion avec le serveur"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            self.connected = True
            self.message = f"Connecté au serveur {SERVER_HOST}:{SERVER_PORT}"
        except Exception as e:
            self.connected = False
            self.message = f"Erreur de connexion: {e}"
    
    def receive_loop(self):
        """Boucle de réception des messages du serveur"""
        while self.running and self.connected:
            try:
                # Lire l'en-tête (5 octets)
                header = self.sock.recv(5)
                if not header or len(header) < 5:
                    self.connected = False
                    self.message = "Connexion fermée par le serveur"
                    break
                
                # Analyser l'en-tête
                msg_type = header[0]
                msg_length = struct.unpack(">I", header[1:5])[0]
                
                # Lire le contenu du message
                payload = self.sock.recv(msg_length)
                if len(payload) < msg_length:
                    self.message = "Message incomplet reçu"
                    continue
                
                # Traiter le message selon son type
                if msg_type == MSG_TYPE_GAME_STATE:
                    self.handle_game_state(payload)
                elif msg_type == MSG_TYPE_PLAYER_JOIN:
                    self.handle_player_join(payload)
                elif msg_type == MSG_TYPE_PLAYER_READY:
                    self.handle_player_ready(payload)
            
            except Exception as e:
                self.connected = False
                self.message = f"Erreur dans la boucle de réception: {e}"
                break
    
    def handle_game_state(self, payload):
        """Traite un message d'état du jeu"""
        if len(payload) >= 18:
            self.state["player1_y"] = int(struct.unpack(">f", payload[0:4])[0])
            self.state["player2_y"] = int(struct.unpack(">f", payload[4:8])[0])
            self.state["ball_x"] = int(struct.unpack(">f", payload[8:12])[0])
            self.state["ball_y"] = int(struct.unpack(">f", payload[12:16])[0])
            self.state["player1_score"] = payload[16]
            self.state["player2_score"] = payload[17]
            
            # Si les deux joueurs sont prêts, le jeu est considéré comme démarré
            if self.player1_ready and self.player2_ready:
                self.game_started = True
    
    def handle_player_join(self, payload):
        """Traite un message d'attribution d'ID de joueur"""
        if len(payload) >= 1:
            self.player_id = payload[0]
            self.message = f"Vous êtes le joueur {self.player_id}"
    
    def handle_player_ready(self, payload):
        """Traite un message d'état de préparation d'un joueur"""
        if len(payload) >= 2:
            player_id = payload[0]
            is_ready = payload[1] == 1
            
            if player_id == 1:
                self.player1_ready = is_ready
                self.message = f"Joueur 1 est {'prêt' if is_ready else 'pas prêt'}"
            elif player_id == 2:
                self.player2_ready = is_ready
                self.message = f"Joueur 2 est {'prêt' if is_ready else 'pas prêt'}"
    
    def send_player_move(self, direction):
        """Envoie un message de mouvement du joueur"""
        if not self.connected or self.player_id == 0:
            return
        
        try:
            # Créer le message
            payload = struct.pack(">Bb", self.player_id, direction)
            
            # Ajouter l'en-tête
            header = struct.pack(">BI", MSG_TYPE_PLAYER_MOVE, len(payload))
            
            # Envoyer le message complet
            self.sock.sendall(header + payload)
        except Exception as e:
            self.message = f"Erreur d'envoi de mouvement: {e}"
    
    def send_player_ready(self, is_ready):
        """Envoie un message d'état de préparation du joueur"""
        if not self.connected or self.player_id == 0:
            return
        
        try:
            # Créer le message
            payload = struct.pack(">BB", self.player_id, 1 if is_ready else 0)
            
            # Ajouter l'en-tête
            header = struct.pack(">BI", MSG_TYPE_PLAYER_READY, len(payload))
            
            # Envoyer le message complet
            self.sock.sendall(header + payload)
            
            # Mettre à jour l'état local
            if self.player_id == 1:
                self.player1_ready = is_ready
            elif self.player_id == 2:
                self.player2_ready = is_ready
            
            self.message = f"Vous êtes {'prêt' if is_ready else 'pas prêt'}"
        except Exception as e:
            self.message = f"Erreur d'envoi d'état de préparation: {e}"
    
    def clear_screen(self):
        """Efface l'écran de la console"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_waiting_screen(self):
        """Affiche l'écran d'attente"""
        self.clear_screen()
        
        print("======================================")
        print("           PONG MULTIJOUEUR           ")
        print("======================================")
        print()
        
        if not self.connected:
            print("Non connecté au serveur")
            print(self.message)
            return
        
        if self.player_id > 0:
            print(f"Vous êtes le Joueur {self.player_id}")
        else:
            print("En attente d'attribution d'un ID de joueur...")
        
        print()
        print(f"Joueur 1: {'[PRÊT]' if self.player1_ready else '[PAS PRÊT]'}")
        print(f"Joueur 2: {'[PRÊT]' if self.player2_ready else '[PAS PRÊT]'}")
        print()
        
        if self.player_id > 0:
            print("Appuyez sur R pour être prêt")
            print("Utilisez les touches A (haut) et Z (bas) pour déplacer votre raquette")
            print("Appuyez sur Q pour quitter")
        
        print()
        print("Message: " + self.message)
    
    def display_game_status(self):
        """Affiche une représentation textuelle simplifiée du jeu"""
        self.clear_screen()
        
        print("======================================")
        print(f"    SCORE: {self.state['player1_score']} - {self.state['player2_score']}    ")
        print("======================================")
        print()
        print("Positions:")
        print(f"Raquette Joueur 1: y={self.state['player1_y']}")
        print(f"Raquette Joueur 2: y={self.state['player2_y']}")
        print(f"Balle: x={self.state['ball_x']}, y={self.state['ball_y']}")
        print()
        print("Contrôles:")
        print("A: Déplacer vers le haut")
        print("Z: Déplacer vers le bas")
        print("Q: Quitter")
        print()
        print("Message: " + self.message)
    
    def main_loop(self):
        """Boucle principale du jeu"""
        try:
            while self.running:
                # Afficher l'interface
                if not self.game_started:
                    self.print_waiting_screen()
                else:
                    self.display_game_status()
                
                # Lire une touche (non-bloquant)
                command = input("Commande > ")
                
                if command.lower() == 'q':
                    self.running = False
                
                elif command.lower() == 'r' and not self.game_started:
                    # Changer l'état de préparation
                    if self.player_id == 1:
                        self.send_player_ready(not self.player1_ready)
                    elif self.player_id == 2:
                        self.send_player_ready(not self.player2_ready)
                
                elif command.lower() == 'a':
                    self.send_player_move(-1)  # Vers le haut
                
                elif command.lower() == 'z':
                    self.send_player_move(1)   # Vers le bas
                
                # Pause pour éviter une utilisation excessive du CPU
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            # Gestion propre de Ctrl+C
            self.running = False
        
        finally:
            # Nettoyage
            if self.connected:
                self.sock.close()
            print("\nAu revoir !")

if __name__ == "__main__":
    PongClient()
