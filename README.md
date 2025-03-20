# Jeu de Pong avec Socket

Ce projet est une implémentation du jeu classique Pong avec une architecture client-serveur utilisant des sockets TCP bruts pour la communication en temps réel. Ce projet a été créé dans un but d'apprentissage sur le modèle OSI et les protocoles socket.

## Structure du Projet

Le projet contient deux implémentations différentes :

### Version WebSocket (Haut niveau)
- `server/` : Serveur Go qui gère la logique du jeu et les connexions WebSocket
  - `pkg/game/` : Logique du jeu (état, mouvements, collisions)
  - `pkg/network/` : Gestion des WebSockets et communication client-serveur
  - `main.go` : Point d'entrée du serveur

- `client/` : Client web pour jouer au jeu
  - `public/` : Fichiers statiques servis par le serveur
    - `js/` : Code JavaScript côté client
    - `index.html` : Page HTML principale
    - `styles.css` : Styles CSS

### Version Socket TCP Brut (Bas niveau)
- `server-tcp/` : Serveur Go implémentant des sockets TCP bruts
  - `pkg/protocol/` : Définitions du protocole de communication binaire personnalisé
  - `pkg/game/` : Logique du jeu (état, mouvements, collisions)
  - `pkg/network/` : Gestion des sockets TCP et communication client-serveur
  - `main.go` : Point d'entrée du serveur

- `client-py/` : Client Python avec Pygame
  - `pong_client.py` : Code source Python du client
  - `requirements.txt` : Dépendances Python

## Fonctionnalités

- Jeu de Pong en temps réel pour deux joueurs
- Communication via sockets TCP bruts avec protocole binaire personnalisé
- Logique de jeu côté serveur pour éviter la triche
- Sérialisation/désérialisation binaire pour une communication efficace

## Technologies Utilisées

### Version WebSocket
- **Serveur** : Go, Gorilla WebSocket
- **Client** : HTML, CSS, JavaScript, Pixi.js

### Version Socket TCP
- **Serveur** : Go avec sockets TCP natifs
- **Client** : Python avec Pygame, sockets TCP natifs

## Comment Jouer

### Version WebSocket
1. Démarrez le serveur :
   ```
   cd server
   go mod tidy  # Pour télécharger les dépendances
   go run main.go
   ```

2. Ouvrez votre navigateur et accédez à `http://localhost:8080`

### Version Socket TCP Brut
1. Compilez et démarrez le serveur :
   ```
   cd server-tcp
   go mod tidy
   go run main.go
   ```

2. Compilez et démarrez le client :
   ```
   cd client-py
   pip install -r requirements.txt
   python pong_client.py
   ```

3. Pour jouer à deux, lancez un second client sur une autre machine ou terminal

4. Utilisez les touches flèche haut et flèche bas pour déplacer votre raquette, et espace pour indiquer que vous êtes prêt

## Architecture de Communication et Modèle OSI

### Version Socket TCP Brut
Cette implémentation utilise des sockets TCP bruts et implémente notre propre protocole de communication binaire, ce qui nous permet de voir directement comment les différentes couches du modèle OSI fonctionnent :

1. **Couche Application** : Logique du jeu Pong
2. **Couche Présentation** : Notre protocole de sérialisation/désérialisation binaire
3. **Couche Session** : Gestion des connexions TCP et des états du client
4. **Couche Transport** : Protocole TCP (fiabilité, contrôle de flux)
5. **Couche Réseau** : Adressage IP
6. **Couches Liaison de données et Physique** : Gérées par le système d'exploitation et le matériel

### Protocole Binaire Personnalisé
Nous avons implémenté notre propre protocole binaire avec les types de messages suivants :
- État du jeu (positions, scores)
- Mouvements des joueurs
- Attribution d'ID de joueur
- État de préparation des joueurs

Chaque message a un en-tête contenant :
- Type de message (1 octet)
- Longueur du message (4 octets, big-endian)

## Développement

Pour modifier le jeu :

- **Version WebSocket** :
  - Serveur : Modifiez les fichiers Go dans `server/`
  - Client : Modifiez les fichiers HTML, CSS et JavaScript dans `client/public/`

- **Version Socket TCP** :
  - Serveur : Modifiez les fichiers Go dans `server-tcp/`
  - Client : Modifiez les fichiers Python dans `client-py/`
