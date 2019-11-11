inventory = []
directions = ['n', 'e', 's', 'w']
verbs = ['quit', 'inv', 'look', 'get', 'use', 'n', 'e', 's', 'w']

curRoomDesc = [[0, ["n", 1], "You are in a bedroom. All the windows are closed and the only exit is a door on the north wall.", "flashlight"],
               [1, ["n", 2, "w", 3, "s", 0], "You're in a dark corridor. The only window is blocked by shutters. A faint blinking light shows a door to the north and a passage to the west"],
               [2, ["s", 1], "Another bedroom. Obviously a child's room. Creepy dools are aligned on a shelf of the eastern wall. One of them is newer and cleaner", "doll"],
               [3, ["n", 4, "e", 1, "s", 5], "You're in the lobby of the house. The front door of the house is locked."],
               [4, ["n", 6, "s", 3], "You're in the Kitchen. A side door leads to the garden", "knife"],
               [5, ["n", 3], "You're in a very fancy living room. A chimney heats the cold house here", "key"],
               [6, ["s", 4, "e", 7], "You're in the garden. The grass is cut short and an old oak is the only tree. The garden extends to the south, behind the house."],
               [7, ["w", 6], "You're in the back part of the garden. A wooden kiosk is in the center."],
               [8, ["n", 9], "You're in front of the house on a path that leads north to a dark forest."]]


curRoomActions = [[0],
                  [1],
                  [2],
                  [3, "key", "The front door is now unlocked", "Lobby. The front door of the house is unlocked.", False, ["w", 8]],
                  [4],
                  [5],
                  [6],
                  [7],
                  [8]]

errorMessage = ["You can't do that here!", "That's silly", "But ... why?", "This is non-sense!", "Are you sure?"]

welcomeMessage = "Welcome to PyVenture"
