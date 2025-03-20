// TCP Proxy Server pour le client web Pong
const express = require('express');
const cors = require('cors');
const net = require('net');
const bodyParser = require('body-parser');

const app = express();
const PORT = 8081;

// Middleware
app.use(cors());
app.use(bodyParser.json());

// Connexion TCP
let tcpSocket = null;
let buffer = Buffer.alloc(0);
let messageQueue = [];

// Fonction pour lire les messages complets du buffer
function processBuffer() {
    console.log(`Traitement du buffer: ${buffer.length} octets disponibles`);
    
    while (buffer.length >= 5) {
        // Lire l'en-tête
        const msgType = buffer[0];
        const msgLength = buffer.readUInt32BE(1);
        
        console.log(`Message détecté - Type: ${msgType}, Longueur: ${msgLength}`);
        
        // Vérifier si le message complet est disponible
        if (buffer.length < 5 + msgLength) {
            console.log(`Message incomplet, en attente de plus de données (${buffer.length}/${5 + msgLength} octets)`);
            break;
        }
        
        // Extraire le message complet
        const message = Buffer.concat([
            buffer.slice(0, 5 + msgLength)
        ]);
        
        // Ajouter à la file d'attente
        messageQueue.push(message.toString('base64'));
        console.log(`Message ajouté à la file d'attente. Type: ${msgType}, Queue length: ${messageQueue.length}`);
        
        // Supprimer le message du buffer
        buffer = buffer.slice(5 + msgLength);
    }
}

// Route pour établir une connexion TCP
app.post('/tcp-proxy/connect', (req, res) => {
    const { host, port } = req.body;
    
    if (!host || !port) {
        return res.status(400).json({
            success: false,
            message: 'Host et port sont requis'
        });
    }
    
    try {
        if (tcpSocket) {
            tcpSocket.destroy();
        }
        
        tcpSocket = new net.Socket();
        buffer = Buffer.alloc(0);
        messageQueue = [];
        
        // Configure les gestionnaires d'événements AVANT de tenter la connexion
        tcpSocket.on('data', (data) => {
            console.log(`Données reçues du serveur: ${data.length} octets`);
            buffer = Buffer.concat([buffer, data]);
            processBuffer();
        });
        
        tcpSocket.on('error', (error) => {
            console.error('Erreur de socket:', error.message);
            tcpSocket = null;
        });
        
        tcpSocket.on('close', () => {
            console.log('Connexion fermée');
            tcpSocket = null;
        });
        
        // Connecter au serveur
        tcpSocket.connect(parseInt(port), host, () => {
            console.log(`Connecté à ${host}:${port}`);
            
            // Attendre un peu pour donner le temps au serveur d'envoyer le message PlayerJoin
            setTimeout(() => {
                return res.json({
                    success: true,
                    message: `Connecté à ${host}:${port}`
                });
            }, 500); // Attendre 500ms
        });
    } catch (error) {
        console.error('Erreur de connexion:', error.message);
        
        return res.status(500).json({
            success: false,
            message: error.message
        });
    }
});

// Route pour envoyer des données au serveur TCP
app.post('/tcp-proxy/send', (req, res) => {
    const { data } = req.body;
    
    if (!tcpSocket) {
        return res.status(400).json({
            success: false,
            message: 'Non connecté'
        });
    }
    
    if (!data) {
        return res.status(400).json({
            success: false,
            message: 'Données requises'
        });
    }
    
    try {
        const buffer = Buffer.from(data, 'base64');
        tcpSocket.write(buffer);
        
        return res.json({
            success: true,
            message: 'Données envoyées'
        });
    } catch (error) {
        return res.status(500).json({
            success: false,
            message: error.message
        });
    }
});

// Route pour recevoir des données du serveur TCP
app.get('/tcp-proxy/receive', (req, res) => {
    if (!tcpSocket) {
        return res.status(400).json({
            success: false,
            message: 'Non connecté'
        });
    }
    
    // Prendre le message le plus ancien de la file d'attente
    const message = messageQueue.shift();
    
    // Répondre avec succès même s'il n'y a pas de message
    return res.json({
        success: true,
        data: message || null  // Retourne null au lieu de undefined quand il n'y a pas de message
    });
});

// Démarrer le serveur
app.listen(PORT, () => {
    console.log(`Serveur proxy TCP démarré sur le port ${PORT}`);
});
