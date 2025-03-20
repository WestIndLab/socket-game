package game

import (
	"math"
	"math/rand"
	"sync"
	"time"
)

const (
	// Dimensions du jeu
	GameWidth  = 800
	GameHeight = 600

	// Dimensions de la raquette
	PaddleWidth  = 15
	PaddleHeight = 100

	// Dimensions de la balle
	BallSize = 10

	// Vitesse
	BallSpeed       = 5.0
	PaddleSpeed     = 8.0
	UpdateFrequency = 60 // FPS
)

// Ball représente la balle
type Ball struct {
	X         float32
	Y         float32
	VelocityX float32
	VelocityY float32
}

// Player représente un joueur et sa raquette
type Player struct {
	Position float32
	Score    uint16
	Ready    bool
}

// Game représente l'état complet du jeu
type Game struct {
	Ball       Ball
	Player1    Player
	Player2    Player
	IsRunning  bool
	UpdateRate time.Duration
	Mu         sync.Mutex // Rendu public pour y accéder depuis le package network
}

// NewGame crée une nouvelle instance de jeu
func NewGame() *Game {
	return &Game{
		Ball: Ball{
			X: GameWidth / 2,
			Y: GameHeight / 2,
		},
		Player1: Player{
			Position: GameHeight/2 - PaddleHeight/2,
			Score:    0,
			Ready:    false,
		},
		Player2: Player{
			Position: GameHeight/2 - PaddleHeight/2,
			Score:    0,
			Ready:    false,
		},
		IsRunning:  false,
		UpdateRate: time.Second / UpdateFrequency,
	}
}

// ResetBall replace la balle au centre avec une vélocité aléatoire
func (g *Game) ResetBall() {
	g.Mu.Lock()
	defer g.Mu.Unlock()

	g.Ball.X = GameWidth / 2
	g.Ball.Y = GameHeight / 2

	// Angle de départ aléatoire entre -π/4 et π/4 (ou π-π/4 et π+π/4 pour partir vers la gauche)
	var angle float64
	if rand.Float64() > 0.5 {
		angle = rand.Float64()*math.Pi/2 - math.Pi/4
	} else {
		angle = rand.Float64()*math.Pi/2 - math.Pi/4 + math.Pi
	}

	g.Ball.VelocityX = float32(BallSpeed * math.Cos(angle))
	g.Ball.VelocityY = float32(BallSpeed * math.Sin(angle))
}

// Start démarre le jeu
func (g *Game) Start() {
	g.Mu.Lock()
	defer g.Mu.Unlock()
	
	// Réinitialiser les scores
	g.Player1.Score = 0
	g.Player2.Score = 0
	g.ResetBall()
	g.IsRunning = true
}

// MovePaddle déplace la raquette d'un joueur
func (g *Game) MovePaddle(playerID byte, direction int8) {
	g.Mu.Lock()
	defer g.Mu.Unlock()

	var player *Player
	if playerID == 1 {
		player = &g.Player1
	} else if playerID == 2 {
		player = &g.Player2
	} else {
		return
	}

	// Direction: 1 pour bas, -1 pour haut
	movement := float32(direction) * PaddleSpeed
	newPosition := player.Position + movement

	// Garder la raquette dans les limites du jeu
	if newPosition < 0 {
		newPosition = 0
	} else if newPosition > GameHeight-PaddleHeight {
		newPosition = GameHeight - PaddleHeight
	}

	player.Position = newPosition
}

// SetPlayerReady définit l'état de préparation d'un joueur
func (g *Game) SetPlayerReady(playerID byte, ready bool) {
	g.Mu.Lock()
	defer g.Mu.Unlock()

	if playerID == 1 {
		g.Player1.Ready = ready
	} else if playerID == 2 {
		g.Player2.Ready = ready
	}

	// Si les deux joueurs sont prêts, démarrer le jeu
	if g.Player1.Ready && g.Player2.Ready && !g.IsRunning {
		g.Start()
	}
}

// Update met à jour l'état du jeu pour un cycle
func (g *Game) Update() {
	g.Mu.Lock()
	defer g.Mu.Unlock()

	if !g.IsRunning {
		return
	}

	// Mettre à jour la position de la balle
	g.Ball.X += g.Ball.VelocityX
	g.Ball.Y += g.Ball.VelocityY

	// Collision avec les murs (haut/bas)
	if g.Ball.Y <= 0 || g.Ball.Y >= GameHeight-BallSize {
		g.Ball.VelocityY = -g.Ball.VelocityY
	}

	// Collision avec les raquettes
	// Raquette gauche (Player 1)
	if g.Ball.X <= PaddleWidth && g.Ball.Y+BallSize >= g.Player1.Position && g.Ball.Y <= g.Player1.Position+PaddleHeight {
		// Calculer la position relative de collision sur la raquette (de -0.5 à 0.5)
		relativeIntersection := (g.Player1.Position + PaddleHeight/2 - g.Ball.Y) / (PaddleHeight / 2)
		// Calculer l'angle en fonction de la position d'impact
		bounceAngle := float64(relativeIntersection) * math.Pi / 4 // -π/4 à π/4

		g.Ball.VelocityX = float32(BallSpeed * math.Cos(bounceAngle))
		g.Ball.VelocityY = float32(-BallSpeed * math.Sin(bounceAngle))
	}

	// Raquette droite (Player 2)
	if g.Ball.X >= GameWidth-PaddleWidth-BallSize && g.Ball.Y+BallSize >= g.Player2.Position && g.Ball.Y <= g.Player2.Position+PaddleHeight {
		// Calculer la position relative de collision sur la raquette (de -0.5 à 0.5)
		relativeIntersection := (g.Player2.Position + PaddleHeight/2 - g.Ball.Y) / (PaddleHeight / 2)
		// Calculer l'angle en fonction de la position d'impact
		bounceAngle := float64(relativeIntersection) * math.Pi / 4 // -π/4 à π/4

		g.Ball.VelocityX = float32(-BallSpeed * math.Cos(bounceAngle))
		g.Ball.VelocityY = float32(-BallSpeed * math.Sin(bounceAngle))
	}

	// Vérifier si un joueur a marqué
	if g.Ball.X <= 0 {
		// Player 2 marque
		g.Player2.Score++
		g.ResetBall()
	} else if g.Ball.X >= GameWidth {
		// Player 1 marque
		g.Player1.Score++
		g.ResetBall()
	}
}

// Initialise le générateur de nombres aléatoires
func init() {
	rand.Seed(time.Now().UnixNano())
}
