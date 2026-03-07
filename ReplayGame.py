import pygame as p
import json
import time
import os
import sys

# Prevent ChessLogger from creating a new log file during replay
os.environ["CHESS_NO_LOG"] = "1"

# Import game logic and drawing functions from the main app
import ChessEngine
import ChessMain

def get_latest_log_file(log_dir="logs"):
    """Finds the most recently modified JSON log file in the logs directory."""
    if not os.path.exists(log_dir):
        print(f"Error: Log directory '{log_dir}' not found.")
        return None
        
    files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".json")]
    if not files:
        print("Error: No JSON log files found.")
        return None
        
    # Sort files by modification time (newest first)
    files.sort(key=os.path.getmtime, reverse=True)
    
    # Check for the first file that actually has moves
    for file in files:
        try:
            with open(file, "r") as f:
                data = json.load(f)
                if len(data.get("moves", [])) > 0:
                    return file
        except Exception:
            continue
            
    print("Error: No JSON log files with moves found.")
    return None

def replay_game(log_filepath):
    """
    Reads a game log and visually replays the moves.
    """
    print(f"Replaying game from: {log_filepath}")
    
    with open(log_filepath, "r") as f:
        log_data = json.load(f)
        
    moves_to_play = log_data.get("moves", [])
    if not moves_to_play:
        print("No moves found in the log file.")
        return

    # Initialize Pygame and the Game State
    p.init()
    screen = p.display.set_mode((ChessMain.WIDTH, ChessMain.HEIGHT))
    clock = p.time.Clock()
    screen.fill(p.Color("White"))
    
    gs = ChessEngine.GameState()
    validMoves = gs.getValidMoves()
    ChessMain.load_images()
    
    move_index = 0
    total_moves = len(moves_to_play)
    running = True
    game_over = False
    
    # Time between moves (in seconds)
    replay_speed = 1.0 
    last_move_time = time.time()

    print("--- Replay Started ---")
    print(f"Total Moves: {total_moves}")
    print("Press LEFT/RIGHT arrows to change replay speed.")
    print("Close the window to stop.")

    while running:
        for e in p.event.get():
            if e.type == p.QUIT:
                running = False
            elif e.type == p.KEYDOWN:
                if e.key == p.K_RIGHT:
                    replay_speed = max(0.1, replay_speed - 0.2) # Faster
                    print(f"Speed increased: {replay_speed:.1f}s per move")
                elif e.key == p.K_LEFT:
                    replay_speed += 0.2 # Slower
                    print(f"Speed decreased: {replay_speed:.1f}s per move")

        if not game_over and (time.time() - last_move_time) > replay_speed:
            if move_index < total_moves:
                move_data = moves_to_play[move_index]
                uci_move = move_data.get("parsed_move")
                agent = move_data.get("agent")
                quality = move_data.get("move_quality", "N/A")
                
                is_legal = move_data.get("is_legal", True)
                
                if not is_legal:
                    print(f"Move {move_index+1}/{total_moves}: {agent} attempted INVALID move {uci_move} (Skipping...)")
                else:
                    print(f"Move {move_index+1}/{total_moves}: {agent} played {uci_move} [{quality}]")
                    
                    # Find the move object corresponding to the UCI string
                    move_made = False
                    for move in validMoves:
                        if move.getChessNotation() == uci_move:
                            gs.MakeMove(move)
                            move_made = True
                            break
                            
                    if move_made:
                        validMoves = gs.getValidMoves()
                        # Play sound
                        try:
                            ChessMain.sound.play()
                        except Exception:
                            pass # Ignore if sound fails to load
                            
                        # Check for game over
                        if gs.checkMate:
                            game_over = True
                            print("Game Over: Checkmate")
                        elif gs.staleMate:
                            game_over = True
                            print("Game Over: Draw (Stalemate / Repetition)")
                    else:
                        print(f"ERROR: Could not find valid move for {uci_move}")
                        game_over = True # Stop replay if state gets corrupted
                
                move_index += 1
                last_move_time = time.time()
                
            else:
                game_over = True
                print("--- Replay Finished ---")

        # Draw the board using ChessMain functions
        ChessMain.DrawGameState(screen, gs, validMoves, sqSelected=())
        
        if game_over:
            if gs.checkMate:
                if gs.WhiteToMove:
                    ChessMain.drawText(screen, 'Black won by checkmate')
                else:
                    ChessMain.drawText(screen , ' White won by checkmate')
            elif gs.staleMate:
                ChessMain.drawText(screen ,'Game is draw')
            elif move_index >= total_moves:
                ChessMain.drawText(screen, 'Replay Complete')
                
        clock.tick(ChessMain.MAX_FPS)
        p.display.flip()

    p.quit()

if __name__ == "__main__":
    # If a specific file is passed as an argument, use that
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        # Otherwise, find the most recent game
        log_file = get_latest_log_file()
        
    if log_file:
        replay_game(log_file)
