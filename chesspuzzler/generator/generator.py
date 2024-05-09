import logging
import argparse
import chess
import chess.pgn
import chess.engine
import copy
import sys
from chesspuzzler.generator.model import Puzzle, NextMovePair
from io import StringIO
from chess import Move, Color
from chess.engine import SimpleEngine, Mate, Cp, Score, PovScore
from chess.pgn import Game, ChildNode
from typing import List, Optional, Union, Set
from chesspuzzler.generator.util import get_next_move_pair, material_count, material_diff, is_up_in_material, maximum_castling_rights, win_chances, count_mates
from chesspuzzler.analysis.logger import configure_log

logger = configure_log(__name__, "puzzle_gen.log")

pair_limit = chess.engine.Limit(depth = 50, time = 30, nodes = 25_000_000)
mate_defense_limit = chess.engine.Limit(depth = 15, time = 10, nodes = 8_000_000)

mate_soon = Mate(15)

class Generator:
    def __init__(self, engine: SimpleEngine) -> None:
        self.engine = engine

    def is_valid_mate_in_one(self, pair: NextMovePair) -> bool:
        
        if pair.best.score != Mate(1):
            # Ensure that the best move is a mate in one
            return False
        non_mate_win_threshold = 0.6
        if not pair.second or win_chances(pair.second.score) <= non_mate_win_threshold:
            # If the second pair is None or the win chance is less than the set non mate
            # winning threshold then the first pair (i.e Best Move) is a valid mate in one.
            return True
        
        if pair.second.score == Mate(1):
            # if the second candidate move is a mate in one, check if they are other moves
            # that are mate in one also
            logger.debug("Looking for the best non-mating move...")
            mates = count_mates(copy.deepcopy(pair.node.board()))
            info = self.engine.analyse(pair.node.board(), multipv=mates+1, limit=pair_limit)
            scores = [pv["score"].pov(pair.winner) for pv in info]

            # The first non mate in 1 move
            if scores[-1] < Mate(1) and win_chances(scores[-1]) > non_mate_win_threshold:
                return False
            return True
        return False
    
    # is pair.best the only continuation
    def is_valid_attack(self, pair: NextMovePair) -> bool:
        return (
            pair.second is None or self.is_valid_mate_in_one(pair)
            or win_chances(pair.best.score) > win_chances(pair.second.score) + 0.7
        )

    def get_next_pair(self, node: ChildNode, winner: Color) -> Optional[NextMovePair]:
        pair = get_next_move_pair(self.engine, node, winner, pair_limit)
        if node.board().turn == winner and not self.is_valid_attack(pair):
            logger.debug("No valid attack {}".format(pair))
            return None
        return pair
    
    def get_next_move(self, node: ChildNode, limit: chess.engine.Limit) -> Optional[Move]:
        result = self.engine.play(node.board(), limit=limit)
        return result.move if result else None
    
    def cook_mate(self, node: ChildNode, winner: Color) -> Optional[List[Move]]:
        print("COOK MATE...")
        board = node.board()

        # if the game has come to an end return empty list
        if board.is_game_over():
            print("GAME IS OVER")
            return []
        
        # if move turn is the winner of the game
        if board.turn == winner:
            pair = self.get_next_pair(node, winner)
            if not pair:
                print("Could not find next pair...")
                return None
            
            if pair.best.score < mate_soon:
                logger.debug("Best move is not a mate, we're probably not searching deep enough")
                print("Best move is not a mate, we're probably not searching deep enough")
                return None
            move = pair.best.move
        else:
            next = self.get_next_move(node, mate_defense_limit)
            if not next:
                return None
            move = next

        # Recursively make engine moves still the game is over or one of the other conditions is meet above 
        follow_up = self.cook_mate(node.add_main_variation(move), winner)

        if not follow_up and type(follow_up) is not list:
            return None
        return [move] + follow_up
    
    def analyze_game(self, game: Game, tier: int) -> Optional[Puzzle]:
        print("ANALYZE GAME...")

        logger.debug(f'Analyzing tier {tier} {game.headers.get("Site")}...')
        print(f'Analyzing tier {tier} {game.headers.get("Site")}...')

        prev_score: Score = Cp(20)
        seen_epds: Set[str] = set()
        board = game.board()
        skip_until_irreversible = False
        puzzle_count = 0
        puzzle_list = []

        for node in game.mainline():
            if skip_until_irreversible:
                if board.is_irreversible(node.move):
                    skip_until_irreversible = False
                    seen_epds.clear()
                else:
                    board.push(node.move)
                    continue

            current_eval = node.eval()

            if not current_eval:
                logger.debug("Skipping game without eval on ply {}".format(node.ply()))
                print("Skipping game without eval on ply {}".format(node.ply()))

                if puzzle_count:
                    logger.debug("Found {} puzzles from {}".format(puzzle_count, game.headers.get("Site")))
                    print("Found {} puzzles from {}".format(puzzle_count, game.headers.get("Site")))
                else:
                    logger.debug("Found nothing from {}".format(game.headers.get("Site")))
                    print("Found nothing from {}".format(game.headers.get("Site")))

                return puzzle_list

            board.push(node.move)
            epd = board.epd()
            if epd in seen_epds:
                skip_until_irreversible = True
                continue
            seen_epds.add(epd)

            if board.castling_rights != maximum_castling_rights(board):
                continue

            result = self.analyze_position(node, prev_score, current_eval, tier)

            if isinstance(result, Puzzle):
                print("Found Puzzle...")
                puzzle_count += 1
                print(result)
                # return result
                puzzle_list.append(result)
                prev_score = -current_eval.pov(node.turn())
                continue

            prev_score = -result
        if puzzle_count:
            logger.debug("Found {} puzzles from {}".format(puzzle_count, game.headers.get("Site")))
            print("Found {} puzzles from {}".format(puzzle_count, game.headers.get("Site")))
        else:
            logger.debug("Found nothing from {}".format(game.headers.get("Site")))
            print("Found nothing from {}".format(game.headers.get("Site")))

        return puzzle_list
    
    def cook_advantage(self, node: ChildNode, winner: Color) -> Optional[List[NextMovePair]]:
        print("COOK ADVANTAGE...")
        board = node.board()

        if board.is_repetition(2):
            logger.debug("Found repetition, canceling")
            return None

        pair = self.get_next_pair(node, winner)
        if not pair:
            return []
        if pair.best.score < Cp(200):
            logger.debug("Not winning enough, aborting")
            print("Not winning enough, aborting")
            return None

        follow_up = self.cook_advantage(node.add_main_variation(pair.best.move), winner)

        if follow_up is None:
            return None

        return [pair] + follow_up

    def analyze_position(self, node: ChildNode, prev_score: Score, current_eval: PovScore, tier: int) -> Union[Puzzle, Score]:
        board = node.board()
        winner = board.turn
        score = current_eval.pov(winner)

        if board.legal_moves.count() < 2:
            return score

        game_url = node.game().headers.get("Site")

        logger.debug("{} {} to {}".format(node.ply(), node.move.uci() if node.move else None, score))
        print("{} {} to {}".format(node.ply(), node.move.uci() if node.move else None, score))

        if prev_score > Cp(300) and score < mate_soon:
            logger.debug("{} Too much of a winning position to start with {} -> {}".format(node.ply(), prev_score, score))
            print("{} Too much of a winning position to start with {} -> {}".format(node.ply(), prev_score, score))
            return score
        if is_up_in_material(board, winner):
            logger.debug("{} already up in material {} {} {}".format(node.ply(), winner, material_count(board, winner), material_count(board, not winner)))
            print("{} already up in material {} {} {}".format(node.ply(), winner, material_count(board, winner), material_count(board, not winner)))
            return score
        elif score >= Mate(1) and tier < 3:
            logger.debug("{} mate in one".format(node.ply()))
            print("{} mate in one".format(node.ply()))
            return score
        elif score > mate_soon:
            logger.debug("Mate {}#{} Probing...".format(game_url, node.ply()))
            print("Mate {}#{} Probing...".format(game_url, node.ply()))
            mate_solution = self.cook_mate(copy.deepcopy(node), winner)
            # if mate_solution is None or (tier == 1 and len(mate_solution) == 3):
            if mate_solution is None:
                return score
            print("PUZZLE CREATED")
            return Puzzle(node, mate_solution, score.mate())
        elif score >= Cp(200) and win_chances(score) > win_chances(prev_score) + 0.6:
            if score < Cp(400) and material_diff(board, winner) > -1:
                logger.debug("Not clearly winning and not from being down in material, aborting")
                print("Not clearly winning and not from being down in material, aborting")
                return score
            logger.debug("Advantage {}#{} {} -> {}. Probing...".format(game_url, node.ply(), prev_score, score))
            print("Advantage {}#{} {} -> {}. Probing...".format(game_url, node.ply(), prev_score, score))
#             if self.server.is_seen_pos(node):
#                 logger.debug("Skip duplicate position")
#                 return score
            puzzle_node = copy.deepcopy(node)
            solution : Optional[List[NextMovePair]] = self.cook_advantage(puzzle_node, winner)
#             self.server.set_seen(node.game())
            if not solution:
                return score
            while len(solution) % 2 == 0 or not solution[-1].second:
                if not solution[-1].second:
                    logger.debug("Remove final only-move")
                solution = solution[:-1]
            if not solution or len(solution) == 1 :
                logger.debug("Discard one-mover")
                print("Discard one-mover")
                return score
            if tier < 3 and len(solution) == 3:
                logger.debug("Discard two-mover")
                print("Discard two-mover")
                return score
            cp = solution[len(solution) - 1].best.score.score()

            cp = solution[len(solution) - 1].best.score.score()
            return Puzzle(node, [p.best.move for p in solution], 999999998 if cp is None else cp)
        else:
            return score
