import random

pieceScore = {"K": 0, "Q": 9, "R": 5, "N": 3, "B": 3, "p": 1}
CHECKMATE = 10000
STALEMATE = 0
DEPTH = 4  # You can increase this as needed

def findBestMove(gs, validMoves):
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
