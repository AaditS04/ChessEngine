import pygame as p
import ChessEngine
import ChessAI
import ChessMain
import time

def evaluate_personas():
    p.init()
    # Initialize screen for visualizing the board states
    screen = p.display.set_mode((ChessMain.WIDTH, ChessMain.HEIGHT))
    ChessMain.load_images()
    
    # Configure custom logging file for evaluations
    eval_log_name = f"evaluation_{int(time.time())}.json"
    ChessAI.logger.set_log_file(eval_log_name)
    
    import PersonaCatalogue
    import csv
    import os
    import copy
    import random
    
    tests = []
    if os.path.exists("fen_analysis.csv"):
        with open("fen_analysis.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            all_rows = list(reader)
            
            sample_size = min(100, len(all_rows))
            sampled_rows = random.sample(all_rows, sample_size)
            
            for row in sampled_rows:
                tests.append({
                    "name": "",
                    "description": "",
                    "fen": row["FEN"]
                })
    else:
        print("fen_analysis.csv not found!")
    
    def calculate_attack_score(gs_original, move):
        if not move: return 0
        score = 0
        
        piece_values = {'p': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 100}
        our_val = piece_values.get(move.pieceMoved[1], 0)
        
        # 1. King Proximity
        enemy_king_loc = gs_original.blackKingLocation if gs_original.WhiteToMove else gs_original.whiteKingLocation
        dist = max(abs(move.endRow - enemy_king_loc[0]), abs(move.endCol - enemy_king_loc[1]))
        score += max(0, 7 - dist)
        
        # 2. Enemy Territory Invasion
        if gs_original.WhiteToMove:
            if move.endRow <= 3: score += 3
        else:
            if move.endRow >= 4: score += 3
                
        # Simulate move
        gs = copy.deepcopy(gs_original)
        gs.MakeMove(move)
        
        # Analyze opponent responses
        opponent_moves = gs.getAllPossibleMoves()
        is_attacked_by_any = False
        min_attacker_val = 999
        
        for m in opponent_moves:
            if m.endRow == move.endRow and m.endCol == move.endCol:
                is_attacked_by_any = True
                opp_val = piece_values.get(m.pieceMoved[1], 0)
                if opp_val < min_attacker_val:
                    min_attacker_val = opp_val
                    
        is_attacked_by_lower = is_attacked_by_any and (min_attacker_val < our_val)

        # 3. Capture Bonus (Only if not recapturable by a lower value piece)
        if move.pieceCaptured != '--':
            if not is_attacked_by_lower:
                score += 4
            
        # 4. Safe Threats (Attacking smartly)
        # Check if we defend our newly placed piece
        original_piece = gs.board[move.endRow][move.endCol]
        enemy_color = 'b' if original_piece[0] == 'w' else 'w'
        gs.board[move.endRow][move.endCol] = enemy_color + 'p'
        gs.WhiteToMove = not gs.WhiteToMove
        our_moves = gs.getAllPossibleMoves()
        is_defended = any(m.endRow == move.endRow and m.endCol == move.endCol for m in our_moves)
        gs.WhiteToMove = not gs.WhiteToMove
        gs.board[move.endRow][move.endCol] = original_piece
        
        is_safe = False
        if is_defended:
            if not is_attacked_by_lower:
                is_safe = True
        else:
            if not is_attacked_by_any:
                is_safe = True
                
        # 5. Check Bonus (Only if the checking piece is completely safe!)
        if gs.inCheck():
            if is_safe:
                score += 6
        
        # Check if we are actively attacking an enemy piece (excluding the King) from this safe square
        attacks_enemy = False
        gs.WhiteToMove = not gs.WhiteToMove # Swap to our perspective
        our_moves_from_sq = gs.getAllPossibleMoves()
        gs.WhiteToMove = not gs.WhiteToMove
        
        for m in our_moves_from_sq:
            # Check if this move originates from our new piece and captures an enemy piece
            if m.startRow == move.endRow and m.startCol == move.endCol and m.pieceCaptured != '--':
                # Ignore the King to prevent double counting with the Check Bonus
                if m.pieceCaptured[1] != 'K':
                    attacks_enemy = True
                    break
                
        if attacks_enemy and is_safe:
            score += 5
            
        return score

    def calculate_defensive_score(gs_original, move):
        if not move: return 0
        score = 0
        
        # 1. Simulate the move
        gs = copy.deepcopy(gs_original)
        gs.MakeMove(move)
        
        # Identify who just moved to evaluate their defense
        our_color = 'b' if gs_original.WhiteToMove else 'w'
        our_king_loc = gs.blackKingLocation if our_color == 'b' else gs.whiteKingLocation
        
        # --- Metric 1: King Proximity (Pawn Shield & Defenders) ---
        defenders_near_king = 0
        for r in range(max(0, our_king_loc[0]-2), min(8, our_king_loc[0]+3)):
            for c in range(max(0, our_king_loc[1]-2), min(8, our_king_loc[1]+3)):
                piece = gs.board[r][c]
                if piece != '--' and piece[0] == our_color and piece[1] != 'K':
                    defenders_near_king += 1
                    # Bonus for pawns directly shielding the king
                    if piece[1] == 'p' and abs(r - our_king_loc[0]) == 1:
                        score += 3
        
        score += defenders_near_king * 2
        
        # --- Metric 2: Avoiding Undefended/Hanging Pieces ---
        # Temporarily switch perspective to see our own attacks (defenses)
        gs.WhiteToMove = not gs.WhiteToMove
        our_moves = gs.getAllPossibleMoves()
        gs.WhiteToMove = not gs.WhiteToMove
        
        defended_squares = set((m.endRow, m.endCol) for m in our_moves)
        
        hanging_pieces = 0
        for r in range(8):
            for c in range(8):
                piece = gs.board[r][c]
                if piece != '--' and piece[0] == our_color and piece[1] != 'K':
                    if (r, c) not in defended_squares:
                        hanging_pieces += 1
                        
        # Penalize for hanging pieces. A solid defensive player shouldn't have any.
        score -= hanging_pieces * 4
        
        # --- Metric 3: Safe Retreats / Solid Placement ---
        # Did the move take us further away from enemy territory?
        # A higher row value implies staying closer to the 1st rank for White, or 8th for Black
        distance_from_base = move.endRow if our_color == 'w' else (7 - move.endRow)
        
        # Reward dropping back or staying compact (ranks 1-4)
        if distance_from_base >= 4: # e.g. Row 4,5,6,7 for White (ranks 4,3,2,1)
             score += 2
             
        # Big bonus if we moved a piece out of an attacked square to a safe square
        gs_copy = copy.deepcopy(gs_original)
        opponent_moves_before = gs_copy.getAllPossibleMoves()
        was_attacked = any(m.endRow == move.startRow and m.endCol == move.startCol for m in opponent_moves_before)
        
        if was_attacked:
            # Check if destination is safe
            opponent_moves_after = gs.getAllPossibleMoves()
            is_attacked_now = any(m.endRow == move.endRow and m.endCol == move.endCol for m in opponent_moves_after)
            if not is_attacked_now:
                score += 5 # Successfully rescued a piece

        return score

    evaluation_results = []

    for test in tests:
        print(f"\n{'='*60}")
        print(f"--- Running Test: {test['name']} ---")
        print(f"Description: {test['description']}")
        print(f"FEN: {test['fen']}")
        print(f"{'='*60}")
        
        # Load the custom board state for visualization
        gs = ChessEngine.GameState()
        gs.loadFEN(test['fen'])
        validMoves = gs.getValidMoves()
        
        # Draw board initially so you can see the puzzle
        ChessMain.DrawGameState(screen, gs, validMoves, ())
        p.display.flip()
        pygame_events = p.event.get() # flush events so window doesn't freeze
        
        print("\nBoard loaded on screen! Giving you 2 seconds to look at it...")
        time.sleep(2)
        
        for p_key, active_persona in PersonaCatalogue.PERSONAS.items():
            persona_name = active_persona["name"]
            persona_prompt = active_persona["prompt"]
            
            print(f"\nEvaluating Persona: {persona_name}...")
            
            # Reload fresh game state for each persona
            gs = ChessEngine.GameState()
            gs.loadFEN(test['fen'])
            validMoves = gs.getValidMoves()

            # --- SELECT YOUR LLM HERE ---
            # aimove = ChessAI.LLMsMove(gs, validMoves, persona_prompt=persona_prompt, persona_name=persona_name, description=test['description']) # Gemini
            # aimove = ChessAI.OLlama(gs, validMoves, persona_prompt=persona_prompt, persona_name=persona_name, description=test['description']) # Ollama
            aimove = ChessAI.OpenRouterMove(gs, validMoves, persona_prompt=persona_prompt, persona_name=persona_name, description=test['description'])
            
            # Extract log entry for this persona from the global logger
            log_entry = None
            for entry in reversed(ChessAI.logger.data["moves"]):
                if entry["agent"] == persona_name:
                    log_entry = entry
                    break

            attack_score = calculate_attack_score(gs, aimove) if aimove else 0
            defensive_score = calculate_defensive_score(gs, aimove) if aimove else 0
            print(f"    [Metrics] Aggressive Score: {attack_score} | Defensive Score: {defensive_score}")
            
            if log_entry:
                log_entry["attack_score"] = attack_score
                log_entry["defensive_score"] = defensive_score
                ChessAI.logger._save()

            if aimove:
                print(f">>> FINAL VERDICT: {persona_name} chose {aimove.getSAN(validMoves)} <<<")
                
                # Show the move on the screen quickly
                gs.MakeMove(aimove)
                ChessMain.DrawGameState(screen, gs, gs.getValidMoves(), ())
                p.display.flip()
                p.event.get()
                time.sleep(2)
            else:
                print(f"AI ({persona_name}) failed to return a legal move.")
            
            if log_entry:
                evaluation_results.append({
                    "Test Name": test["name"],
                    "FEN": test["fen"],
                    "Model": "OpenRouter (liquid/lfm-2.5-1.2b-thinking:free)",
                    "Persona": persona_name,
                    "Raw Response": log_entry.get("raw_response", ""),
                    "LLM Move": log_entry.get("parsed_move", ""),
                    "Best Move": log_entry.get("best_move", ""),
                    "Score Diff": log_entry.get("score_diff", ""),
                    "Quality": log_entry.get("move_quality", ""),
                    "Is Legal": log_entry.get("is_legal", False),
                    "Attack Metric": attack_score,
                    "Defensive Metric": defensive_score
                })
                
        print("\nFinished all personas for this test. Waiting 3 seconds before next test...")
        time.sleep(3)
            
    csv_path = os.path.join("logs", f"persona_evaluation_results_{int(time.time())}.csv")
    if not os.path.exists("logs"):
        os.makedirs("logs")
        
    if evaluation_results:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=evaluation_results[0].keys())
            writer.writeheader()
            writer.writerows(evaluation_results)
        print(f"\n--- Evaluation Complete! Detailed report saved to {csv_path} ---")
    else:
        print("\n--- Evaluation Complete! No results logged. ---")
    p.quit()

if __name__ == "__main__":
    evaluate_personas()
