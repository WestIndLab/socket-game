#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import struct
import threading
import time
import curses
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
            "player1_y": 10,
            "player2_y": 10,
            "ball_x": 40,
            "ball_y": 12,
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
        
        # Initialiser curses
        self.setup_curses()
        
        try:
            # Boucle principale du jeu
            self.main_loop()
        finally:
            # Nettoyage de curses
            curses.endwin()
            # Fermeture du socket
            if self.connected:
                self.sock.close()
    
    def setup_curses(self):
        """Initialise l'interface texte avec curses"""
        self.stdscr = curses.initscr()
        curses.cbreak()
        curses.noecho()
        self.stdscr.keypad(True)
        self.stdscr.timeout(100)  # Délai d'attente pour getch en ms
        curses.curs_set(0)  # Masquer le curseur
        
        # Vérifier la taille du terminal
        self.height, self.width = self.stdscr.getmaxyx()
        if self.height < 24 or self.width < 80:
            curses.endwin()
            print("Fenêtre de terminal trop petite. Redimensionnez-la (min 80x24).")
            sys.exit(1)
    
    def connect_to_server(self):
        """Établit la connexion avec le serveur"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            self.connected = True
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
            elif player_id == 2:
                self.player2_ready = is_ready
    
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
        except Exception as e:
            self.message = f"Erreur d'envoi d'état de préparation: {e}"
    
    def draw_waiting_screen(self):
        """Affiche l'écran d'attente"""
        self.stdscr.clear()
        
        # Bordure
        self.stdscr.border()
        
        # Titre
        title = "PONG - Mode Multijoueur"
        self.stdscr.addstr(1, (self.width - len(title)) // 2, title)
        
        # Statut de connexion
        if not self.connected:
            status = "Non connecté au serveur"
            self.stdscr.addstr(3, (self.width - len(status)) // 2, status, curses.A_BOLD)
            if hasattr(self, 'message'):
                self.stdscr.addstr(4, (self.width - len(self.message)) // 2, self.message)
            return
        
        # ID du joueur
        if self.player_id > 0:
            player_text = f"Vous êtes le Joueur {self.player_id}"
            self.stdscr.addstr(3, (self.width - len(player_text)) // 2, player_text)
        
        # État des joueurs
        p1_status = "Prêt" if self.player1_ready else "En attente"
        p2_status = "Prêt" if self.player2_ready else "En attente"
        
        self.stdscr.addstr(5, 20, f"Joueur 1: {p1_status}")
        self.stdscr.addstr(5, self.width - 30, f"Joueur 2: {p2_status}")
        
        # Instructions
        if self.player_id > 0:
            self.stdscr.addstr(10, (self.width - 36) // 2, "Appuyez sur ESPACE pour être prêt")
        
        self.stdscr.addstr(12, (self.width - 55) // 2, "Utilisez les flèches HAUT et BAS pour déplacer votre raquette")
        
        # Messages système
        if hasattr(self, 'message'):
            self.stdscr.addstr(self.height - 2, 2, self.message)
    
    def draw_game(self):
        """Affiche l'état du jeu"""
        self.stdscr.clear()
        
        # Bordure
        self.stdscr.border()
        
        # Terrain de jeu (utiliser des coordonnées proportionnelles)
        game_width = self.width - 4
        game_height = self.height - 4
        
        # Ligne centrale
        for y in range(2, self.height - 2, 2):
            self.stdscr.addch(y, self.width // 2, '|')
        
        # Score
        score_text = f"{self.state['player1_score']} - {self.state['player2_score']}"
        self.stdscr.addstr(1, (self.width - len(score_text)) // 2, score_text)
        
        # Calculer les positions à l'échelle
        # Proportions originales: terrain 800x600, raquettes 10x100
        scale_x = game_width / 800
        scale_y = game_height / 600
        
        p1_x = 2
        p1_y = int(2 + self.state["player1_y"] * scale_y)
        p1_height = int(100 * scale_y)
        
        p2_x = self.width - 3
        p2_y = int(2 + self.state["player2_y"] * scale_y)
        p2_height = int(100 * scale_y)
        
        ball_x = int(2 + self.state["ball_x"] * scale_x)
        ball_y = int(2 + self.state["ball_y"] * scale_y)
        
        # Dessiner les raquettes
        for i in range(p1_height):
            if 2 <= p1_y + i < self.height - 2:
                self.stdscr.addch(p1_y + i, p1_x, '#')
        
        for i in range(p2_height):
            if 2 <= p2_y + i < self.height - 2:
                self.stdscr.addch(p2_y + i, p2_x, '#')
        
        # Dessiner la balle
        if 2 <= ball_y < self.height - 2 and 2 <= ball_x < self.width - 2:
            self.stdscr.addch(ball_y, ball_x, 'O')
        
        # Instructions
        instr = "Utilisez flèches HAUT/BAS pour déplacer votre raquette, Q pour quitter"
        self.stdscr.addstr(self.height - 1, (self.width - len(instr)) // 2, instr)
    
    def main_loop(self):
        """Boucle principale du jeu"""
        last_ready_toggle = time.time() - 1  # Pour éviter les changements rapides d'état
        
        while self.running:
            # Affichage
            if not self.game_started:
                self.draw_waiting_screen()
            else:
                self.draw_game()
            
            # Rafraîchir l'écran
            self.stdscr.refresh()
            
            # Gestion des touches
            try:
                key = self.stdscr.getch()
                
                if key == ord('q') or key == ord('Q'):
                    self.running = False
                
                elif key == ord(' '):
                    # Changer l'état de préparation (avec un délai minimum)
                    now = time.time()
                    if now - last_ready_toggle > 0.5 and not self.game_started:
                        if self.player_id in (1, 2):
                            is_ready = not (self.player1_ready if self.player_id == 1 else self.player2_ready)
                            self.send_player_ready(is_ready)
                            last_ready_toggle = now
                
                elif key == curses.KEY_UP:
                    self.send_player_move(-1)  # Vers le haut
                
                elif key == curses.KEY_DOWN:
                    self.send_player_move(1)   # Vers le bas
                
                elif key == -1:  # Aucune touche pressée
                    # Si aucune flèche n'est pressée, envoyer un arrêt
                    if self.connected and self.game_started:
                        self.send_player_move(0)
            
            except Exception as e:
                self.message = f"Erreur dans la boucle principale: {e}"
                time.sleep(0.1)  # Éviter de consommer trop de CPU en cas d'erreur

if __name__ == "__main__":
    PongClient()
