import re
import random

from content import *

def mainGame():
    startRoomId = 5
    curRoomId = startRoomId
    commandInput = ""
    exitsList = str(curRoomDesc[curRoomId][1][0::2]).strip("[]")

    def look():
        print(curRoomDesc[curRoomId][2])    # prints the current room description field from list
        try:
            roomItem = curRoomDesc[curRoomId][3]    # checks if there's an object in the room
            print('You see a ' + roomItem)          # prints the object
        except IndexError:
            print('You see nothing interesting here.')
        print('Possible exits are ' + exitsList)    # prints the exits available

    def inv():
        print('You are carrying: ')
        if not inventory:  # checks if inventory array is empty
            print("Nothing")
        else:  # if not empty, display array items
            for x in inventory:
                print(x)

    def get():
        pickedUpObject = commandInputSplit[1]  # splits input to get object name
        if curRoomDesc[curRoomId].count(pickedUpObject) == 0:  # checks if object is in the current room
            print("There's no " + pickedUpObject + " here")
            if inventory.count(pickedUpObject) == 1:  # checks if object is in inventory
                print("It's already in your inventory!")
        else:
            print("OK")
            inventory.append(pickedUpObject)  # adds object to inventory
            pickedUpObjectIndex = curRoomDesc[curRoomId].index(pickedUpObject)  # gets object index in room array
            curRoomDesc[curRoomId].pop(pickedUpObjectIndex)  # removes object from room

    def use():
        usedObject = commandInputSplit[1]   # object to be used
        try:
            if usedObject in inventory:     # checks if object is in inventory
                if usedObject in curRoomActions[curRoomId]:  # checks if object can be used in that room
                    print(curRoomActions[curRoomId][3])     # prints the object action description
                    inventory.pop(inventory.index(usedObject))      # removes the object from inventory when used
            else:
                print("You don't have a " + usedObject + " in your inventory")
        except IndexError:
            errormessage()

    def inputerror():
        print("Can't do that, two words maximum: " + verbslist)

    def errormessage():
        error = random.choice(errorMessage)
        print(error)

    print('Welcome to the haunted house.')
    look()

    while commandInput != 'quit':
        commandInput = input('What now? ').lower()
        commandInputSplit = re.findall(r'\w+', commandInput)                    # breaks down input into an array
        verbslist = str(verbs).strip('[]')                                      # gets verbs list and strips it
        exitsList = str(curRoomDesc[curRoomId][1][0::2]).strip("[]")

        if commandInputSplit[0] not in verbs or len(commandInputSplit) > 2:     # checks input validity
            inputerror()
        else:
            if commandInputSplit[0] == 'inv':                                   # inventory
                inv()
            elif commandInputSplit[0] == 'look':                                # look around -- WIP
                look()
            elif commandInputSplit[0] == 'get':                                 # pickup objects -- WIP
                get()
            elif commandInputSplit[0] == 'use':
                use()
            elif commandInputSplit[0] in directions:                            # check if one of the directions has been typed
                if commandInputSplit[0] in curRoomDesc[curRoomId][1]:           # check if the type direction is in exits list
                    dirIndex = curRoomDesc[curRoomId][1].index(commandInputSplit[0]) + 1
                    nextRoomId = curRoomDesc[curRoomId][1][dirIndex]
                    curRoomId = nextRoomId
                    exitsList = str(curRoomDesc[curRoomId][1][0::2]).strip("[]")
                    look()
                else:
                    print("You can't go that way!")
                    print('Possible exits are ' + exitsList)
            elif commandInputSplit == 'quit':
                break
