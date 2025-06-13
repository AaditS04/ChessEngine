 Python Chess Engine with Pygame GUI 

This project is a fully functional chess game built in Python, featuring a graphical interface powered by **Pygame** and an AI opponent using a **Minimax engine with Alpha-Beta pruning**.

## Features

-  Play as White or Black vs AI or another human
-  AI opponent using **Negamax with Alpha-Beta Pruning**
-  Adjustable depth
-  Undo last move (`Z` key)
- Restart game (`R` key)
- rule support: en passant, castling, pawn promotion
- Sound effects for moves
- piece images rendered on a resizable board

##  AI Logic

The AI is implemented in `ChessAI.py` and uses:
- **Negamax algorithm** (a simplified Minimax)
- **Alpha-beta pruning** to improve search efficiency
- **Material evaluation function**
- Optional randomization to prevent deterministic behavior
- Customizable depth (`DEPTH` variable)

You can increase the search depth in `ChessAI.py`:
```python
DEPTH = 4  # Set to 3 or 4 for stronger AI
