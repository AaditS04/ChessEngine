import random
from google import genai
from google.genai import errors
import pygame 
import os
import json
import ollama
from openai import OpenAI
import time
import re
import ChessLogger
import copy

# Initialize Logger
logger = ChessLogger.ChessLogger()

client = genai.Client(api_key="")



pieceScore = {"K": 0, "Q": 9, "R": 5, "N": 3, "B": 3, "p": 1}
CHECKMATE = 10000
STALEMATE = 0
DEPTH = 4  # You can increase this as needed



def scoreMove(gs, move):
    gs_copy = copy.deepcopy(gs)
    gs_copy.MakeMove(move)
    turnMultiplier = 1 if gs_copy.WhiteToMove else -1
    # Use same depth as engine
    score = -negamaxAlphaBeta(gs_copy, DEPTH - 1, -CHECKMATE, CHECKMATE, turnMultiplier)
    return score

def LLMsMove(gs,validMoves, persona_prompt="You are a Grandmaster Level Chess Engine. Play solid, positional chess. 1. Prioritize King Safety. 2. Capture free (hanging) pieces. 3. Avoid blundering your own pieces. Output ONLY the best move in UCI format (e.g., e2e4).", persona_name="Gemini"):
    currValidMoves = [move.getChessNotation() for move in validMoves]
    turn = "White" if gs.WhiteToMove else "Black"
    FEN = gs.getFEN()
    print(f"DEBUG - FEN sent to AI: {FEN}")

    piece_case = "UPPERCASE" if turn == "White" else "lowercase"
    enemy_case = "lowercase" if turn == "White" else "UPPERCASE"
    direction = "up the board (rank 2 to 8)" if turn == "White" else "down the board (rank 7 to 1)"

    prompt_text = f"""
    Current Board Position (FEN): {FEN}
    Active Side: {turn}
    Legal Moves: {", ".join(currValidMoves)}

    You are playing as {turn}. 
    - Your pieces are {piece_case} letters. The enemy's are {enemy_case}.
    - Your pawns move {direction}.
    Analyze the position and select the best move from the Legal Moves list.
    Return ONLY the move in UCI format. No explanation.
    """
    response = client.models.generate_content(
    model="gemini-2.0-flash-lite",
    contents=prompt_text,    config={
        "system_instruction": persona_prompt,
        "temperature": 0.1 
    })
    
    raw_response = response.text.strip()
    aimove = raw_response
    print(aimove)

    # Robust Parsing: Try to find a move embedded in <MOVE> tags first (CoT Prompting)
    cot_match = re.search(r"<MOVE>\s*([a-h][1-8][a-h][1-8][qrbn]?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?|[O0]-[O0](?:-[O0])?[+#]?)\s*</MOVE>", aimove, re.IGNORECASE)
    
    if cot_match:
        aimove = cot_match.group(1).strip()
        print(f"Extracted CoT move: {aimove}")
    else:
        # Fallback to standard UCI pattern anywhere in text
        match = re.search(r"\b[a-h][1-8][a-h][1-8][qrbn]?\b", aimove)
        if match:
            aimove = match.group(0)
            print(f"Extracted move: {aimove}")
    
    # Validation
    is_legal = False
    valid_move_obj = None
    for move in validMoves:
        if aimove == move.getChessNotation():
            is_legal = True
            valid_move_obj = move
            break
            
    if not is_legal:
         # SAN Fallback with Regex
        print("Checking SAN...")
        # Regex for SAN: Castling (O-O[-O]) OR Piece moves (e.g. Nf3, exd5, R1e2, a8=Q+)
        san_pattern = r"\b([KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?|[O0]-[O0](?:-[O0])?)[+#]?\b"
        match = re.search(san_pattern, aimove) # Check extracted move for SAN
        extracted_san = match.group(0) if match else aimove
        
        if match:
             print(f"Extracted SAN candidate: {extracted_san}")

        for move in validMoves:
            san = move.getSAN(validMoves)
            # Check against extracted SAN or the full aimove string
            if extracted_san.lower() == san.lower() or aimove.lower() == san.lower():
                print(f"SAN Match Found: {san}")
                is_legal = True
                valid_move_obj = move
                aimove = move.getChessNotation() # Update to UCI
                break

    # Evaluation / Blunder Detection
    ai_score = None
    best_score = None
    best_move_uci = None
    score_diff = None

    if is_legal and valid_move_obj:
        print("Evaluating move...")
        ai_score = scoreMove(gs, valid_move_obj)
        # Use a fresh copy for the engine's search
        best_move_obj, best_score = findBestMove(copy.deepcopy(gs), validMoves, returnScore=True, verbose=False)
        if best_move_obj:
            best_move_uci = best_move_obj.getChessNotation()
        score_diff = best_score - ai_score
        
        # Quick Classification for Console
        quality = "Best/Good"
        if score_diff > 8: quality = "BLUNDER"
        elif score_diff > 4: quality = "Mistake"

        print(f"AI Score: {ai_score}, Best: {best_score} ({best_move_uci}) Diff: {score_diff} [{quality}]")

    # Set persona details in logger (only happens once per game)
    logger.set_persona(persona_name, persona_prompt)

    # Log the attempt
    logger.log_move_attempt(persona_name, raw_response, aimove, is_legal, best_move=best_move_uci, best_score=best_score, ai_score=ai_score, score_diff=score_diff)

    if is_legal:
        return valid_move_obj
    
    print("Invalid move from Gemini. Using engine.")
    # Use copy for safety, though findBestMove cleans up
    fallback_move, fallback_score = findBestMove(gs, validMoves, returnScore=True, verbose=False) 
    if fallback_move:
        # Fallback is the best move, so diff is 0, ai_score is best_score
        print(f"Engine Fallback: {fallback_move.getChessNotation()} Score: {fallback_score}")
        logger.log_move_attempt("Engine (Fallback)", "N/A", fallback_move.getChessNotation(), True, 
                                best_move=fallback_move.getChessNotation(), 
                                best_score=fallback_score, 
                                ai_score=fallback_score, 
                                score_diff=0)
    return fallback_move 
    
 
def OLlama(gs, validMoves, persona_prompt="You are a Chess Master. Play solid, principled chess. 1. King Safety is #1. 2. Capture hanging pieces. 3. Do not hang your pieces. Output exactly ONE move (single word) from the Legal Moves list in UCI format or SAN.", persona_name="Ollama"):
    
    currValidMoves = [move.getChessNotation() for move in validMoves]
    turn = "White" if gs.WhiteToMove else "Black"
    FEN = gs.getFEN()
    print(f"DEBUG - FEN sent to AI: {FEN}")

    piece_case = "UPPERCASE" if turn == "White" else "lowercase"
    enemy_case = "lowercase" if turn == "White" else "UPPERCASE"
    direction = "up the board (rank 2 to 8)" if turn == "White" else "down the board (rank 7 to 1)"

    prompt_text = f"""
    Position (FEN): {FEN}
    Your Turn: {turn}
    Available Legal Moves: {", ".join(currValidMoves)}

    You are playing as {turn}. 
    - Your pieces are {piece_case} letters. The enemy's are {enemy_case}.
    - Your pawns move {direction}.
    Select exactly one move from the list above. Output ONLY the move string.
    """

    response = ollama.chat(
        model="gemma3:4b",
        messages=[
            {
                "role": "system",
                "content": persona_prompt
            },
            {
                "role": "user",
                "content": prompt_text
            }
        ],
        options={
            "temperature": 0.0,
            "num_predict": 20
        }
    )

    raw_response = response["message"]["content"].strip()
    best_move = raw_response
    print(best_move)

    # Robust Parsing: Try to find a move pattern (e.g., e2e4 or a7a8q) in the text
    match = re.search(r"\b[a-h][1-8][a-h][1-8][qrbn]?\b", best_move)
    if match:
        best_move = match.group(0)
        print(f"Extracted move: {best_move}")
    
    # Validation
    is_legal = False
    valid_move_obj = None
    for move in validMoves:
        if best_move == move.getChessNotation():
            is_legal = True
            valid_move_obj = move
            break

    # Validation (SAN fallback)
    if not is_legal:
        print("Checking SAN...")
        san_pattern = r"\b([KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?|[O0]-[O0](?:-[O0])?)[+#]?\b"
        match = re.search(san_pattern, best_move) # Check extracted move for SAN
        extracted_san = match.group(0) if match else best_move

        if match:
             print(f"Extracted SAN candidate: {extracted_san}")

        for move in validMoves:
            san = move.getSAN(validMoves)
            if extracted_san.lower() == san.lower() or best_move.lower() == san.lower():
                print(f"SAN Match Found: {san}")
                is_legal = True
                valid_move_obj = move
                best_move = move.getChessNotation() # Update to UCI
                break

    # Evaluation / Blunder Detection
    ai_score = None
    best_score = None
    best_move_uci = None
    score_diff = None

    if is_legal and valid_move_obj:
        print("Evaluating move...")
        ai_score = scoreMove(gs, valid_move_obj)
        best_move_obj, best_score = findBestMove(copy.deepcopy(gs), validMoves, returnScore=True)
        if best_move_obj:
            best_move_uci = best_move_obj.getChessNotation()
        score_diff = best_score - ai_score

        # Quick Classification for Console
        quality = "Best/Good"
        if score_diff > 8: quality = "BLUNDER"
        elif score_diff > 4: quality = "Mistake"

        print(f"AI Score: {ai_score}, Best: {best_score} ({best_move_uci}) Diff: {score_diff} [{quality}]")

    # Set persona details in logger (only happens once per game)
    logger.set_persona(persona_name, persona_prompt)

    # Log the attempt
    logger.log_move_attempt(persona_name, raw_response, best_move, is_legal, best_move=best_move_uci, best_score=best_score, ai_score=ai_score, score_diff=score_diff)

    if is_legal:
        return valid_move_obj
 
    
    print("Ollama returned invalid move:", best_move)
    fallback_move, fallback_score = findBestMove(gs, validMoves, returnScore=True, verbose=False)
    if fallback_move:
        print(f"Engine Fallback: {fallback_move.getChessNotation()} Score: {fallback_score}")
        logger.log_move_attempt("Engine (Fallback)", "N/A", fallback_move.getChessNotation(), True,
                                best_move=fallback_move.getChessNotation(),
                                best_score=fallback_score,
                                ai_score=fallback_score,
                                score_diff=0)
    return fallback_move  


def OpenRouterMove(gs, validMoves, persona_prompt="You are a Strong Chess Engine. Play solid, low-risk chess. 1. Never blunder material. 2. Capture free pieces. 3. Keep your King safe. Output exactly ONE legal move in UCI format.", persona_name="OpenRouter"):

    currValidMoves = [move.getChessNotation() for move in validMoves]
    turn = "White" if gs.WhiteToMove else "Black"
    FEN = gs.getFEN()
    print(f"DEBUG - FEN sent to AI: {FEN}")

    piece_case = "UPPERCASE" if turn == "White" else "lowercase"
    enemy_case = "lowercase" if turn == "White" else "UPPERCASE"
    direction = "up the board (rank 2 to 8)" if turn == "White" else "down the board (rank 7 to 1)"

    prompt_text = f"""
    Board State: {FEN}
    Active Player: {turn}
    Valid Moves: {", ".join(currValidMoves)}

    You are playing as {turn}. 
    - Your pieces are {piece_case} letters. The enemy's are {enemy_case}.
    - Your pawns move {direction}.
    Pick the best move from the Valid Moves list and return it in UCI format.
    Return only the move. No reasoning.
    """
    
    openrouter_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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"
    )

    # Retry loop (handles rate limits)
    for attempt in range(3):
        try:
            
            response = openrouter_client.chat.completions.create(
                model="arcee-ai/trinity-large-preview:free",
                messages=[
                    {
                        "role": "system",
                        "content": persona_prompt
                    },
                    {
                        "role": "user",
                        "content": prompt_text
                    }
                ],
                temperature=0.0,
                max_tokens=8
            )

            raw_output = response.choices[0].message.content.strip()
            print("Raw model output:", raw_output)
            # Robust Parsing: Try to find a move embedded in <MOVE> tags first (CoT Prompting)
            cot_match = re.search(r"<MOVE>\s*([a-h][1-8][a-h][1-8][qrbn]?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?|[O0]-[O0](?:-[O0])?[+#]?)\s*</MOVE>", raw_output, re.IGNORECASE)
            
            if cot_match:
                best_move = cot_match.group(1).strip()
                print(f"Extracted CoT move: {best_move}")
            else:
                match = re.search(r"\b[a-h][1-8][a-h][1-8]\b", raw_output)
                if match:
                    best_move = match.group(0)
                else :
                    best_move = raw_output
            print("OpenRouter move:", best_move)
            break

        except Exception as e:
            print("OpenRouter error:", e)
            time.sleep(2)

    else:
        print("OpenRouter failed. Using engine.")
        fallback_move, fallback_score = findBestMove(gs, validMoves, returnScore=True, verbose=False)
        if fallback_move:
            print(f"Engine Fallback: {fallback_move.getChessNotation()} Score: {fallback_score}")
            logger.log_move_attempt("Engine (Fallback)", "N/A", fallback_move.getChessNotation(), True,
                                    best_move=fallback_move.getChessNotation(),
                                    best_score=fallback_score,
                                    ai_score=fallback_score,
                                    score_diff=0)
        return fallback_move

    # Validate move exists
    is_legal = False
    valid_move_obj = None
    for move in validMoves:
        if best_move == move.getChessNotation():
            is_legal = True
            valid_move_obj = move
            break

    # Validation (SAN fallback)
    if not is_legal:
        print("Checking SAN...")
        san_pattern = r"\b([KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?|[O0]-[O0](?:-[O0])?)[+#]?\b"
        match = re.search(san_pattern, best_move)
        extracted_san = match.group(0) if match else best_move

        if match:
             print(f"Extracted SAN candidate: {extracted_san}")

        for move in validMoves:
            san = move.getSAN(validMoves)
            if extracted_san.lower() == san.lower() or best_move.lower() == san.lower():
                print(f"SAN Match Found: {san}")
                is_legal = True
                valid_move_obj = move
                best_move = move.getChessNotation() # Update to UCI
                break

    # Evaluation / Blunder Detection
    ai_score = None
    best_score = None
    best_move_uci = None
    score_diff = None

    if is_legal and valid_move_obj:
        print("Evaluating move...")
        ai_score = scoreMove(gs, valid_move_obj)
        best_move_obj, best_score = findBestMove(copy.deepcopy(gs), validMoves, returnScore=True)
        if best_move_obj:
            best_move_uci = best_move_obj.getChessNotation()
        score_diff = best_score - ai_score

        # Quick Classification for Console
        quality = "Best/Good"
        if score_diff > 8: quality = "BLUNDER"
        elif score_diff > 2: quality = "Mistake"

        print(f"AI Score: {ai_score}, Best: {best_score} ({best_move_uci}) Diff: {score_diff} [{quality}]")

    # Set persona details in logger (only happens once per game)
    logger.set_persona(persona_name, persona_prompt)

    # Log the attempt
    logger.log_move_attempt(persona_name, raw_output, best_move, is_legal, best_move=best_move_uci, best_score=best_score, ai_score=ai_score, score_diff=score_diff)

    if is_legal:
        return valid_move_obj

    print("Invalid move from OpenRouter. Using engine.")
    fallback_move, fallback_score = findBestMove(gs, validMoves, returnScore=True, verbose=False)
    if fallback_move:
        print(f"Engine Fallback: {fallback_move.getChessNotation()} Score: {fallback_score}")
        logger.log_move_attempt("Engine (Fallback)", "N/A", fallback_move.getChessNotation(), True,
                                best_move=fallback_move.getChessNotation(),
                                best_score=fallback_score,
                                ai_score=fallback_score,
                                score_diff=0)
    return fallback_move


def findBestMove(gs, validMoves, returnScore=False, verbose=False):
    turnMultiplier = 1 if gs.WhiteToMove else -1
    bestMove = None
    bestScore = -CHECKMATE
    alpha = -CHECKMATE
    beta = CHECKMATE

    random.shuffle(validMoves)  # To add unpredictability among equal moves

    for move in validMoves:
        gs.MakeMove(move)
        score = -negamaxAlphaBeta(gs, DEPTH - 1, -beta, -alpha, -turnMultiplier)
        gs.undoMove()

        if score > bestScore:
            bestScore = score
            bestMove = move
            alpha = max(alpha, bestScore)  # Update alpha
        
    if bestMove and verbose:
        print(bestMove.getChessNotation())
    
    if returnScore:
        return bestMove, bestScore
        
    return bestMove

def negamaxAlphaBeta(gs, depth, alpha, beta, turnMultiplier):
    if depth == 0:
        return turnMultiplier * scoreMaterial(gs.board)

    validMoves = gs.getValidMoves()

    if gs.checkMate:
        return -CHECKMATE + (DEPTH - depth)
    elif gs.staleMate:
        return STALEMATE

    maxScore = -CHECKMATE
    for move in validMoves:
        gs.MakeMove(move)
        score = -negamaxAlphaBeta(gs, depth - 1, -beta, -alpha, -turnMultiplier)
        gs.undoMove()

        if score > maxScore:
            maxScore = score
        alpha = max(alpha, score)
        if alpha >= beta:
            break  # β cutoff

    return maxScore

def scoreMaterial(board):
    score = 0
    for row in board:
        for square in row:
            if square != "--":
                pieceType = square[1]
                if square[0] == 'w':
                    score += pieceScore[pieceType]
                elif square[0] == 'b':
                    score -= pieceScore[pieceType]
    return score
