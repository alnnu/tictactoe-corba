import sys
import threading
import time
from omniORB import CORBA, PortableServer
import CosNaming
import TicTacToe, TicTacToe__POA

SCAVENGER_INTERVAL = 30


class GameFactory_i(TicTacToe__POA.GameFactory):
    def __init__(self, poa):
        self.games = []
        self.iterators = {}
        self.lock = threading.Lock()
        self.poa = poa

        self.iterator_poa = poa.create_POA("IterPOA", None, [])
        self.iterator_poa._get_the_POAManager().activate()

        self.iterator_scavenger = IteratorScavenger(self)
        print("GameFactory_i created.")

    def newGame(self, name):
        try:
            game_poa = self.poa.create_POA("Game-" + name, None, [])
        except PortableServer.POA.AdapterAlreadyExists:
            raise TicTacToe.GameFactory.NameInUse()

        gservant = Game_i(self, name, game_poa)
        gid = game_poa.activate_object(gservant)
        gobj = game_poa.id_to_reference(gid)
        game_poa._get_the_POAManager().activate()

        with self.lock:
            self.games.append((name, gservant, gobj))

        return gobj

    def listGames(self, how_many):
        with self.lock:
            front = self.games[:int(how_many)]
            rest = self.games[int(how_many):]

        ret = list(map(lambda g: TicTacToe.GameInfo(g[0], g[2]), front))

        if rest:
            iter = GameIterator_i(self, self.iterator_poa, rest)
            iid = self.iterator_poa.activate_object(iter)
            iobj = self.iterator_poa.id_to_reference(iid)
            with self.lock:
                self.iterators[iid] = iter
        else:
            iobj = None

        return ret, iobj

    def _removeGame(self, name):
        with self.lock:
            self.games = [g for g in self.games if g[0] != name]

    def _removeIterator(self, iid):
        with self.lock:
            del self.iterators[iid]


class GameIterator_i(TicTacToe__POA.GameIterator):
    def __init__(self, factory, poa, games):
        self.factory = factory
        self.poa = poa
        self.games = games
        self.tick = 1
        print("GameIterator_i created.")

    def __del__(self):
        print("GameIterator_i deleted.")

    def next_n(self, how_many):
        self.tick = 1
        front = self.games[:int(how_many)]
        self.games = self.games[int(how_many):]

        ret = list(map(lambda g: TicTacToe.GameInfo(g[0], g[2]), front))
        more = 1 if self.games else 0

        return ret, more

    def destroy(self):
        id = self.poa.servant_to_id(self)
        self.factory._removeIterator(id)
        self.poa.deactivate_object(id)


class IteratorScavenger(threading.Thread):
    def __init__(self, factory):
        super().__init__(daemon=True)
        self.factory = factory
        self.start()

    def run(self):
        print("Iterator scavenger running...")
        while True:
            time.sleep(SCAVENGER_INTERVAL)
            print("Scavenging dead iterators...")

            with self.factory.lock:
                for id, iter in list(self.factory.iterators.items()):
                    if iter.tick == 1:
                        iter.tick = 0
                    else:
                        del self.factory.iterators[id]
                        self.factory.iterator_poa.deactivate_object(id)
                        del iter


class Game_i(TicTacToe__POA.Game):
    def __init__(self, factory, name, poa):
        self.factory = factory
        self.name = name
        self.poa = poa
        self.lock = threading.Lock()
        self.state = [[TicTacToe.Nobody] * 3 for _ in range(3)]
        self.p_noughts = None
        self.p_crosses = None
        self.whose_go = TicTacToe.Nobody
        self.players = 0
        self.spectators = []
        self.spectatorNotifier = SpectatorNotifier(self.spectators, self.lock)
        print("Game_i created.")

    # Métodos restantes permanecem semelhantes, com a sintaxe corrigida