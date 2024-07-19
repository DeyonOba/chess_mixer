#!/usr/bin/env python3

"""Analyze Chess Games stored in pgn format."""

import os
import copy
import sys
import logging
from enum import Enum
from typing import Optional
import pandas as pd
from chesspuzzler.analysis.file_util import FileManager
import chess
from chess import Board, Square, Move
import chess.pgn
from chess.pgn import ChildNode
import chess.engine
from chess.engine import Cp, Mate, PovScore, InfoDict, SimpleEngine
from chesspuzzler.analysis.constants import Constant
from chesspuzzler.analysis.board_util import (
    win_chances, wdl_score, up_in_material, symbol_uci_move,
    material_count, material_diff, is_piece_hanging, slient_move
)
from chesspuzzler.analysis.model import CandidateMoves, EngineMove, TrackEval
from colorama import Fore, Back, Style
from chesspuzzler.analysis.model import TrackEval, BoardInfo
from chesspuzzler.analysis.logger import configure_log

# Create logging folder if it does not exist
os.makedirs("./data/logging", exist_ok=True)
logger = configure_log(__name__, "analysis.log")
board_logger = configure_log("board", "evaluation.log", view_on_console=True)

class Judgement(Enum):
    """List of chess move classification."""
    BLUNDER = "Blunder"
    MISTAKE = "Mistake"
    INACCURACY = "Inaccuracy"
    GOOD = "Good"
    EXCELLENT = "Excellent"
    BEST = "Best"
    DECISIVE = "Decisive"
    BRILLANT = "Brillant"
    FORCED = "Forced"
    

class EvaluationEngine:
    CandidateInfo: Optional[CandidateMoves] = None
    def __init__(
        self,
        engine: SimpleEngine,
        board: Board,
        move: Move,
        info: InfoDict,
        prevInfo: InfoDict,
        turn: int
    ) -> None:
        self.engine = engine
        self.board = board.copy()
        self.move = move
        self.info = info
        self.prevInfo = prevInfo
        self.turn = turn
        self.comment = ""
        self.best_move = prevInfo["pv"][0].uci()
        self.initial_board = board.copy()
        self.initial_board.pop()

       
    def position_classification(self) -> str:
        self.current = TrackEval(self.info["score"], self.turn)
        self.previous = TrackEval(self.prevInfo["score"], self.turn)

        self.advantage = self.current.wdl > 0.5
        lostAdvantage = not self.advantage
        mateSequence = self.previous.mateCreated or self.current.mateCreated

        logger.info("--"*20)
        logger.info("SCORE DETAILS: ")
        logger.info("TURN: {}".format("White" if self.turn else "Black"))
        logger.info("Full move number: {}\t Half move number: {}".format(self.node.board().fullmove_number,self.node.ply()))
        logger.info("INDEX\t\t\tCP\tWDL\tMATE\t")
        logger.info("Previous Move Scores   {}\t{}\t{}".format(self.previous.cp, self.previous.wdl, self.previous.mate))
        logger.info("Current Move Scores    {}\t{}\t{}".format(self.current.cp, self.current.wdl, self.current.mate))
        
        if self.board.is_checkmate():
            self.comment = "Game Ended with Checkmate..."
            return Judgement.BEST.value
        
        if len(list(self.initial_board.legal_moves)) == 1:
            self.comment = "Forced move"
            return Judgement.FORCED.value
        
        if mateSequence:
            logger.debug("Checking Mating conditions")

            if self.previous.mateCreated and self.current.inCheckMate:
                self.comment = "Lost mate and now in Mate."
                return Judgement.BLUNDER.value        
            
            elif self.previous.mateCreated and self.current.noMateFound:
                if self.current.cp > 999:
                    self.comment += "Did you know your opponent could have been checkmate in {}.".format(self.current.mate + 1)
                    return Judgement.INACCURACY.value
                elif self.current.cp > 700:
                    self.comment += "Did you know your opponent could have been checkmate in {}.".format(self.current.mate + 1)
                    return Judgement.MISTAKE.value
                else:
                    self.comment += "What an opportunity missed, you could have checkmated you opponent in {}.".format(self.current.mate + 1)
                    return Judgement.BLUNDER.value
         
            elif self.previous.mateCreated and self.current.noMateFound and self.advantage:
                self.comment = "Lost mate but you still have the advantage"
                if self.current.wdl < self.previous.wdl:
                    return self.evaluate(self.current.wdl, self.previous.wdl)
                else:
                    return self.further_analysis()

            elif self.previous.mateCreated and self.current.noMateFound and lostAdvantage:
                self.comment = "Lost mate and also the advantage."
                return Judgement.BLUNDER.value
            
            elif self.current.mateCreated and self.previous.noMateFound:
                self.comment = "Mating sequence created"
                return self.further_analysis()

            elif self.current.mate >= self.previous.mate and self.previous.mateCreated:
                self.comment = f"Fewer mating moves in {self.previous.mate} but now {self.current.mate}"
                return self.further_analysis()
            
            elif self.current.mate < self.previous.mate and self.current.mateCreated and self.previous.mateCreated:
                self.comment = "Making precise mating moves."
                return self.further_analysis()
            
            else:
                self.comment = "Check for candidate moves and best move"
                self.further_analysis()
                
        elif self.previous.noMateFound and self.current.inCheckMate:
            self.comment += "Checkmate cannot be avoided."
            if self.previous.cp < -999:
                return Judgement.INACCURACY.value
            elif self.previous.cp < -700:
                return Judgement.MISTAKE.value
            else:
                self.comment += " They might have still been a chance to continue the game, if you played {}.".format(self.best_move)
                return Judgement.BLUNDER.value

        # # `evaluate` only considers moves that a Excellent down to blunder
        elif (self.previous.wdl - self.current.wdl >= 0.02) and (self.move.uci() != self.best_move):
            # At the beginning of a game WHITE has an advantage of 0.25 center pawn score,
            # this CP score is equivalent to a Win Draw Loss probability of 0.009.
            # In order to ensure that minute changes in Cp like this are not necessary
            # classified as bad moves, but are not the best. 
            delta_wdl = self.previous.wdl - self.current.wdl
            return self.evaluate(delta_wdl)

        else:
            return self.further_analysis()
        
    
    def evaluate(self, delta_wdl):
        if delta_wdl >= 0.2:
            self.comment += "Blunder best move is  {}.".format(self.best_move)
            return Judgement.BLUNDER.value
        elif delta_wdl >= 0.1:
            self.comment += "Mistake best move is  {}.".format(self.best_move)
            return Judgement.MISTAKE.value
        elif delta_wdl >= 0.05:
            self.comment += "Made an inaccuracy you can consider moves like  {}.".format(self.best_move)
            return Judgement.INACCURACY.value
        else:
            self.comment += "Nice move, but you can consider this move {} as the best.".format(self.best_move)
            return Judgement.GOOD.value
        
        
    def further_analysis(self):
        self.comment += "You found the best move in the position."

        if not EvaluationEngine.CandidateInfo:
            # If `CandidateInfo` is not set (i.e None) and analyse position with higher engine depth
            EvaluationEngine.CandidateInfo = self.engine.analyse(chess.Board(self.initial_board.fen()), limit=Limit(depth=27), multipv=2)

        MultiInfo = EvaluationEngine.CandidateInfo
        BestInfo, SecondInfo = MultiInfo[0], MultiInfo[1]

        self.best_move = BestInfo['pv'][0].uci()

        if self.move.uci() == self.best_move:
            # Update the object attribute `current` to the position evaluation of `BestInfo`
            self.current = EngineMove(BestInfo, self.turn).score

        if self.move.uci() == SecondInfo["pv"][0].uci():
            # Update the object attribute `current` to the position evaluation of `BestInfo`
            self.current = EngineMove(SecondInfo, self.turn).score  
    
        if (self.previous.wdl < 0.49 and self.current.wdl < 0.49):
            # Best move played does not give a winning advantage
            if self.previous.wdl - self.current.wdl >= 0.009 and self.move.uci() != self.best_move:
                return Judgement.EXCELLENT.value
            return Judgement.BEST.value
        
        if up_in_material(self.initial_board, self.turn) and self.current.cp > 100:
            # Player is up in material and has a better position
            if self.previous.wdl - self.current.wdl >= 0.009 and self.move.uci() != self.best_move:
                return Judgement.EXCELLENT.value
            return Judgement.BEST.value

        cdt_moves = CandidateMoves(
            self.turn, 
            EngineMove(BestInfo, self.turn), 
            EngineMove(SecondInfo, self.turn)
            )

        if cdt_moves.second.score:
            if ( win_chances(cdt_moves.best.score.cp) > win_chances(cdt_moves.second.score.cp) + 0.6):
                # Check for Brillancy or Decisive Moves

                # Compare the best move with the second best move
                # Check if the best move is a valid attack (i.e is by far better than the second best move)
                if (
                    is_piece_hanging(self.board, self.move.to_square)
                    or slient_move(self.board, self.initial_board, self.turn, self.move)
                    or self.move.promotion != chess.QUEEN or self.move.promotion != chess.ROOK):
                    return Judgement.BRILLANT.value
                else:
                    return Judgement.DECISIVE.value
                
        if self.previous.wdl - self.current.wdl >= 0.009 and self.move.uci() != self.best_move:
            return Judgement.EXCELLENT.value
        return Judgement.BEST.value

class GameAnalysis(FileManager):

    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        self.is_game_processed = False

    def game_analysis(self):
        from chesspuzzler.analysis.logger import log_board
        
        board = chess.Board()
        print("Load Engine")
        engine = SimpleEngine.popen_uci(Constant.ENGINE_PATH)
        prevInfo = engine.analyse(board, chess.engine.Limit(depth=20), info= chess.engine.Info.ALL)
        print("Engine Successfully loaded")

        game_data = []
        column_labels = ["move_number", "move", "side", "fen", "cp", "wdl", "mate", "evaluation"]

        for node in self.game.mainline():
            if not board.is_legal(node.move):
                print(symbol_uci_move(node))
                print("Move {} is illegal".format(symbol_uci_move(node)))
                print(" ".join(map(lambda x: x.uci(), board.generate_pseudo_legal_moves())))
                break
            
            board.push(node.move)
            board_info = BoardInfo(node)
            currInfo = engine.analyse(board, chess.engine.Limit(depth=20), info= chess.engine.Info.ALL)

            evaluate = EvaluationEngine(engine, board, node.move, currInfo, prevInfo, not board.turn)
            position_classification = evaluate.position_classification()
    
            # After evaluating the board position update the `prevScore`
            prevInfo = currInfo

            cp, wdl, mate = evaluate.current.cp, evaluate.current.wdl, evaluate.current.mate
            move_info = board_info.get_info() + [cp, wdl, mate, position_classification]
            board_logger.info(log_board(board_info, node, currInfo["score"].pov(node.turn), position_classification))
            logger.debug("--"*20)
            game_data.append(move_info)


        df = pd.DataFrame(game_data, columns=column_labels)
        print(df.groupby(["side", "evaluation"])["move_number"].count())
        # self.update_game(node.game(), node.game().headers.get("Site"))
        self.save_dataframe(df, node.game().headers.get("Site"))  
        engine.quit()
        self.is_game_processed = True 
        return node.game()
    
    @staticmethod
    def set_node_details(node: ChildNode, povscore: PovScore) -> ChildNode:
        """
        Sets node comment with evaluation and engine depth.
        """
        if node.eval() and node.eval_depth():
            if node.eval_depth() < Constant.SCAN_ENGINE_DEPTH:
                node.set_eval(povscore, Constant.SCAN_ENGINE_DEPTH)
            if node.clock():
                node.set_clock(node.clock())
        else:
            node.set_eval(povscore, Constant.SCAN_ENGINE_DEPTH)
            if node.clock():
                node.set_clock(node.clock())
        return node
