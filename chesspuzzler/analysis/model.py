import math
# import chess
from chess import Move
from dataclasses import dataclass, field
from chess.engine import PovScore, Cp
from chess.pgn import ChildNode
from typing import List, ClassVar

@dataclass
class TrackEval:
    povscore: PovScore
    turn: int

    def __post_init__(self):
        self.set_mate()
        self.set_cp()
        self.wdl = self.povscore.pov(self.turn).wdl(model="sf12").expectation()
        # self.wdl = self.wdl_score()
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
class BestMovePair:
    best: PovScore
    second: PovScore
    turn: int

@dataclass
class Continuation:
    bestmove: Move
    solution: List[Move]
    turn: int

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
    
    def get_info(self):
        board_info_list = [self.half_move_number, self.move, self.side, self.fen]
        return board_info_list

# class TrackPrevScore(TrackEval):
#     white_prev_score: ClassVar[PovScore] = PovScore(Cp(20), chess.WHITE)
#     black_prev_score: ClassVar[PovScore] = PovScore(Cp(-20), chess.BLACK)

#     def __init__(self, score: PovScore, turn: int) -> None:
#         self.score = self.set_prev_score(score)
#         super().__init__(self.score, self.turn)

#     def set_score(self, score):
#         if self.turn:
#             TrackPrevScore.white_prev_score = score
#             return TrackPrevScore.white_prev_score
#         else:
#             TrackPrevScore.white_prev_score = score
#             return TrackPrevScore.black_prev_score