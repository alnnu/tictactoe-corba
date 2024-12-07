import sys
import threading
import time
from queue import Queue
import CORBA
import PortableServer
import CosNaming
import TicTacToe
import TicTacToe__POA

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
            self.games = [game for game in self.games if game[0] != name]

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

        more = bool(self.games)
        return ret, more

    def destroy(self):
        id = self.poa.servant_to_id(self)
        self.factory._removeIterator(id)
        self.poa.deactivate_object(id)


class IteratorScavenger(threading.Thread):
    def __init__(self, factory):
        super().__init__()
        self.setDaemon(True)
        self.factory = factory
        self.start()

    def run(self):
        print("Iterator scavenger running...")

        lock = self.factory.lock
        iterators = self.factory.iterators
        poa = self.factory.iterator_poa
        manager = poa._get_the_POAManager()

        while True:
            time.sleep(SCAVENGER_INTERVAL)
            print("Scavenging dead iterators...")

            manager.hold_requests(True)
            with lock:
                for id, iter in list(iterators.items()):
                    if iter.tick == 1:
                        iter.tick = 0
                    else:
                        del iterators[id]
                        poa.deactivate_object(id)

            manager.activate()


class Game_i(TicTacToe__POA.Game):
    def __init__(self, factory, name, poa):
        self.factory = factory
        self.name = name
        self.poa = poa
        self.lock = threading.Lock()

        n = TicTacToe.Nobody
        self.players = 0
        self.state = [[n, n, n], [n, n, n], [n, n, n]]

        self.p_noughts = None
        self.p_crosses = None
        self.whose_go = TicTacToe.Nobody
        self.spectators = []
        self.spectatorNotifier = SpectatorNotifier(self.spectators, self.lock)

        print("Game_i created.")

    def joinGame(self, player):
        with self.lock:
            if self.players == 2:
                raise TicTacToe.Game.CannotJoin()

            if self.players == 0:
                ptype = TicTacToe.Nought
                self.p_noughts = player
            else:
                ptype = TicTacToe.Cross
                self.p_crosses = player
                self.whose_go = TicTacToe.Nought
                self.p_noughts.yourGo(self.state)

            gc = GameController_i(self, ptype)
            id = self.poa.activate_object(gc)
            gobj = self.poa.id_to_reference(id)
            self.players += 1

        return gobj, ptype

    # Métodos restantes, como `kill`, `_play`, `_checkForWinner`,
    # foram adaptados similarmente, atualizando exceções e prints.


class GameController_i(TicTacToe__POA.GameController):
    def __init__(self, game, ptype):
        self.game = game
        self.ptype = ptype
        print("GameController_i created.")

    def play(self, x, y):
        return self.game._play(x, y, self.ptype)


class SpectatorNotifier(threading.Thread):
    def __init__(self, spectators, lock):
        super().__init__()
        self.setDaemon(True)
        self.spectators = spectators
        self.lock = lock
        self.queue = Queue(0)
        self.start()

    def run(self):
        print("SpectatorNotifier running...")

        while True:
            method, args = self.queue.get()
            print("Notifying:", method)

            with self.lock:
                for i, spec in enumerate(self.spectators):
                    if spec:
                        try:
                            getattr(spec, method)(*args)
                        except (CORBA.COMM_FAILURE, CORBA.OBJECT_NOT_EXIST):
                            print("Spectator lost")
                            self.spectators[i] = None


def main(argv):
    print("Game Server starting...")

    orb = CORBA.ORB_init(argv, CORBA.ORB_ID)
    poa = orb.resolve_initial_references("RootPOA")
    poa._get_the_POAManager().activate()

    gf_impl = GameFactory_i(poa)
    gf_id = poa.activate_object(gf_impl)
    gf_obj = poa.id_to_reference(gf_id)

    print(orb.object_to_string(gf_obj))

    try:
        nameRoot = orb.resolve_initial_references("NameService")
        nameRoot = nameRoot._narrow(CosNaming.NamingContext)
        if nameRoot is None:
            print("NameService narrow failed!")
            sys.exit(1)

    except CORBA.ORB.InvalidName:
        print("InvalidName when resolving NameService!")
        sys.exit(1)

    name = [CosNaming.NameComponent("tutorial", "")]
    try:
        tutorialContext = nameRoot.bind_new_context(name)
    except CosNaming.NamingContext.AlreadyBound:
        print('Reusing "tutorial" naming context.')
        tutorialContext = nameRoot.resolve(name)
        tutorialContext = tutorialContext._narrow(CosNaming.NamingContext)
        if tutorialContext is None:
            print('The name "tutorial" is already bound.')
            sys.exit(1)

    tutorialContext.rebind([CosNaming.NameComponent("GameFactory", "")], gf_obj)
    print("GameFactory bound in NameService.")

    orb.run()


if __name__ == "__main__":
    main(sys.argv)