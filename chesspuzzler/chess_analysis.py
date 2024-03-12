#!/usr/bin/env python3

"""Analyze Chess Games stored in pgn format."""

import pandas as pd
import chess
import chess.pgn
import chess.engine
from chess.engine import Cp, Mate
from chesspuzzler.constants import Constant
import re
from colorama import Fore, Back, Style
from dataclasses import dataclass

class TrackCpWdl:
    
    INITIAL_CP = 0
    INITIAL_WDL = Cp(INITIAL_CP).wdl().expectation() # wdl 0.5
    INITIAL_MATE_IN = Mate(0).mate()
    
    white_prev_wdl = INITIAL_WDL
    black_prev_wdl = INITIAL_WDL
    white_prev_cp = INITIAL_CP
    black_prev_cp = INITIAL_CP
    white_prev_mate_in = INITIAL_MATE_IN
    black_prev_mate_in = INITIAL_MATE_IN
    
    def __init__(self, board: chess.Board, info: chess.engine.InfoDict) -> None:
        self.board = board
        self.info = info
    
    def track_wdl(self) -> tuple:
        """Track the Win Draw Loss probability of WHITE or BLACK."""
        if self.board.turn:
            curr_wdl = self.info["score"].black().wdl().expectation()
            prev_wdl = TrackCpWdl.white_prev_wdl
            opp_curr_wdl = TrackCpWdl.black_prev_wdl
        else:
            curr_wdl = self.info["score"].white().wdl().expectation()
            prev_wdl = TrackCpWdl.black_prev_wdl
            opp_curr_wdl = TrackCpWdl.white_prev_wdl

        self.curr_wdl = curr_wdl    
        # self.set_prev_wdl(curr_wdl)
        return curr_wdl, prev_wdl, opp_curr_wdl
    
    def track_cp(self) ->tuple:
        """
        Track centre pawn score for both sides WHITE and BLACK

        if number of moves to checkmate is found set cp to 10,000
        """
        if self.board.turn:
            curr_cp = self.info["score"].black()
            curr_cp = self.set_mate_cp(curr_cp)
            prev_cp = TrackCpWdl.white_prev_cp
        else:
            curr_cp = self.info["score"].white()
            curr_cp = self.set_mate_cp(curr_cp)
            prev_cp = TrackCpWdl.black_prev_cp

        self.curr_cp = curr_cp   
        # self.set_prev_cp(curr_cp)
        return curr_cp, prev_cp
    
    def track_mate(self) -> tuple[int, int]:
        """
        Track current and previous number of moves to checkmate.

        If no mating moves found (i.e. mate_in = None) set current moves to mate
        to the Initial moves to mate at the start of the game
        """
        if self.board.turn:
            curr_mate_in = self.info["score"].black().mate()
            prev_mate_in = TrackCpWdl.white_prev_mate_in
            opp_mate_in = TrackCpWdl.black_prev_mate_in
        else:
            curr_mate_in = self.info["score"].white().mate()
            prev_mate_in = TrackCpWdl.black_prev_mate_in
            opp_mate_in = TrackCpWdl.white_prev_mate_in
            
        if not curr_mate_in:
            curr_mate_in = TrackCpWdl.INITIAL_MATE_IN

        self.curr_mate_in = curr_mate_in    
        # self.set_prev_mate_in(curr_mate_in)
        return curr_mate_in, prev_mate_in, opp_mate_in
    
    def track_curr_scores(self):
        if self.board.turn:
            cp = self.info["score"].black()
            wdl = self.info["score"].black().wdl().expectation()
            mate = self.info["score"].black().mate()
        else:
            cp = self.info["score"].white()
            wdl = self.info["score"].white().wdl().expectation()
            mate = self.info["score"].white().mate()
        
        if not mate:
            mate = TrackCpWdl.INITIAL_MATE_IN
        cp = self.set_mate_cp(cp)
        
        return cp, wdl, mate
              
    def update(self):
        """Update previous eval to the current eval wdl, cp, and number of mating moves."""
        if self.board.turn:
            TrackCpWdl.white_prev_wdl = self.curr_wdl
            TrackCpWdl.white_prev_cp = self.curr_cp
            TrackCpWdl.white_prev_mate_in = self.curr_mate_in
        else:
            TrackCpWdl.black_prev_wdl = self.curr_wdl
            TrackCpWdl.black_prev_cp = self.curr_cp
            TrackCpWdl.black_prev_mate_in = self.curr_mate_in
            
    def set_mate_cp(self, cp):
        """sets cp score for mate position to 10,000"""
        if cp.mate():
            if cp.mate() > 0:
                return 10_000
            else:
                return -10_000
        else:
            return cp.score()    
                  
    @classmethod
    def reset(cls):
        """Reset evaluation scores to initial score at begining of the game."""
        cls.white_prev_wdl = cls.INITIAL_WDL
        cls.black_prev_wdl = cls.INITIAL_WDL
        cls.white_prev_cp = cls.INITIAL_CP
        cls.black_prev_cp = cls.INITIAL_CP
        cls.black_prev_mate_in = cls.INITIAL_MATE_IN
        cls.white_prev_mate_in = cls.INITIAL_MATE_IN
        
@dataclass
class TrackEval:
    cp: int
    wdl: float
    mate: int
    opponents_wdl: float
    opponents_mate_in: float

    def __post_init__(self):
        self.mateCreated = True if self.mate > 0 else False
        self.inCheckMate = True if self.mate < 0 else False
        self.noMate = True if not self.mate else False
    # def __init__(self, cp, wdl, mate, opponents_curr_wdl, opponents_mate_in):
    #     self.cp = cp
    #     self.wdl = wdl
    #     self.mate = mate
    #     self.opponents_wdl = opponents_curr_wdl
    #     self.opponents_mate = opponents_mate_in
    #     self.mateCreated = self.check_for_mate()
    #     self.inCheckMate = self.in_check_mate()
    #     self.noMate = self.is_mate_found()
        
    # def check_for_mate(self):
    #     if self.mate > 0:
    #         return True
    #     return False
    
    # def in_check_mate(self):
    #     if self.mate < 0:
    #         return True
    #     return False
    
    # def is_mate_found(self):
    #     if not self.mate:
    #         return True
    #     return False
    
class EvaluationEngine:
    def __init__(self, board: chess.Board, engine: chess.engine.SimpleEngine) -> None:
        self.board = board
        self.engine = engine
       
    def position_eval(self, track_eval: TrackCpWdl) -> str:
        curr_mate_in, prev_mate_in, opponents_mate_in = track_eval.track_mate()
        curr_wdl, prev_wdl, opponents_wdl = track_eval.track_wdl()
        curr_cp, prev_cp = track_eval.track_cp()
        print("Mate:", "curr:", curr_mate_in, "prev:", prev_mate_in)
        print("Cp:", "curr:", curr_cp, "prev:", prev_cp)
        print("wdl:", "curr:", curr_wdl, "prev:", prev_wdl)
        print("opponents current wdl:", opponents_wdl)

        prev = TrackEval(prev_cp, prev_wdl, prev_mate_in, opponents_wdl, opponents_mate_in)
        curr = TrackEval(curr_cp, curr_wdl, curr_mate_in, opponents_wdl, opponents_mate_in)

        advantage = curr.wdl > 0.5
        lostAdvantage = not advantage
        mateCreated = prev.mateCreated or curr.mateCreated or opponents_mate_in < 0
#         print("Is mateCreated: ", mateCreated)
        if self.board.is_checkmate():
#             print("Game Ended with Checkmate.")
            return "Best Move"
        
        if mateCreated:
            print("Checking Mating conditions")
            if prev.mateCreated and curr.inCheckMate:
                print("Lost mate and now in Mate")
                return "Blunder"
            elif curr.noMate and prev.noMate and opponents_mate_in < 0:
                print("Missing mating chance created by opponent.")
                return "Blunder"
            elif prev.mateCreated and curr.noMate and advantage:
                print("Lost mate but still has the advantage...")
                if curr.wdl < prev.wdl:
                    self.evaluate(curr.wdl, prev.wdl)
                else:
                    self.further_analysis()

            elif prev.mateCreated and curr.noMate and lostAdvantage:
                print("Lost mate and also the advantage...")
                return "Blunder"
            elif curr.mate and prev.noMate:
                print("Mating sequence created....")
                return self.further_analysis()
            elif curr.mate >= prev.mate and prev.mateCreated:
                print(f"Fewer mating moves in {prev.mate} but now {curr.mate}")
                return self.further_analysis()
            elif curr.mate < prev.mate:
                print("Making precise mating moves...")
                return self.further_analysis()
            else:
                self.further_analysis()
        elif (1 - curr.wdl - curr.opponents_wdl) >= 0.1:
            print("Check opponents wdl diff")
            return self.evaluate(curr.wdl, 1-curr.opponents_wdl)
#         elif (1 - curr.wdl - curr.opponents_wdl) >= 0.1:
# # #             print("Check opponents wdl diff")
#             return self.evaluate(curr.wdl,1-curr.opponents_wdl)
        elif curr.wdl < prev.wdl:
            print("previous wdl is greater than current")
            return self.evaluate(curr.wdl, prev.wdl)
        elif prev.wdl == 0 and curr.wdl == 0:
#             print("Check Evaluation in Lossing wdl")
            if (prev.cp - curr.cp) >= 300:
                return "Blunder"
            elif (prev.cp - curr.cp) >= 200:
                return "Mistake"
            else:
                return self.further_analysis()
        else:
            print("**Evaluating ....")
            return self.further_analysis()
        
    def further_analysis(self):
        return "Good Move"
    
    def evaluate(self, curr_wdl, prev_wdl):
        delta_wdl = prev_wdl - curr_wdl
#         print("delta_wdl", delta_wdl)
        if delta_wdl >= 0.3:
            return "Blunder"
        elif delta_wdl >= 0.2:
            return "Mistake"
        elif delta_wdl >= 0.1:
            return "Inaccuracy"
        else:
            return self.further_analysis()

    # def should_investigate(self, curr_wdl, prev_wdl):
    #         if prev_wdl > curr_wdl:
    #             if self.evaluate(curr_wdl, prev_wdl):
    #                 return True
    #         elif prev_wdl == 0 and curr_wdl == 0:
    #             return False
    #         return False

def split_uci_moves(move: str) -> str:
    # Pattern to split should be a non digit and a digit
    PATTERN = r'(\D\d)'
    
    output = re.split(PATTERN, move)
    # Remove empty string from the output
    output = [s for s in output if s]
    # The uci (universal chess interface) consists of two concatenated string
    # positions the first is the original position of piece on board, 
    # and the second is the move been made on the board.
    
    # Example
    # d2d4 (Queen's opening)
    # d2 is the original position of the pawn
    # d4 is the move been made
    return output[1]

def symbol_uci_move(node):
    move = split_uci_moves(node.move.uci())
    piece_symbol = node.board().piece_at(chess.parse_square(move)).unicode_symbol()
    return f"{piece_symbol} {move}"

def game_analysis(game):
    board = chess.Board()
    engine = chess.engine.SimpleEngine.popen_uci(Constant.ENGINE_PATH)
    game_data = []
    column_labels = ["move_number", "side", "move", "fen", "cp", "wdl", "mate", "evaluation"]
    for move_number, node in enumerate(game.mainline()):
        side = "White" if board.turn else "Black"
        move_info = [move_number+1]
        if not board.is_legal(node.move):
            print(symbol_uci_move(node))
            print("Move {} is illegal".format(symbol_uci_move(node)))
            print(" ".join(map(lambda x: x.uci(), board.generate_pseudo_legal_moves())))
            break
        board.push(node.move)
        fen = board.fen()    
        # print(board.unicode())  
        # display(board) 
        info = engine.analyse(board, chess.engine.Limit(depth=20))
        track_eval = TrackCpWdl(board, info)
        evaluation = EvaluationEngine(board, engine)
        move_unicode_symbol = symbol_uci_move(node)
#         print(symbol_uci_move(node))
        evaluation = evaluation.position_eval(track_eval)
        report = Fore.RED + f"{move_unicode_symbol} {evaluation}" if evaluation == "Blunder" else Fore.GREEN + f"{move_unicode_symbol} {evaluation}"
        print(report)
        print(Style.RESET_ALL)
        cp, wdl, mate = track_eval.track_curr_scores()
        move_info.extend([side, node.move, cp, fen, wdl, mate, evaluation])
        game_data.append(move_info)
        track_eval.update()
        should_investigate_puzzle = True if evaluation in ["Blunder", "Mistake", "Miss"] else False

        if should_investigate_puzzle:
            # print("\t".join([side, symbol_uci_move(node), fen, str(cp), evaluation, Fore.CYAN+"INVESTIGATE PUZULLE"]))
            # print(Style.RESET_ALL)
            pass
        else:
            # print("\t".join([side, symbol_uci_move(node), str(cp), evaluation]))
            continue
        
    df = pd.DataFrame(game_data, columns=column_labels)

    engine.quit()
    board.reset()    
    TrackCpWdl.reset()
    return df