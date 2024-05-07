from chess import Move
from copy import deepcopy
from dataclasses import dataclass, field
from chess.pgn import Game, ChildNode
from chess import Color
from typing import List, Literal, Optional

TagKind = Literal[
    "advancedPawn",
    "advantage",
    "anastasiaMate",
    "arabianMate",
    "attackingF2F7",
    "attraction",
    "backRankMate",
    "bishopEndgame",
    "bodenMate",
    "capturingDefender",
    "castling",
    "clearance",
    "coercion",
    "crushing",
    "defensiveMove",
    "discoveredAttack",
    "deflection",
    "doubleBishopMate",
    "doubleCheck",
    "dovetailMate",
    "equality",
    "enPassant",
    "exposedKing",
    "fork",
    "hangingPiece",
    "hookMate",
    "interference",
    "intermezzo",
    "kingsideAttack",
    "knightEndgame",
    "long",
    "mate",
    "mateIn5",
    "mateIn4",
    "mateIn3",
    "mateIn2",
    "mateIn1",
    "oneMove",
    "overloading",
    "pawnEndgame",
    "pin",
    "promotion",
    "queenEndgame",
    "queensideAttack",
    "quietMove",
    "rookEndgame",
    "queenRookEndgame",
    "sacrifice",
    "short",
    "simplification",
    "skewer",
    "smotheredMate",
    "trappedPiece",
    "underPromotion",
    "veryLong",
    "xRayAttack",
    "zugzwang"
]

# @dataclass
# class Puzzle:
#     fen: str
#     game: Game
#     pov : Color = field(init=False)
#     mainline: List[ChildNode] = field(init=False)
#     cp: int

#     def __post_init__(self):
#         self.fen = self.game.board().fen()
#         self.pov = not self.game.turn()
#         self.mainline = list(self.game.mainline())
@dataclass
class Puzzle:
    node: ChildNode
    moves: List[Move]
    cp: int

    def __post_init__(self):
        # the fen would also stand as the unique identifier for puzzles
        self.fen = self.node.board().fen()
        self.pov = self.node.turn()
        self.game = self.add_mainline_nodes()
        self.mainline = list(self.game.mainline())

    def add_mainline_nodes(self):
        # Create variable to store temporary pointer position
        # of the current child node, then transverse the node by 
        # adding the solution moves as the mainline variations 
        # finally return the pointer to the current child node which now
        # has the solution moves as the continuation of the mainline
        # nodes
        copy_node = deepcopy(self.node)
        tmp_node = copy_node
        for move in self.moves:
            tmp_node = tmp_node.add_main_variation(move)
        return copy_node
        # tmp_node = self.node
        # for move in self.moves:
        #     tmp_node = tmp_node.add_variation(move)
        # return self.node
