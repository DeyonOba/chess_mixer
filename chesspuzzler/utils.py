#!/usr/bin/env python3

"""Manages download and storage of lichess games based on game id or user API token"""

import os
import sys
import requests
# from chesspuzzler.constants import ENGINE_PATH, API_TOKEN_PATH
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
        os.makedirs(parent_dir, exist_ok=True)

        file_name = f'lichess_{game_id}.pgn'
        file_path = os.path.join(parent_dir, file_name)

        with open(file_path, mode="w") as file:
            file.writelines(file_object.content.decode())
        
        # check if the pgn file contains useful information about games
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
        else:
            FileManger.__game_id = input("Enter game id:")


class GameDownloader(FileManger):
    """Download lichess game

    Attributes:
        is_token(bool, optional): How the game is to be downloader
            if true then .json file location should be provided.
            if false then game id is to be provided.
    """

    def __init__(self, is_token=False):
        super().__init__()
        self.is_token = is_token
        self.game_id = ""

    def get_lichess_game(self):
        if self.is_token:
            # self.token = FileManager.get_token(token_path)
            # self.get_game_via_api(self.token)
            pass
        else:
            self.set_game_id()
    
    def get_game_via_api(self):
        pass

    def get_game_via_gameid(self, game_id="") -> bool:
        if game_id:
            self.game_id = game_id
            LICHESS_SITE = "https://lichess.org/"
            TASK = "game/export/"
            url = LICHESS_SITE + TASK + game_id
            r = requests.get(url)
            
            if r.status_code == 200:
                self.save_url_game_content(r, self.game_id)
            else:
                print("Invalid game id from Lichess....", file=sys.stderr)
                return False
            return True
        else:
            self.set_game_id()
        return False
    
    def set_game_id(self):
        self.game_id = input("Enter Game id: ")
        if self.game_id:
            self.get_game_via_gameid(self.game_id)
        else:
            print("Enter valid game id from Lichess....", file=sys.stderr)
        