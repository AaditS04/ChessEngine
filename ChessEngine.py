""" This class is responsible for storing all the information about the current state of the game """
""" also responsible for determining the valid moves """

class GameState():
    def __init__(self):
        # board is a 8*8 2d list and each element has 2 char, first char is colour and second char represents the type of peice
        # -- represents a empty space
        self.board = [
            ["bR","bN","bB","bQ","bK","bB","bN","bR"],
            ["bp","bp","bp","bp","bp","bp","bp","bp"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["wp","wp","wp","wp","wp","wp","wp","wp"],
            ["wR","wN","wB","wQ","wK","wB","wN","wR"]
        ]
        self.WhiteToMove = True
        self.MoveLog = []
        '''
        we need to override the equals method to compare the move made and the valid moves
        '''
        
        self.whiteKingLocation = (7,4)
        self.blackKingLocation = (0,4)
        self.checkMate = False
        self.staleMate = False
        self.EnpassantPossible = ()
        self.currentCastleRights = CastleRights(True,True,True,True)
        self.threefoldRepetition = False
        self.castleRightsLog = [CastleRights(self.currentCastleRights.wks,self.currentCastleRights.bks
                                             ,self.currentCastleRights.wqs,
                                             self.currentCastleRights.bqs)]
        self.repetitions = {}  # Dictionary to store board state counts
        self.updateRepetitions()


        
        
    def MakeMove(self,move):
        self.board[move.startRow][move.startCol] = "--"
        self.board[move.endRow][move.endCol] = move.pieceMoved
        self.MoveLog.append(move)
        self.WhiteToMove = not self.WhiteToMove
        
        # also update king location
        if move.pieceMoved == 'wK':
            self.whiteKingLocation = (move.endRow,move.endCol)
        if move.pieceMoved=='bK':
            self.blackKingLocation = (move.endRow,move.endCol)
            
        # pawn promotion check
        if move.isPawnPromotion:
            self.board[move.endRow][move.endCol] = move.pieceMoved[0] + 'Q'
        
        # enpassant check
        if move.isEnpassantMove:    
            
            self.board[move.startRow][move.endCol] = '--'
        
        if move.pieceMoved[1] == 'p' and abs(move.startRow - move.endRow) ==2:
            self.EnpassantPossible = ((move.startRow + move.endRow)//2,move.startCol)
        else:
            self.EnpassantPossible = ()
        move.temp = self.EnpassantPossible
        
        # check if move is a castle move
        if move.isCastleMove:
            if move.endCol - move.startCol == 2:
                # king side castle
                self.board[move.endRow][move.endCol-1] = self.board[move.endRow][move.endCol+1]
                self.board[move.endRow][move.endCol+1] = "--"
            else:
                # queen side castle
                self.board[move.endRow][move.endCol+1] = self.board[move.endRow][move.endCol-2]
                self.board[move.endRow][move.endCol-2] = "--"
                
        
        # update castling rights when a king or a rook is moved
        self.updateCastleRights(move)
        self.castleRightsLog.append(CastleRights(self.currentCastleRights.wks,self.currentCastleRights.bks
                                             ,self.currentCastleRights.wqs,
                                             self.currentCastleRights.bqs))
        
        # update repetition history
        self.updateRepetitions()

    def updateRepetitions(self, decrement=False):
        state_key = self.get_state_key()
        if decrement:
            self.repetitions[state_key] = self.repetitions.get(state_key, 1) - 1
            if self.repetitions[state_key] < 3:
                self.threefoldRepetition = False # Clear draw flag if we undo out of it
        else:
            self.repetitions[state_key] = self.repetitions.get(state_key, 0) + 1
            # DEBUG: print(f"Position Count: {self.repetitions[state_key]} | WhiteToMove: {self.WhiteToMove}")
            
            # Only check for the draw if Black just moved (WhiteToMove is now True)
            if self.repetitions[state_key] >= 3 and self.WhiteToMove:
                # print("DEBUG: Threefold Repetition detected after Black move!")
                self.threefoldRepetition = True
            
    def get_state_key(self):
        # Create a unique tuple key for the current board position ONLY
        # Tuples are more efficient and stable than strings for dictionary keys
        return tuple(map(tuple, self.board))
        
        
    def undoMove(self):
        #implimented using keypress z
        if len(self.MoveLog) !=0:
            self.updateRepetitions(decrement=True)
            move  = self.MoveLog.pop()
            self.board[move.startRow][move.startCol] = move.pieceMoved
            self.board[move.endRow][move.endCol] = move.pieceCaptured
            self.WhiteToMove = not self.WhiteToMove
            if move.pieceMoved == 'wK':
               self.whiteKingLocation = (move.startRow,move.startCol)
            if move.pieceMoved=='bK':
               self.blackKingLocation = (move.startRow,move.startCol)
               
            self.EnpassantPossible = move.temp
            
            # undo enpassant move
            if move.isEnpassantMove:
                self.board[move.endRow][move.endCol] ="--"
                self.board[move.startRow][move.endCol] = move.pieceCaptured
                self.EnpassantPossible = (move.endRow,move.endCol)
                
            # undo a 2 square pawn advance
            if move.pieceMoved[1] =='p' and abs(move.startRow - move.endRow)==2:
                self.EnpassantPossible = ()
            # undo castling rights
            self.castleRightsLog.pop() # Remove current rights
            lastRights = self.castleRightsLog[-1] # New top is the previous rights
            self.currentCastleRights = CastleRights(lastRights.wks, lastRights.bks, lastRights.wqs, lastRights.bqs)
            
            # undo the castle move
            if move.isCastleMove:
                if move.endCol - move.startCol ==2:
                    self.board[move.endRow][move.endCol+1]=self.board[move.endRow][move.endCol-1]
                    self.board[move.endRow][move.endCol-1] = '--'
                else :
                    self.board[move.endRow][move.endCol-2] = self.board[move.endRow][move.endCol+1]
                    self.board[move.endRow][move.endCol+1] = '--'
                    
                    
          
    def updateCastleRights(self,move):
        if move.pieceMoved =='wK':
            self.currentCastleRights.wks = False
            self.currentCastleRights.wqs = False
        elif move.pieceMoved == 'bK':
            self.currentCastleRights.bks = False
            self.currentCastleRights.bqs = False
        elif move.pieceMoved =='wR':
            if move.startRow ==7:
                if move.startCol ==0:
                    self.currentCastleRights.wqs = False
                elif move.startCol ==7:
                    self.currentCastleRights.wks = False
        elif move.pieceMoved =='bR':
            if move.startRow ==0:
                if move.startCol ==0:
                    self.currentCastleRights.bqs = False
                elif move.startCol ==7:
                    self.currentCastleRights.bks = False
                
            
    
    def getFEN(self):
        fen = ""
        for r in range(8):
            empty = 0
            for c in range(8):
                piece = self.board[r][c]
                if piece == "--":
                    empty += 1
                else:
                    if empty > 0:
                        fen += str(empty)
                        empty = 0
                    # Convert internal piece notation (wK, bP) to FEN char (K, p)
                    color = piece[0]
                    type = piece[1]
                    if color == 'w':
                        fen_char = type.upper()
                    else:
                        fen_char = type.lower()
                    fen += fen_char
            if empty > 0:
                fen += str(empty)
            if r < 7:
                fen += "/"
        
        # Active Color
        fen += " w " if self.WhiteToMove else " b "
        
        # Castling
        castling = ""
        if self.currentCastleRights.wks: castling += "K"
        if self.currentCastleRights.wqs: castling += "Q"
        if self.currentCastleRights.bks: castling += "k"
        if self.currentCastleRights.bqs: castling += "q"
        if castling == "": castling = "-"
        fen += castling
        
        # En Passant
        if self.EnpassantPossible:
            r, c = self.EnpassantPossible
            # Convert row/col to algebraic (e.g., e3)
            # Row 0 is Rank 8, Row 7 is Rank 1.
            # So Rank = 8 - r
            rank = 8 - r
            file = chr(ord('a') + c)
            fen += f" {file}{rank}"
        else:
            fen += " -"
            
        # Halfmove/Fullmove (Defaulting to 0 1 as we don't track them strictly yet)
        fen += " 0 1"
        
        return fen

    """
    all moves considering checks
    """
    def getValidMoves(self):
        # Preserve the repetition flag before we test moves
        # (testing moves uses MakeMove/undoMove which can mess with the flag)
        tempThreefoldRepetition = self.threefoldRepetition

        moves =  self.getAllPossibleMoves()
        if self.WhiteToMove:
            self.getCastleMoves(self.whiteKingLocation[0],self.whiteKingLocation[1],moves)
        else:
            self.getCastleMoves(self.blackKingLocation[0],self.blackKingLocation[1],moves)
            
        for i in range(len(moves)-1,-1,-1):
            self.MakeMove(moves[i])
            self.WhiteToMove =not self.WhiteToMove
            if self.inCheck():
                moves.remove(moves[i])
            self.WhiteToMove = not self.WhiteToMove
            self.undoMove()
            
        # Restore the real repetition flag after testing
        self.threefoldRepetition = tempThreefoldRepetition
        
        if(len(moves)==0):
            if self.inCheck():
                self.checkMate = True
            else:
                self.staleMate = True
        else:
            self.checkMate = self.staleMate = False
            
        if self.threefoldRepetition:
            self.staleMate = True
        
        return moves
    
    
    def inCheck(self):
        if self.WhiteToMove:
            return self.squareUnderAttack(self.whiteKingLocation[0],self.whiteKingLocation[1])
        else:
            return self.squareUnderAttack(self.blackKingLocation[0],self.blackKingLocation[1])
    
    #  to determine if enemy can attack the  square r,c
    def squareUnderAttack(self,r,c):
        self.WhiteToMove = not self.WhiteToMove
        oppMoves = self.getAllPossibleMoves()
        self.WhiteToMove = not self.WhiteToMove
        for move in oppMoves:
            if move.endRow == r and move.endCol ==c:
                
                return True
        
        return False
        
    """
    all moves without considering checks
    """
    def getAllPossibleMoves(self):
        moves = []
        for r in range((len(self.board))):
            for c in range(len(self.board[r])):
                turn = self.board[r][c][0]
                if((turn =='w'and self.WhiteToMove) or (turn =='b'and not self.WhiteToMove)):
                    piece = self.board[r][c][1]
                    if piece =='p':
                        
                        self.getPawnMoves(r,c,moves)
                    elif piece == 'R':
                        self.getRookMoves(r,c,moves)
                    elif piece =='B':
                        self.getBishopMoves(r,c,moves)
                    elif piece == 'Q':
                        self.getQueenMoves(r,c,moves)
                    elif piece =='N':
                        self.getNightMoves(r,c,moves)
                    elif piece =='K':
                        self.getKingMoves(r,c,moves)
        return moves
                        
    # get all the pawn moves for a given location 
    def getPawnMoves(self,r,c,moves):
        #consider different cases in which a pawn moves can add complex moves like en - passant later
        if self.WhiteToMove and r-1>=0:
            if self.board[r-1][c]=="--":
                moves.append(Move((r,c),(r-1,c),self.board))
                if r==6:
                    if self.board[r-2][c]== "--":
                        moves.append(Move((r,c),(r-2,c),self.board))
            if c-1 >=0:
                if self.board[r-1][c-1][0]=='b':
                    moves.append(Move((r,c),(r-1,c-1),self.board))
                elif (r-1,c-1) == self.EnpassantPossible:
                    moves.append(Move((r,c),(r-1,c-1),self.board,isEnpassantMove = True))
            if c+1 <=7:
                if self.board[r-1][c+1][0] =='b':
                    moves.append(Move((r,c),(r-1,c+1),self.board))
                elif (r-1,c+1) == self.EnpassantPossible:
                    moves.append(Move((r,c),(r-1,c+1),self.board,isEnpassantMove = True))
        elif not self.WhiteToMove and r+1 <=7:
            if self.board[r+1][c]=="--":
                moves.append(Move((r,c),(r+1,c),self.board))
                if r==1:
                    if self.board[r+2][c]== "--":
                        moves.append(Move((r,c),(r+2,c),self.board))
            if c-1 >=0:
                if self.board[r+1][c-1][0]=='w':
                    moves.append(Move((r,c),(r+1,c-1),self.board))
                elif (r+1,c-1) == self.EnpassantPossible:
                    moves.append(Move((r,c),(r+1,c-1),self.board,isEnpassantMove = True))
            if c+1 <=7:
                if self.board[r+1][c+1][0] =='w':
                    moves.append(Move((r,c),(r+1,c+1),self.board))
                elif (r+1,c+1) == self.EnpassantPossible:
                    moves.append(Move((r,c),(r+1,c+1),self.board,isEnpassantMove = True))
            
                
    def getRookMoves(self,r,c,moves):
        directions = [(-1,0),(1,0),(0,-1),(0,1)]
        enemycolor = 'b' if self.WhiteToMove else 'w'
        for d in directions:
            for i in range (1,8):
                endRow = r+ d[0]*i
                endCol  = c+d[1]*i
                if 0<= endRow and endRow < 8 and 0<= endCol and endCol <8 :
                    endPiece = self.board[endRow][endCol]
                    if endPiece == "--":
                        moves.append(Move((r,c),(endRow,endCol),self.board))
                    elif endPiece[0] == enemycolor:
                        moves.append(Move((r,c),(endRow,endCol),self.board))
                        break
                    else:
                        break
    
    def getBishopMoves(self,r,c,moves):
        directions = [(1,1),(1,-1),(-1,1),(-1,-1)]
        enemycolor = 'b' if self.WhiteToMove else 'w'
        for d in directions:
            for i in range(1,8):
                endRow = r+d[0]*i
                endCol = c+ d[1]*i
                if 0<=endRow <8 and 0<=endCol<8:
                    endPiece = self.board[endRow][endCol]
                    if endPiece =="--":
                        moves.append(Move((r,c),(endRow,endCol),self.board))
                    elif endPiece[0] == enemycolor:
                        moves.append(Move((r,c),(endRow,endCol),self.board))
                        break
                    else :
                        break
    def getQueenMoves(self,r,c,moves):
        self.getRookMoves(r,c,moves)
        self.getBishopMoves(r,c,moves)
    def getNightMoves(self,r,c,moves):
        kmoves = [(-2,-1),(-2,1),(2,-1),(2,1),(-1,-2),(-1,2),(1,-2),(1,2)]
        allycolor = 'w' if self.WhiteToMove else 'b'
        for i in kmoves:
            endRow = r + i[0]
            endCol = c+ i[1]
            if 0<=endRow <8 and 0<=endCol <8:
                if self.board[endRow][endCol][0]!= allycolor:
                    moves.append(Move((r,c),(endRow,endCol),self.board))
    
                    
            
    def getKingMoves(self,r,c,moves):
        kmoves = [(1,1),(1,-1),(-1,1),(-1,-1),(-1,0),(1,0),(0,-1),(0,1)]
        allycolor = 'w' if self.WhiteToMove else 'b'
        for i   in kmoves:
            endRow = r+ i[0]
            endCol = c + i[1]
            if 0<=endRow<8 and 0<=endCol<8:
                if self.board[endRow][endCol][0]!= allycolor:
                    moves.append(Move((r,c),(endRow,endCol),self.board))
        
    
    def getCastleMoves(self,r,c,moves):
        if self.squareUnderAttack(r,c):
            return
        if (self.WhiteToMove and self.currentCastleRights.wks ) or(  not self.WhiteToMove and self.currentCastleRights.bks):
            self.getKingSideCastleMoves(r,c,moves)
        
        if (self.WhiteToMove and self.currentCastleRights.wqs ) or(  not self.WhiteToMove and self.currentCastleRights.bqs):
            self.getQueenSideCastleMoves(r,c,moves)
    
    def getKingSideCastleMoves(self,r,c,moves):
        if  c+2<=7 and self.board[r][c+1] == "--" and self.board[r][c+2] =="--":
            if not self.squareUnderAttack(r,c+1) and not self.squareUnderAttack(r,c+2):
                moves.append(Move((r,c),(r,c+2),self.board,isCastleMove= True))
            
            
    def getQueenSideCastleMoves(self,r,c,moves):
       if c-3>=0 and self.board[r][c-1]=='--' and self.board[r][c-2] =='--' and  self.board[r][c-3]=='--':
            if not self.squareUnderAttack(r,c-1) and not self.squareUnderAttack(r,c-2) and not self.squareUnderAttack(r,c-3):
                moves.append(Move((r,c),(r,c-2),self.board,isCastleMove= True))       
        
       
class Move():
    
    ranksToRows = { "1":7,"2":6, "3":5,"4":4,"5":3,"6":2, "7":1,"8":0 }
    rowsToRanks = {v: k for k,v in ranksToRows.items()}
    filesToCols = {"a":0,"b":1,"c":2,"d":3,"e":4,"f":5,"g":6,"h":7}
    colsToFiles = {v:k for k,v in filesToCols.items()}
    
    def __init__(self,startSq,endSq,board,isEnpassantMove = False,isCastleMove = False):
       
        self.startRow = startSq[0]
        self.startCol = startSq[1]
        self.endRow = endSq[0]
        self.endCol = endSq[1]
        self.pieceMoved = board[self.startRow][self.startCol]
        self.pieceCaptured = board[self.endRow][self.endCol]
        self.moveID = self.startRow * 1000 + self.startCol*100 + self.endRow*10 + self.endCol
        self.isPawnPromotion = False
        if (self.pieceMoved=='wp' and self.endRow ==0)or( self.pieceMoved =='bp'and self.endRow ==7):
            self.isPawnPromotion = True
        # check for enpassant
        self.isEnpassantMove = isEnpassantMove
        self.isCastleMove = isCastleMove
        if self.isEnpassantMove:
            self.pieceCaptured = 'wp' if self.pieceMoved =='bp' else 'bp'
        
        temp = ()
        
        
    
    def __eq__(self,other):
        if isinstance(other,Move):
            return self.moveID == other.moveID
        return False
        
    def getChessNotation(self):
        # you can make this a real chess notation to add the peice and whether a capture is made or not or if a chasseling is done
        return self.getRankFile(self.startRow,self.startCol) + self.getRankFile(self.endRow,self.endCol)
        
    def getRankFile(self,r,c):
        return self.colsToFiles[c] + self.rowsToRanks[r]

    def getSAN(self, valid_moves=None):
        """
        Generates Standard Algebraic Notation (SAN) for the move.
        Requires valid_moves list for disambiguation (e.g. Nbd7).
        """
        if self.isCastleMove:
            if self.endCol - self.startCol == 2:
                return "O-O"
            else:
                return "O-O-O"
        
        start_square = self.getRankFile(self.startRow, self.startCol)
        end_square = self.getRankFile(self.endRow, self.endCol)
        
        # Pawn Moves
        if self.pieceMoved[1] == 'p':
            if self.pieceCaptured != "--" or self.isEnpassantMove:
                san = start_square[0] + "x" + end_square
            else:
                san = end_square
            
            if self.isPawnPromotion:
                san += "=Q"
            return san

        # Piece Moves
        piece_type = self.pieceMoved[1]
        san = piece_type
        
        # Disambiguation
        if valid_moves:
            needs_file = False
            needs_rank = False
            ambiguous = False
            
            for m in valid_moves:
                if m == self:
                    continue
                if m.pieceMoved == self.pieceMoved and m.endRow == self.endRow and m.endCol == self.endCol:
                    ambiguous = True
                    if m.startCol == self.startCol:
                        needs_rank = True
                    else:
                        needs_file = True
            
            if ambiguous:
                if needs_file:
                    san += start_square[0]
                elif needs_rank:
                    san += start_square[1]
                else: # Default to file if neither specifically needed but still ambiguous (rare)
                    san += start_square[0]

        if self.pieceCaptured != "--":
            san += "x"
        
        san += end_square
        return san
    
    
class CastleRights():
        def __init__(self,wks,bks,wqs,bqs):
            self.wks=wks
            self.bks=bks
            self.wqs=wqs
            self.bqs=bqs
                  
    
