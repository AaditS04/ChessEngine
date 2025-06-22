""" This is the driver file , for handeling the user input and displaying current gaame state"""

import pygame as p

import ChessEngine
import ChessAI


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
    sqSelected = () # to keep track of the last selected squaare by th user
    playerClicks = []
    gameOver  = False
    playerOne = True # if human is playing white this is true 
    playerTwo = False # if a human is playing black this is true
    
    while running:
        humanTurn = (gs.WhiteToMove  and playerOne) or ( not gs.WhiteToMove and playerTwo)
        if not gameOver:
            for e in p.event.get() :
                if e.type ==  p .QUIT:
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
            AIMove = ChessAI.findBestMove(gs,validMoves)
            if AIMove is None:
                AIMove = ChessAI.findRandomMove(validMoves)
                
            
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


                    
            
        
            
