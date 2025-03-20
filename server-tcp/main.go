package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"pong-game/pkg/network"
)

func main() {
	// Configurer l'adresse du serveur
	address := "127.0.0.1:9090" // Adresse par défaut
	if port := os.Getenv("PORT"); port != "" {
		address = ":" + port
	}

	// Créer et démarrer le serveur
	server := network.NewServer(address)
	
	// Canal pour les signaux d'arrêt
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	
	// Démarrer le serveur dans une goroutine
	errChan := make(chan error)
	go func() {
		errChan <- server.Start(address)
	}()
	
	// Attendre un signal d'arrêt ou une erreur
	select {
	case err := <-errChan:
		log.Fatalf("Erreur du serveur: %v", err)
	case sig := <-sigChan:
		log.Printf("Signal reçu: %v, arrêt du serveur...", sig)
		server.Stop()
	}
}
