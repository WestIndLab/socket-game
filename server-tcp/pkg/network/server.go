package network

import (
	"fmt"
	"io"
	"log"
	"net"
	"sync"
	"time"

	"pong-game/pkg/game"
	"pong-game/pkg/protocol"
)

// Client représente une connexion client
type Client struct {
	conn     net.Conn
	playerID byte
	server   *Server
}

// Server gère les connexions clients et l'état du jeu
type Server struct {
	game           *game.Game
	clients        map[byte]*Client // Clé: playerID
	listener       net.Listener
	clientsMutex   sync.Mutex
	broadcastChan  chan []byte
	shutdownChan   chan struct{}
	isRunning      bool
}

// NewServer crée un nouveau serveur
func NewServer(address string) *Server {
	return &Server{
		game:          game.NewGame(),
		clients:       make(map[byte]*Client),
		broadcastChan: make(chan []byte, 100),
		shutdownChan:  make(chan struct{}),
		isRunning:     false,
	}
}

// Start démarre le serveur
func (s *Server) Start(address string) error {
	var err error
	s.listener, err = net.Listen("tcp", address)
	if err != nil {
		return fmt.Errorf("erreur lors du démarrage du serveur: %v", err)
	}

	s.isRunning = true

	// Goroutine pour la boucle de jeu
	go s.gameLoop()

	// Goroutine pour la diffusion des états de jeu
	go s.broadcastLoop()

	// Accepter les connexions clients
	log.Printf("Serveur démarré sur %s", address)
	for s.isRunning {
		conn, err := s.listener.Accept()
		if err != nil {
			log.Printf("Erreur lors de l'acceptation de la connexion: %v", err)
			continue
		}

		// Gérer le nouveau client
		go s.handleClient(conn)
	}

	return nil
}

// Stop arrête le serveur
func (s *Server) Stop() {
	s.isRunning = false
	close(s.shutdownChan)
	if s.listener != nil {
		s.listener.Close()
	}
	
	// Fermer toutes les connexions clients
	s.clientsMutex.Lock()
	for _, client := range s.clients {
		client.conn.Close()
	}
	s.clientsMutex.Unlock()
}

// gameLoop met à jour l'état du jeu à intervalles réguliers
func (s *Server) gameLoop() {
	ticker := time.NewTicker(s.game.UpdateRate)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			// Mettre à jour l'état du jeu
			s.game.Update()
			
			// Préparer l'état du jeu à envoyer
			s.broadcastGameState()
		case <-s.shutdownChan:
			return
		}
	}
}

// broadcastLoop envoie les messages en attente aux clients
func (s *Server) broadcastLoop() {
	for {
		select {
		case data := <-s.broadcastChan:
			s.sendToAllClients(data)
		case <-s.shutdownChan:
			return
		}
	}
}

// handleClient gère une connexion client
func (s *Server) handleClient(conn net.Conn) {
	log.Printf("Nouveau client connecté: %s", conn.RemoteAddr())

	// Assigner un ID de joueur
	s.clientsMutex.Lock()
	var playerID byte
	if s.clients[1] == nil {
		playerID = 1
	} else if s.clients[2] == nil {
		playerID = 2
	} else {
		// Trop de joueurs, refuser la connexion
		s.clientsMutex.Unlock()
		conn.Close()
		log.Printf("Connexion refusée, trop de joueurs: %s", conn.RemoteAddr())
		return
	}

	client := &Client{
		conn:     conn,
		playerID: playerID,
		server:   s,
	}
	s.clients[playerID] = client
	s.clientsMutex.Unlock()

	// Envoyer l'ID du joueur au client
	playerJoin := &protocol.PlayerJoin{
		PlayerID: playerID,
	}
	joinMsg := protocol.EncodePlayerJoin(playerJoin)
	conn.Write(joinMsg)

	// Buffer pour lire les messages
	headerBuf := make([]byte, protocol.HeaderSize)
	
	// Boucle de lecture des messages
	for {
		// Lire l'en-tête du message
		_, err := io.ReadFull(conn, headerBuf)
		if err != nil {
			if err == io.EOF {
				log.Printf("Client déconnecté: %s", conn.RemoteAddr())
			} else {
				log.Printf("Erreur de lecture: %v", err)
			}
			break
		}
		
		// Décoder l'en-tête
		header, err := protocol.DecodeHeader(headerBuf)
		if err != nil {
			log.Printf("Erreur de décodage de l'en-tête: %v", err)
			break
		}
		
		// Lire le corps du message
		msgBuf := make([]byte, header.Length)
		_, err = io.ReadFull(conn, msgBuf)
		if err != nil {
			log.Printf("Erreur de lecture du corps du message: %v", err)
			break
		}
		
		// Traiter le message selon son type
		client.handleMessage(header.Type, msgBuf)
	}
	
	// Déconnexion du client
	s.clientsMutex.Lock()
	delete(s.clients, playerID)
	s.clientsMutex.Unlock()
	conn.Close()
	log.Printf("Client %d déconnecté: %s", playerID, conn.RemoteAddr())
}

// handleMessage traite un message reçu d'un client
func (c *Client) handleMessage(msgType byte, data []byte) {
	switch msgType {
	case protocol.MsgTypePlayerMove:
		// Décoder le mouvement
		move, err := protocol.DecodePlayerMove(data)
		if err != nil {
			log.Printf("Erreur de décodage du mouvement: %v", err)
			return
		}
		
		// Vérifier que le joueur contrôle bien sa propre raquette
		if move.PlayerID != c.playerID {
			log.Printf("Tentative de contrôle d'une raquette étrangère")
			return
		}
		
		// Appliquer le mouvement
		c.server.game.MovePaddle(move.PlayerID, move.Direction)
	
	case protocol.MsgTypePlayerReady:
		// Décoder l'état de préparation
		ready, err := protocol.DecodePlayerReady(data)
		if err != nil {
			log.Printf("Erreur de décodage de l'état de préparation: %v", err)
			return
		}
		
		// Vérifier que le joueur contrôle bien son propre état
		if ready.PlayerID != c.playerID {
			log.Printf("Tentative de modification de l'état d'un autre joueur")
			return
		}
		
		// Mettre à jour l'état de préparation
		c.server.game.SetPlayerReady(ready.PlayerID, ready.Ready == 1)
		
		// Diffuser l'état de préparation à tous les clients
		c.server.broadcastPlayerReady(ready)
	}
}

// broadcastGameState envoie l'état actuel du jeu à tous les clients
func (s *Server) broadcastGameState() {
	// Verrouiller pour accéder à l'état du jeu
	s.game.Mu.Lock()
	
	// Créer un message d'état de jeu
	gameState := &protocol.GameState{
		BallX:        s.game.Ball.X,
		BallY:        s.game.Ball.Y,
		Player1Y:     s.game.Player1.Position,
		Player1Score: s.game.Player1.Score,
		Player2Y:     s.game.Player2.Position,
		Player2Score: s.game.Player2.Score,
	}
	
	if s.game.IsRunning {
		gameState.IsRunning = 1
	} else {
		gameState.IsRunning = 0
	}
	
	s.game.Mu.Unlock()
	
	// Encoder et envoyer l'état du jeu
	stateMsg := protocol.EncodeGameState(gameState)
	s.broadcastChan <- stateMsg
}

// broadcastPlayerReady envoie l'état de préparation d'un joueur à tous les clients
func (s *Server) broadcastPlayerReady(ready *protocol.PlayerReady) {
	// Encoder et envoyer l'état de préparation
	readyMsg := protocol.EncodePlayerReady(ready)
	s.broadcastChan <- readyMsg
}

// sendToAllClients envoie un message à tous les clients connectés
func (s *Server) sendToAllClients(data []byte) {
	s.clientsMutex.Lock()
	defer s.clientsMutex.Unlock()
	
	for _, client := range s.clients {
		_, err := client.conn.Write(data)
		if err != nil {
			log.Printf("Erreur d'envoi au client %d: %v", client.playerID, err)
		}
	}
}
