import argparse
import pandas as pd
import chess
import chess.pgn
import chess.engine
import io


def set_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--depth",
        type=int,
        default=23,
        help="Requires the engine depth as an Integer"
    )
    parser.add_argument(
        "--dir_path",
        type=str,
        default=r'C:\Users\HP\Desktop\ChessX',
        help="Project directory formatted as a string"
    )
    parser.add_argument(
        "--engine_dir",
        type=str,
        default="stockfish_engine\stockfish-windows-x86-64-avx2.exe"
    )
    parser.add_argument(
        "--data",
        type=str,
        default="data\game_data\lichess_73Gz0j7m72l6.pgn"
    )

    return parser.parse_args()


args = set_args()

with io.open(args.data, "r") as file:
    game = chess.pgn.read_game(file)  # Load the pgn chess game

# Get game headers
game_headers = dict(game.headers)


def get_3_candidate_moves(board, engine, depth, multipv):
    """
    Get Candidate Moves form the Chess Position Played on the Board.

    The candidate moves are the move that can alternately be played instead of the best move without lossing a
    considerate amount of advantage in the game.

    Parameters
    ----------
    board : chess.Board
        Contains the current position of the board.
    engine : chess.engine.SimpleEngine
        Loaded Lichess Stockfish engine.
    depth : int
        Engine depth.
    multipv : int
        Output the N best lines (principle variation) when searching.

    Returns
    -------
    list of str
        Containing N best engine candidate moves.

    """

    info_ = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=multipv)
    best_3_engine_moves = [i["pv"][0].uci() for i in info_]
    return best_3_engine_moves


def get_evaluation_report(move_number, side, previous_wdl, current_wdl):
    """
    Get the evaluation report of each move.

    Parameters
    ----------
    move_number : int
        The number of moves played (n-1).
    side : {"White", "Black"}
        The side to move either white or black.
    previous_wdl : float
        The previous win draw loss probability of either sides.
    current_wdl : float
        The current win draw loss probability of the current position.

    Returns
    -------
    {"Best Move", "Excellent", "Good Move", "Blunder", "Mistake", "Inaccuracy"}
    """
    global previous_white_wdl
    global previous_black_wdl
    if move_number == 0:
        previous_white_wdl = current_wdl
    if move_number == 1:
        previous_black_wdl = current_wdl

    if side == "White":
        delta_wdl = abs(current_wdl - previous_white_wdl)
        previous_white_wdl = current_wdl

    else:
        delta_wdl = abs(current_wdl - previous_black_wdl)
        previous_black_wdl = current_wdl

    if move == best_move:
        return "Best Move"

    elif (move in candidate_moves) and delta_wdl < 0.1:
        return "Excellent"

    elif delta_wdl >= 0.3:
        return "Blunder"

    elif 0.3 > delta_wdl >= 0.2:
        return "Mistake"

    elif 0.2 > delta_wdl >= 0.1:
        return "Inaccuracy"

    else:
        return "Good Move"


# Run the engine
engine = chess.engine.SimpleEngine.popen_uci(args.engine_dir)
engine.configure({"UCI_elo": 2850})
print("engine loaded successfully")
# Initialize the chess board
board = chess.Board()
moves_list = []
previous_white_wdl = 0
previous_black_wdl = 0

report_list = []
openings_df = pd.read_csv("data\db\openings_sheet.csv")


for move_number, move in enumerate(game.mainline_moves()):
    # push the move played (san)
    board.push(move)

    # get the FEN of the current board position
    fen = board.fen()

    # get the moves
    moves_list.append(move.uci())
    moves = " ".join(moves_list)

    # Get detailed analysis of the game in a dictionary
    info = engine.analyse(board, chess.engine.Limit(depth=args.depth))

    best_move = engine.play(board, chess.engine.Limit(depth=args.depth)).move
    pv = info["pv"]
    # Get the engine evaluation info for "White" or "Black"
    # The possible move number for white can only be 0, which is the first move
    # or a move number divisible by 2
    if move_number % 2 == 0 or move_number == 0:
        score = info["score"].black().score()
        wdl_prob = info["score"].black().wdl().expectation()
        side = "White"
        side_to_move = "Black"
        mate = info["score"].black().mate()

    else:
        score = info["score"].white().score()
        wdl_prob = info["score"].white().wdl().expectation()
        side = "Black"
        side_to_move = "White"
        mate = info["score"].white().mate()

    # When move is not best move. check for 3 moves recommended by the engine
    candidate_moves = get_3_candidate_moves(board, engine, depth=15, multipv=3)

    evaluation_report = get_evaluation_report(
        move_number, side,
        previous_white_wdl, wdl_prob
    )
    # pgn files without header key name "opening"
    header_keys = list(map(str.lower, game_headers.keys()))
    if "opening" in header_keys:
        OpeningFamily, OpeningVariation = game_headers["Opening"].split(": ")
        # Record  game analysis (GA) details
        GA = {
            "FEN": fen, "OpeningFamily": OpeningFamily,
            "OpeningVariation": OpeningVariation, "Move": move,
            "Best_Move": best_move, "Candidate_Moves": candidate_moves,
            "Engine_Moves": pv, "Moves": moves, "Move_Number": move_number + 1,
            "Side": side, "Side_to_play": side_to_move, "Win_Draw_Loss_Probability": wdl_prob,
            "Engine_depth": args.depth, "Report": evaluation_report
        }
    else:
        GA = {
            "FEN": fen, "Move": move, "Best_Move": best_move,
            "Candidate_Moves": candidate_moves, "Engine_Moves": pv,
            "Moves": moves, "Move_Number": move_number + 1, "Side": side,
            "Side_to_play": side_to_move, "Win_Draw_Loss_Probability": wdl_prob,
            "Engine_depth": args.depth, "Report": evaluation_report
        }
    print(moves)
    GA["check_open_in_db"] = openings_df.query("moves == @moves")["name"]
    print(GA["check_open_in_db"])
    break

#     # update `GA` with pgn headers
#     GA.update(game_headers)

#     # when score is in mating move number, calculate mate cp
#     if mate is not None:
#         GA["cp"] = (mate / abs(mate)) * 3600  # set high cp value representing the value of the king
#     else:
#         GA["cp"] = score

#     report_list.append(GA)

# df = pd.DataFrame(report_list)
# # Reset the chess board to the initial positioning of pieces
# board.reset()

# # Get the count of all unique values in `Report`
# print(df["Report"].value_counts())
# # Extract puzzles that have evaluation as either blunder or mistake
# puzzles_df = df.query("Report == 'Blunder' or Report == 'Mistake'")
# print(puzzles_df.shape)
# print(puzzles_df.head())
# # Save the total game analysis
# df.to_csv("data\chess_analysis_report\chess_game_analysis.csv", index=False)
# # Save the game puzzles
# puzzles_df.to_csv("data\chess_puzzles\chess_puzzle.csv", index=False)
# # stop chess engine
engine.quit()
