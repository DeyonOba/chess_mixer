#!/usr/bin/python3
"""
Creates game analysis, puzzles, and puzzle tags.
"""
version = 0.2

import sys
import argparse
from chess.engine import SimpleEngine
from chesspuzzler.analysis.constants import Constant
from chesspuzzler.analysis.file_util import GameDownloader
from chesspuzzler.analysis.chess_analysis import GameAnalysis
from chesspuzzler.generator.generator import Generator
from chesspuzzler.tagger.cook import cook


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Chess puzzle generator')
    parser.add_argument('game_id', metavar='GAME_ID', type=str, help='ID of the game to analyze')
    return parser.parse_args()

def main():
    """Entry point of puzzle generator."""
    args = parse_arguments()
    game_id = args.game_id

    download = GameDownloader()
    game = download.load_pgn_game(game_id)

    if not game:
        download.get_game_via_gameid(game_id)
        game = download.load_pgn_game(download.game_id)

    print(game)
    analyzer = GameAnalysis(game)
    node = analyzer.game_analysis()
    engine = SimpleEngine.popen_uci(Constant.ENGINE_PATH)
    puzzles = Generator(engine).analyze_game(node, 3)
    print("Number of puzzles generated:", len(puzzles))
    if puzzles:
        for puzzle in puzzles:
            print("Puzzle:", puzzle.node.board().fen())
            print("Puzzle Solution:", " ".join([move.uci() for move in puzzle.moves]))
            print(puzzle)
            print(puzzle.__dict__)
            print("Creating puzzle tags...")
            print("Puzzle Tags:", cook(puzzle))
    engine.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"chesspuzzler version: {version}")

    