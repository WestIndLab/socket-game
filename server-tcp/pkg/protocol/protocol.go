package protocol

import (
	"bytes"
	"encoding/binary"
	"fmt"
)

// Définition des types de messages
const (
	MsgTypeGameState  byte = 1 // État du jeu envoyé par le serveur
	MsgTypePlayerMove byte = 2 // Mouvement du joueur envoyé par le client
	MsgTypePlayerJoin byte = 3 // Notification de connexion d'un joueur
	MsgTypePlayerReady byte = 4 // Le joueur est prêt
)

// En-tête pour chaque message
// Format:
// - Octet 0: Type de message
// - Octets 1-4: Longueur totale du message (uint32, big-endian)
type MessageHeader struct {
	Type   byte
	Length uint32
}

// Taille de l'en-tête en octets
const HeaderSize = 5

// Encode l'en-tête du message dans un tableau d'octets
func EncodeHeader(msgType byte, length uint32) []byte {
	header := make([]byte, HeaderSize)
	header[0] = msgType
	binary.BigEndian.PutUint32(header[1:], length)
	return header
}

// Décode l'en-tête du message
func DecodeHeader(data []byte) (MessageHeader, error) {
	if len(data) < HeaderSize {
		return MessageHeader{}, fmt.Errorf("données insuffisantes pour décoder l'en-tête")
	}
	
	header := MessageHeader{
		Type:   data[0],
		Length: binary.BigEndian.Uint32(data[1:HeaderSize]),
	}
	
	return header, nil
}

// GameState représente l'état complet du jeu
// Format binaire:
// - Octets 0-3: Position X de la balle (float32)
// - Octets 4-7: Position Y de la balle (float32)
// - Octets 8-11: Position Y du joueur 1 (float32)
// - Octets 12-15: Score du joueur 1 (uint16)
// - Octets 16-19: Position Y du joueur 2 (float32)
// - Octets 20-23: Score du joueur 2 (uint16)
// - Octet 24: 1 si le jeu est en cours, 0 sinon
type GameState struct {
	BallX     float32
	BallY     float32
	Player1Y  float32
	Player1Score uint16
	Player2Y  float32
	Player2Score uint16
	IsRunning byte
}

// Encode un GameState en tableau d'octets
func EncodeGameState(state *GameState) []byte {
	buf := new(bytes.Buffer)
	
	// Écrire chaque champ en binaire
	binary.Write(buf, binary.BigEndian, state.BallX)
	binary.Write(buf, binary.BigEndian, state.BallY)
	binary.Write(buf, binary.BigEndian, state.Player1Y)
	binary.Write(buf, binary.BigEndian, state.Player1Score)
	binary.Write(buf, binary.BigEndian, state.Player2Y)
	binary.Write(buf, binary.BigEndian, state.Player2Score)
	binary.Write(buf, binary.BigEndian, state.IsRunning)
	
	data := buf.Bytes()
	
	// Créer le message complet avec l'en-tête
	message := append(EncodeHeader(MsgTypeGameState, uint32(len(data))), data...)
	
	return message
}

// Décode un tableau d'octets en GameState
func DecodeGameState(data []byte) (*GameState, error) {
	if len(data) < 25 { // Taille minimale du GameState
		return nil, fmt.Errorf("données insuffisantes pour décoder GameState")
	}
	
	state := &GameState{}
	buf := bytes.NewReader(data)
	
	// Lire chaque champ
	binary.Read(buf, binary.BigEndian, &state.BallX)
	binary.Read(buf, binary.BigEndian, &state.BallY)
	binary.Read(buf, binary.BigEndian, &state.Player1Y)
	binary.Read(buf, binary.BigEndian, &state.Player1Score)
	binary.Read(buf, binary.BigEndian, &state.Player2Y)
	binary.Read(buf, binary.BigEndian, &state.Player2Score)
	binary.Read(buf, binary.BigEndian, &state.IsRunning)
	
	return state, nil
}

// PlayerMove représente un mouvement de joueur
// Format binaire:
// - Octet 0: ID du joueur (1 ou 2)
// - Octet 1: Direction (1 pour bas, -1 pour haut, 0 pour arrêt)
type PlayerMove struct {
	PlayerID byte
	Direction int8
}

func EncodePlayerMove(move *PlayerMove) []byte {
	buf := new(bytes.Buffer)
	
	binary.Write(buf, binary.BigEndian, move.PlayerID)
	binary.Write(buf, binary.BigEndian, move.Direction)
	
	data := buf.Bytes()
	
	// Créer le message complet avec l'en-tête
	message := append(EncodeHeader(MsgTypePlayerMove, uint32(len(data))), data...)
	
	return message
}

// Décode un tableau d'octets en PlayerMove
func DecodePlayerMove(data []byte) (*PlayerMove, error) {
	if len(data) < 2 {
		return nil, fmt.Errorf("données insuffisantes pour décoder PlayerMove")
	}
	
	move := &PlayerMove{}
	buf := bytes.NewReader(data)
	
	binary.Read(buf, binary.BigEndian, &move.PlayerID)
	binary.Read(buf, binary.BigEndian, &move.Direction)
	
	return move, nil
}

// PlayerJoin représente l'attribution d'un ID de joueur
// Format binaire:
// - Octet 0: ID du joueur (1 ou 2)
type PlayerJoin struct {
	PlayerID byte
}

// Encode un PlayerJoin en tableau d'octets
func EncodePlayerJoin(join *PlayerJoin) []byte {
	buf := new(bytes.Buffer)
	
	binary.Write(buf, binary.BigEndian, join.PlayerID)
	
	data := buf.Bytes()
	
	// Créer le message complet avec l'en-tête
	message := append(EncodeHeader(MsgTypePlayerJoin, uint32(len(data))), data...)
	
	return message
}

// Décode un tableau d'octets en PlayerJoin
func DecodePlayerJoin(data []byte) (*PlayerJoin, error) {
	if len(data) < 1 {
		return nil, fmt.Errorf("données insuffisantes pour décoder PlayerJoin")
	}
	
	join := &PlayerJoin{}
	buf := bytes.NewReader(data)
	
	binary.Read(buf, binary.BigEndian, &join.PlayerID)
	
	return join, nil
}

// PlayerReady représente l'état de préparation d'un joueur
// Format binaire:
// - Octet 0: ID du joueur (1 ou 2)
// - Octet 1: 1 si prêt, 0 sinon
type PlayerReady struct {
	PlayerID byte
	Ready    byte
}

// Encode un PlayerReady en tableau d'octets
func EncodePlayerReady(ready *PlayerReady) []byte {
	buf := new(bytes.Buffer)
	
	binary.Write(buf, binary.BigEndian, ready.PlayerID)
	binary.Write(buf, binary.BigEndian, ready.Ready)
	
	data := buf.Bytes()
	
	// Créer le message complet avec l'en-tête
	message := append(EncodeHeader(MsgTypePlayerReady, uint32(len(data))), data...)
	
	return message
}

// Décode un tableau d'octets en PlayerReady
func DecodePlayerReady(data []byte) (*PlayerReady, error) {
	if len(data) < 2 {
		return nil, fmt.Errorf("données insuffisantes pour décoder PlayerReady")
	}
	
	ready := &PlayerReady{}
	buf := bytes.NewReader(data)
	
	binary.Read(buf, binary.BigEndian, &ready.PlayerID)
	binary.Read(buf, binary.BigEndian, &ready.Ready)
	
	return ready, nil
}
