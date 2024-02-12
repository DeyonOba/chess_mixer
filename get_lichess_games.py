import berserk
import json
import argparse
import sys
import os
"""Download players N most current Lichess games.
"""
def set_args():
    """Download Lichess games using command line arguments provided.
    """
    parser = argparse.ArgumentParser(description=set_args.__doc__)

    parser.add_argument(
        "--token_path",
        type=str,
        help="Relative or Abosolute path to json file contain lichess API token."
        )
    parser.add_argument(
        "--username",
        type=str,
        help="Lichess username"
    )
    parser.add_argument(
        "-n",
        type=int,
        help="Number of games to be downloaded."
    )

    args = parser.parse_args()

    if not all([args.token_path, args.username, args.n]):
        parser.print_help()
        parser.exit(1, "\nAdd all required command line arguments.\n")

    return args

def download_games():
    args = set_args()

    if not os.path.isfile(args.token_path):
        print("Token file not found. Please provide a valid path.",
              file=sys.stderr)
        return
  
    with open(args.token_path) as file:
        token = json.load(file)

    session = berserk.TokenSession(token.get("LICHESS_API_TOKEN"))
    client = berserk.Client(session)

    try:
        games_iterator = client.games.export_by_player(
            args.username,
            max=args.n,
            pgn_in_json=True
        )

        games_list = list(games_iterator)

        # Create a directory to store the downloaded games if it doesn't exist
        os.makedirs("./games_data", exist_ok=True)

        for game_info in games_list:
            fullid = game_info.get("fullId")
            filename = f"lichess_{fullid}.pgn"
            filepath = os.path.join("./games_data", filename)
            with open(filepath, "w") as file:
                file.write(game_info.get("pgn"))
        print(f"{args.n} games downloded and saved in the './games_data' directory")
    except berserk.exceptions.BerserkError as e:
        print(f"Error downloading files: {e}", file=sys.stderr)

if __name__ == "__main__":
    download_games()