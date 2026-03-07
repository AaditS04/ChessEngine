""" This is the driver file , for handeling the user input and displaying current game state"""

import pygame as p
import copy
import ChessEngine
import ChessAI
import re



WIDTH = HEIGHT   = 750
DIMENSION  = 8
SQ_SIZE = HEIGHT // DIMENSION
MAX_FPS = 15
IMAGES = {}

"""
Innitialize a global dictionary of images , this will be called eactly once in the main
"""
p.mixer.init()
sound = p.mixer.Sound("move.wav")


def load_images():
    pieces = ["bR","bN","bB","bQ","bK","wR","wN","wB","wQ","wK","bp","wp"]
    
    for piece in pieces:
        IMAGES[piece] = p.transform.scale(p.image.load("images/" + piece +  ".png"),(SQ_SIZE,SQ_SIZE))
        
def main():
    p.init()
    screen = p.display.set_mode((WIDTH,HEIGHT))
    clock = p.time.Clock()
    screen.fill(p.Color("White"))
    gs = ChessEngine.GameState()
    validMoves = gs.getValidMoves()
    moveMade = False # only generate validMoves after the game state changes and the move is made
    load_images()
    running  = True
    sqSelected = () # to keep track of the last selected square by th user
    playerClicks = []
    gameOver  = False
    playerOne = False # if human is playing white this is true 
    playerTwo = False # if a human is playing black this is true
    currboard = copy.deepcopy(gs.board)
    currValidMoves = []
    for move in validMoves:
                currValidMoves.append(move.getChessNotation())
    
    while running:
        
        # if currboard != gs.board :
        #     print(gs.board)
        #     print("\n")
        #     for move in validMoves:
        #         currValidMoves.append(move.getChessNotation())
        #     print(currValidMoves)
        #     #currValidMoves = []
        #     print("\n")
        #     currboard = copy.deepcopy(gs.board)
        
        humanTurn = (gs.WhiteToMove  and playerOne) or ( not gs.WhiteToMove and playerTwo)
        if not gameOver:
           
            for e in p.event.get() :
                if e.type ==  p.QUIT:
                    running  = False
                # mouse instructions
                elif e.type == p.MOUSEBUTTONDOWN:
                    if not gameOver and humanTurn:
                        location = p.mouse.get_pos()
                        col = location[0]//SQ_SIZE
                        row = location[1]//SQ_SIZE
                        if sqSelected == (row,col):
                            sqSelected = ()
                            playerClicks=[]
                        else:
                            sqSelected = (row,col)
                            playerClicks.append(sqSelected)
                        # if it was the second click of the user we have to make some changes
                        if len(playerClicks)==2:
                            move = ChessEngine.Move(playerClicks[0],playerClicks[1],gs.board)
                            for i in range(len(validMoves)):
                                if move == validMoves[i]:
                                    gs.MakeMove(validMoves[i])
                                    moveMade=True
                                    sound.play()
                                    ChessAI.logger.log_move_attempt("Human", "Manual", validMoves[i].getChessNotation(), True)
                            
                                    sqSelected=()
                                    playerClicks=[]
                                
                            if  not moveMade:
                                playerClicks = [sqSelected]
                        if gs.checkMate or gs.staleMate:
                            gameOver = True
                
                # key instructions
                elif e.type == p.KEYDOWN:
                    if e.key == p.K_z:
                        gs.undoMove()
                        moveMade = True
                    if e.key ==p.K_r:
                        gs = ChessEngine.GameState()
                        validMoves = gs.getValidMoves()
                        sqSelected = ()
                        playerClicks = []
                        moveMade = False
                        gameOver = False
        
        # AI move finder logic
        if not gameOver and not humanTurn:
            
            # --- Strategic Persona Setup (Center Controller - Morphy) ---
            custom_persona_name = "Morphy (Center)"
            custom_persona_prompt = (
                "You are a Classical Chess Master. You play for development and center control.\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. Analyze the FEN to understand the board and use the 'Legal Moves' list.\n"
                "2. Rapid Development: Prioritize moving your E and D pawns, Knights, and Bishops.\n"
                "3. Center Control: Aim your pieces at the center squares (d4, e4, d5, e5).\n"
                "4. King Safety: Castle early (O-O or O-O-O).\n"
                "5. Blunder Check: DO NOT blunder! Never move a piece to a square where it can be captured by the enemy for free.\n"
                "Output EXACTLY ONE move from the Legal Moves list in UCI format."
            )

            # Pass the custom prompt and name to the AI function
            AIMove = ChessAI.OpenRouterMove(gs, validMoves, persona_prompt=custom_persona_prompt, persona_name=custom_persona_name)
            
            # if AIMove is None:
            #     AIMove = ChessAI.findRandomMove(validMoves)
                
            
            gs.MakeMove(AIMove)
            
            sound.play()
            moveMade = True
            
                    
        if moveMade:
            validMoves = gs.getValidMoves()
            moveMade = False 
        
        DrawGameState(screen,gs,validMoves,sqSelected)
        if gs.checkMate:
            gameOver = True
            if gs.WhiteToMove:
                drawText(screen, 'Black won by checkmate')
            else:
                drawText(screen , ' White won by checkmate')
        elif gs.staleMate:
            gameOver = True
            drawText(screen ,'Game is draw by stalemate')
        elif gs.threefoldRepetition:
            gameOver = True
            drawText(screen, 'Draw by Threefold Repetition')  
        
        clock.tick(MAX_FPS)
        
        p.display.flip()
        
        
        
        
"""
hilight square selected
"""
def hilightSquares(screen,gs,validMoves,sqSelected):
    if sqSelected !=():
        r,c = sqSelected
        if gs.board[r][c][0] == ('w' if gs.WhiteToMove else 'b'): # sq selected is a piece
            s= p.Surface((SQ_SIZE,SQ_SIZE))
            s.set_alpha(100)
            s.fill(p.Color('blue'))
            screen.blit(s,(c*SQ_SIZE,r*SQ_SIZE))
            # hilight moves from that square
            s.fill(p.Color('yellow'))
            for move in validMoves:
                if move.startRow ==r  and move.startCol ==c:
                    screen.blit(s,(move.endCol*SQ_SIZE,move.endRow*SQ_SIZE))


def DrawGameState(screen,gs,validMoves,sqSelected):
    drawBoard(screen)
    hilightSquares(screen,gs,validMoves,sqSelected)
    drawPieces(screen,gs)
    
def drawBoard(screen):
    # top left square is always light and alternate squates and light and dark 
    colors = [p.Color(" light grey") , p.Color(" dark green")]
    for r in range(DIMENSION):
        for c in range (DIMENSION):
            color = colors[(r+c)%2]
            p.draw.rect(screen, color,p.Rect(c*SQ_SIZE,r*SQ_SIZE,SQ_SIZE,SQ_SIZE))
               

def drawPieces(screen,gs):
    # we have a different function cause we need to hilight a piece before a square 
    for r in range(DIMENSION):
        for c in range (DIMENSION):
            piece = gs.board[r][c]
            if piece !="--":
                screen.blit(IMAGES[piece],p.Rect(c*SQ_SIZE,r*SQ_SIZE,SQ_SIZE,SQ_SIZE))


def drawText(screen, text):
    font = p.font.SysFont("Helvetica",32,True,False)
    textObject = font.render(text,0,p.Color('Red'))
    textLocation = p.Rect(0,0,WIDTH ,HEIGHT).move(WIDTH/2-textObject.get_width()/2,HEIGHT/2-textObject.get_height()/2)
    screen.blit(textObject,textLocation) 
    
                         
if  __name__ == "__main__":
    main()


                    
            
        
            
