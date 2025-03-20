#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import pygame
import sys
import struct
import threading
import time

# Configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9090

# Constantes du jeu
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PADDLE_WIDTH = 10
PADDLE_HEIGHT = 100
BALL_SIZE = 10
BLACK = (0, 0, 33)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)

# Types de messages (doivent correspondre à ceux du serveur)
MSG_TYPE_GAME_STATE = 1
MSG_TYPE_PLAYER_JOIN = 2
MSG_TYPE_PLAYER_MOVE = 3
MSG_TYPE_PLAYER_READY = 4

class PongClient:
    def __init__(self):
        # Initialisation de pygame
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Pong Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        
        # État du jeu
        self.game_state = {
            "player1_y": SCREEN_HEIGHT // 2 - PADDLE_HEIGHT // 2,
            "player2_y": SCREEN_HEIGHT // 2 - PADDLE_HEIGHT // 2,
            "ball_x": SCREEN_WIDTH // 2,
            "ball_y": SCREEN_HEIGHT // 2,
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
            print(f"Connecté au serveur {SERVER_HOST}:{SERVER_PORT}")
        except Exception as e:
            print(f"Erreur de connexion: {e}")
            self.connected = False
    
    def receive_loop(self):
        """Boucle de réception des messages du serveur"""
        while self.running and self.connected:
            try:
                # Lire l'en-tête (5 octets)
                header = self.sock.recv(5)
                if not header or len(header) < 5:
                    print("Connexion fermée par le serveur")
                    self.connected = False
                    break
                
                # Analyser l'en-tête
                msg_type = header[0]
                msg_length = struct.unpack(">I", header[1:5])[0]
                
                # Lire le contenu du message
                payload = self.sock.recv(msg_length)
                if len(payload) < msg_length:
                    print("Message incomplet reçu")
                    continue
                
                # Traiter le message selon son type
                if msg_type == MSG_TYPE_GAME_STATE:
                    self.handle_game_state(payload)
                elif msg_type == MSG_TYPE_PLAYER_JOIN:
                    self.handle_player_join(payload)
                elif msg_type == MSG_TYPE_PLAYER_READY:
                    self.handle_player_ready(payload)
            
            except Exception as e:
                print(f"Erreur dans la boucle de réception: {e}")
                self.connected = False
                break
    
    def handle_game_state(self, payload):
        """Traite un message d'état du jeu"""
        if len(payload) >= 18:
            self.game_state["player1_y"] = struct.unpack(">f", payload[0:4])[0]
            self.game_state["player2_y"] = struct.unpack(">f", payload[4:8])[0]
            self.game_state["ball_x"] = struct.unpack(">f", payload[8:12])[0]
            self.game_state["ball_y"] = struct.unpack(">f", payload[12:16])[0]
            self.game_state["player1_score"] = payload[16]
            self.game_state["player2_score"] = payload[17]
            
            # Si les deux joueurs sont prêts, le jeu est considéré comme démarré
            if self.player1_ready and self.player2_ready:
                self.game_started = True
    
    def handle_player_join(self, payload):
        """Traite un message d'attribution d'ID de joueur"""
        if len(payload) >= 1:
            self.player_id = payload[0]
            print(f"Vous êtes le joueur {self.player_id}")
    
    def handle_player_ready(self, payload):
        """Traite un message d'état de préparation d'un joueur"""
        if len(payload) >= 2:
            player_id = payload[0]
            is_ready = payload[1] == 1
            
            if player_id == 1:
                self.player1_ready = is_ready
                print(f"Joueur 1 est {'prêt' if is_ready else 'pas prêt'}")
            elif player_id == 2:
                self.player2_ready = is_ready
                print(f"Joueur 2 est {'prêt' if is_ready else 'pas prêt'}")
    
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
            print(f"Erreur d'envoi de mouvement: {e}")
    
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
        except Exception as e:
            print(f"Erreur d'envoi d'état de préparation: {e}")
    
    def render_waiting_screen(self):
        """Affiche l'écran d'attente"""
        # Fond
        self.screen.fill(BLACK)
        
        # Afficher l'ID du joueur
        if self.player_id > 0:
            player_text = self.font.render(f"Vous êtes le Joueur {self.player_id}", True, YELLOW)
            self.screen.blit(player_text, (SCREEN_WIDTH // 2 - player_text.get_width() // 2, 100))
        else:
            connecting_text = self.font.render("Connexion au serveur...", True, WHITE)
            self.screen.blit(connecting_text, (SCREEN_WIDTH // 2 - connecting_text.get_width() // 2, 100))
        
        # Afficher l'état des joueurs
        p1_status = "Prêt" if self.player1_ready else "En attente"
        p2_status = "Prêt" if self.player2_ready else "En attente"
        
        p1_text = self.font.render(f"Joueur 1: {p1_status}", True, GREEN if self.player1_ready else RED)
        p2_text = self.font.render(f"Joueur 2: {p2_status}", True, GREEN if self.player2_ready else RED)
        
        self.screen.blit(p1_text, (SCREEN_WIDTH // 4 - p1_text.get_width() // 2, 200))
        self.screen.blit(p2_text, (3 * SCREEN_WIDTH // 4 - p2_text.get_width() // 2, 200))
        
        # Instructions
        if self.player_id > 0:
            ready_text = self.font.render("Appuyez sur ESPACE pour être prêt", True, WHITE)
            self.screen.blit(ready_text, (SCREEN_WIDTH // 2 - ready_text.get_width() // 2, 350))
        
        control_text = self.font.render("Utilisez les flèches HAUT et BAS pour déplacer votre raquette", True, WHITE)
        self.screen.blit(control_text, (SCREEN_WIDTH // 2 - control_text.get_width() // 2, 400))
    
    def render_game(self):
        """Affiche l'état du jeu"""
        # Fond
        self.screen.fill(BLACK)
        
        # Ligne centrale
        for y in range(0, SCREEN_HEIGHT, 20):
            pygame.draw.rect(self.screen, WHITE, (SCREEN_WIDTH // 2 - 1, y, 2, 10))
        
        # Raquettes
        pygame.draw.rect(
            self.screen, WHITE,
            (0, self.game_state["player1_y"], PADDLE_WIDTH, PADDLE_HEIGHT)
        )
        pygame.draw.rect(
            self.screen, WHITE,
            (SCREEN_WIDTH - PADDLE_WIDTH, self.game_state["player2_y"], PADDLE_WIDTH, PADDLE_HEIGHT)
        )
        
        # Balle
        pygame.draw.rect(
            self.screen, YELLOW,
            (self.game_state["ball_x"] - BALL_SIZE // 2, self.game_state["ball_y"] - BALL_SIZE // 2, BALL_SIZE, BALL_SIZE)
        )
        
        # Score
        score_text = self.font.render(
            f"{self.game_state['player1_score']} - {self.game_state['player2_score']}", 
            True, WHITE
        )
        self.screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 20))
    
    def main_loop(self):
        """Boucle principale du jeu"""
        ready_toggle = False  # Pour éviter les changements rapides d'état
        
        while self.running:
            # Gestion des événements
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    
                    # Changer l'état de préparation
                    if event.key == pygame.K_SPACE and not self.game_started and not ready_toggle:
                        if self.player_id == 1:
                            ready_toggle = True
                            self.send_player_ready(not self.player1_ready)
                        elif self.player_id == 2:
                            ready_toggle = True
                            self.send_player_ready(not self.player2_ready)
                
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_SPACE:
                        ready_toggle = False
            
            # Gestion des mouvements (touches maintenues)
            keys = pygame.key.get_pressed()
            
            if self.connected and (self.game_started or (self.player_id == 1 and self.player1_ready) or (self.player_id == 2 and self.player2_ready)):
                if keys[pygame.K_UP]:
                    self.send_player_move(-1)  # Vers le haut
                elif keys[pygame.K_DOWN]:
                    self.send_player_move(1)   # Vers le bas
                else:
                    self.send_player_move(0)   # Arrêt
            
            # Affichage
            if not self.game_started:
                self.render_waiting_screen()
            else:
                self.render_game()
            
            # Mise à jour de l'écran
            pygame.display.flip()
            self.clock.tick(60)  # 60 FPS
        
        # Nettoyage
        if self.connected:
            self.sock.close()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    PongClient()
