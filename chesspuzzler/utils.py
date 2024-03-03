#!/usr/bin/env python3

"""Handles file storage and loading"""
import os
import sys
# from chesspuzzly.constants import ENGINE_PATH, API_TOKEN_PATH
import chess.pgn


class FileManger:
    __token_path = "lichess_api_token.json"
    __game_id = ""

    def get_token(self):
        pass
    @staticmethod
    def save_url_game_content(file_object, game_id):
        # Create a directory to store the downloaded games if it doesn't exist
        parent_dir = "./data/game_data"
        os.makedirs("./data", exist_ok=True)
        os.makedirs(parent_dir, exist_ok=True)

        file_name = f'lichess_{game_id}.pgn'
        file_path = os.path.join(parent_dir, file_name)
        with open(file_path, mode="w") as file:
            file.writelines(file_object.content.decode())
        
        try:
            with open(file_path) as file:
                game = chess.pgn.read_game(file)
                if game is None:
                    print("File: {file_name} is empty", file=sys.stderr)
                    os.remove(file_path)
                else:
                    print(f"File: {file_name} has been stored in ./data/game_data")
                del game
                FileManger.set_game_id(game_id)

        except FileNotFoundError as e:
            print("Invalid file format: ", e, file=sys.stderr)

    @classmethod
    def load_pgn_game(clf, game_id):
        FileManger.set_game_id(game_id)
        file_name = f"lichess_{game_id}.pgn"
        file_path = os.path.join("data", "game_data", file_name)
        if os.path.exists(file_path):
            with open(file_path) as file:
                game = chess.pgn.read_game(file)
                if game is None:
                    print("File is empty.....", file=sys.stderr)
                else:
                    return game
        else:
            print("{} is not found.....".format(file_path), file=sys.stderr)

    @staticmethod
    def get_token(self):
        pass

    @staticmethod
    def set_game_id(game_id=""):
        if game_id:
            FileManger.__game_id = game_id
        elif not FileManger.__game_id:
            FileManger.__game_id = input("Enter game id: ")
        