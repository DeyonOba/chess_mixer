import math
# import chess
from chess import Move, Color
from dataclasses import dataclass, field
from chess.engine import PovScore, Cp
from chess.pgn import ChildNode
from typing import List, ClassVar, Optional

@dataclass
class TrackEval:
    povscore: PovScore
    turn: int

    def __post_init__(self):
        self.set_mate()
        self.set_cp()
        # self.wdl = self.povscore.pov(self.turn).wdl(model="sf15").expectation()
        self.wdl= self.wdl_score()
        self.mateCreated = self.mate > 0
        self.inCheckMate = self.mate < 0
        self.noMateFound = not self.mate
        
    def set_mate(self):
        mate = self.povscore.pov(self.turn).mate()
        if mate:
            self.mate = mate
        else:
            self.mate = 0
            
    def set_cp(self):
        cp = self.povscore.pov(self.turn)
        
        if cp.mate():
            self.cp = 10_000 if cp.mate() > 0 else -10_000
        else:
            self.cp = cp.score()
            
    def win_chances(self):
        """
        winning chances from -1 to 1
        https://lichess.org/page/accuracy
        """
        mate = self.povscore.pov(self.turn).mate()
        if mate is not None:
            return 1 if mate > 0 else -1

        cp = self.povscore.pov(self.turn).score()
        MULTIPLIER = -0.003682081729595926 # https://github.com/lichess-org/lila/pull/11148
        return 2 / (1 + math.exp(MULTIPLIER * cp)) - 1 if cp is not None else 0
    
    def wdl_score(self):
        win_chances = self.win_chances()
        return (50 + 50 * win_chances) * 0.01

@dataclass
class EngineMove:
    turn: Color
    move: Move
    score: PovScore

@dataclass
class CandidateMoves:
    node: ChildNode
    turn: Color
    best: EngineMove
    second: Optional[EngineMove]
    third: Optional[EngineMove]

@dataclass
class BoardInfo:
    node: ChildNode

    def __post_init__(self):
        self.board = self.node.board()
        self.side = "White" if not self.board.turn else "Black"
        self.turn = not self.board.turn
        self.fen = self.board.fen()
        self.move = self.node.move
        self.half_move_number = self.node.ply()
        self.fullmove_number = self.board.fullmove_number if self.turn else self.board.fullmove_number - 1
    
    def get_info(self):
        board_info_list = [self.half_move_number, self.move, self.side, self.fen]
        return board_info_list
