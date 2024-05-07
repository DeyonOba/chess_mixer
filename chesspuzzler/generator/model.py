from chess.pgn import GameNode, ChildNode
from chess import Move, Color
from chess.engine import Score
from dataclasses import dataclass
from typing import Tuple, List, Optional
from copy import deepcopy

@dataclass
class Puzzle:
    node: ChildNode
    moves: List[Move]
    cp: int

    # def __post_init__(self):
    #     # the fen would also stand as the unique identifier for puzzles
    #     self.fen = self.node.board().fen()
    #     self.pov = self.node.turn()
    #     self.game = self.add_mainline_nodes()
    #     self.mainline = list(self.game.mainline())

    # def add_mainline_nodes(self):
    #     # Create variable to store temporary pointer position
    #     # of the current child node, then transverse the node by 
    #     # adding the solution moves as the mainline variations 
    #     # finally return the pointer to the current child node which now
    #     # has the solution moves as the continuation of the mainline
    #     # nodes
    #     # copy_node = deepcopy(self.node)
    #     # tmp_node = copy_node
    #     # for move in self.moves:
    #     #     tmp_node = tmp_node.add_main_variation(move)
    #     # return copy_node
    #     tmp_node = self.node
    #     for move in self.moves:
    #         tmp_node = tmp_node.add_variation(move)
    #     return self.node

@dataclass
class Line:
    nb: Tuple[int, int]
    letter: str
    password: str

@dataclass
class EngineMove:
    move: Move
    score: Score

@dataclass
class NextMovePair:
    node: GameNode
    winner: Color
    best: EngineMove
    second: Optional[EngineMove]
