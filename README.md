# XO Game: Man-in-the-Middle Simulation

A networked Tic-Tac-Toe game demonstrating **Man-in-the-Middle (MITM)** attacks and **error detection/correction algorithms**.

---

## Overview

This project simulates a real-world network scenario where a malicious intermediary can:
- Intercept and modify game moves
- Inject errors into chat messages
- Demonstrate how error detection algorithms catch tampering

```
┌─────────────┐         ┌─────────────────────┐         ┌─────────────┐
│  Player X   │ ◄─────► │    MITM Server      │ ◄─────► │  Player O   │
│  (Client)   │   TCP   │  (Interceptor)      │   TCP   │  (Client)   │
└─────────────┘         └─────────────────────┘         └─────────────┘
```

---

## Features

### Game Features
- **Two-player networked Tic-Tac-Toe**
- **Real-time turn-based gameplay**
- **Rematch voting system** - both players must agree
- **Surrender option** - forfeit the game
- **Modern dark-themed GUI**

### MITM Server Capabilities
- **Intercept moves** - Hold and inspect before forwarding
- **Modify positions** - Change where a move is placed
- **Inject chat errors** - Flip bits in messages
- **Game control** - Force restart or end games

### Error Detection Algorithms
| Algorithm | Type | Description |
|-----------|------|-------------|
| **Parity** | Detection | Adds 1 bit per 8 data bits |
| **CRC** | Detection | Cyclic redundancy check (3-bit) |
| **Hamming(7,4)** | Correction | Can fix single-bit errors |
| **Checksum** | Detection | Sum-based verification |

---

## How It Works

### 1. Connection Flow
```
1. Server starts, listens on port 5000
2. Client 1 connects → assigned 'X'
3. Client 2 connects → assigned 'O'
4. Server broadcasts "game_start"
5. Game begins with X's turn
```

### 2. Move Flow
```
1. Player clicks cell
2. Move sent to server (with encoding)
3. Server holds move for inspection
4. Operator chooses: Pass / Flip / Random
5. Move forwarded to opponent
6. Board updates, turn switches
```

### 3. Chat Flow
```
1. Sender types message
2. Sender selects encoding method (Parity/CRC/Hamming)
3. Message encoded with control information
4. Server can inject errors (flip bits)
5. Receiver decodes and compares:
   - Received control info
   - Calculated control info
6. Mismatch = Error detected!
```

### 4. Restart Flow
```
1. Game ends (win/draw/surrender)
2. Player clicks "Rematch"
3. Opponent receives notification
4. If both vote → New game starts
```

---

## Project Structure

```
project/
├── server.py         # MITM Server with control panel
├── client.py         # Game client with chat
├── algorithms.py     # Error detection implementations
├── README.md         # This file

```

---

## Technical Details

### Network Protocol
- **Transport**: TCP (reliable, ordered)
- **Format**: JSON messages
- **Port**: 5000 (configurable)

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `assign` | S→C | Assigns X or O to client |
| `game_start` | S→C | Game begins, includes current turn |
| `move` | C→S | Player's move with position |
| `move_made` | S→C | Forwarded move (may be modified) |
| `turn` | S→C | Indicates whose turn |
| `round_over` | S→C | Game ended with winner |
| `chat` | C→S | Chat message with encoding |
| `chat_msg` | S→C | Forwarded chat (may have errors) |
| `vote_restart` | C→S | Player wants rematch |
| `surrender` | C→S | Player forfeits |

### Encoding Example

For message "Hi" using CRC:
```
Text:     "Hi"
Binary:   0100100001101001 (16 bits)
CRC:      010 (3 bits)
Sent:     0100100001101001010

If server flips bit 5:
Received: 0100000001101001010
Receiver calculates CRC: 011
Received CRC: 010
Mismatch → Error detected!
```

---

## Running the Project

### Requirements
- Python 3.8+
- Tkinter (included with Python)

### Start Server
```bash
python server.py
```

### Start Clients (2 terminals)
```bash
python client.py
python client.py
```

---

## Server Controls

### Game Tab
| Button | Action |
|--------|--------|
| ✓ Pass | Forward move unchanged |
| ⟲ Flip | Change position to different cell |
| ⊕ Random | Random empty cell |
| Restart | Force new game |
| End | Terminate game |

### Chat Tab
| Button | Action |
|--------|--------|
| ✓ Pass | Forward message unchanged |
| ⟲ Flip 1 Bit | Flip single random bit |
| ⟲ Multi Flip | Flip 2-3 random bits |

---

## Error Detection Comparison

When the server injects an error:

| Method | Detection | Correction | Result |
|--------|-----------|------------|--------|
| Parity | 1 bit | ❌ | Shows mismatch |
| CRC | Multiple | ❌ | Shows mismatch |
| Hamming | 1-2 bits | 1 bit | May correct |
| Checksum | Multiple | ❌ | Shows mismatch |

---

## Use Cases

1. **Educational** - Learn about network security
2. **Demonstration** - Show MITM attack concepts
3. **Testing** - Verify error detection algorithms
4. **Data Communication** - Understand encoding/decoding

---

## Technologies Used

- **Python** - Core language
- **Tkinter** - GUI framework
- **Socket** - TCP networking
- **JSON** - Message serialization
- **Threading** - Concurrent client handling

---

**Data Communication Project**
