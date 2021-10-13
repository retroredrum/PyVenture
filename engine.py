import re
import random

from content import *

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def mainGame():
    startRoomId = 7
    curRoomId = startRoomId
    commandInput = ""

    def exits():
        exitsList = str(curRoomDesc[curRoomId][1][0::2]).strip("[]")
        print('Possible exits are ' + bcolors.RED + exitsList + bcolors.ENDC)   # prints the exits available

    def look():
        print(curRoomDesc[curRoomId][2])                                        # prints the current room description field from list
        if curRoomDesc[curRoomId][3]["object"] == "":
            print('')
        else:
            roomItem = curRoomDesc[curRoomId][3]["object"]                      # checks if there's an object in the room
            print('You see a ' + bcolors.OKGREEN + roomItem + bcolors.ENDC)     # prints the object
        exits()
        
    def inv():
        print('You are carrying: ')
        if not inventory:                                                       # checks if inventory array is empty
            print("Nothing")
        else:                                                                   # if not empty, display array items
            for x in inventory:
                print(bcolors.OKGREEN + x + bcolors.ENDC)

    def get():                                                                  # TBD - Add action check from dictionnary
        pickedUpObject = commandInputSplit[1]                                   # splits input to get object name
        if curRoomDesc[curRoomId][3]["object"] == "":                           # checks if object is in the current room
            print("There's no " + pickedUpObject + " here")
            if inventory.count(pickedUpObject) == 1:                            # checks if object is in inventory
                print("It's already in your inventory!")
        else:
            print("You take: " + curRoomDesc[curRoomId][3]["object"])
            inventory.append(curRoomDesc[curRoomId][3]["object"])               # adds object to inventory
            curRoomDesc[curRoomId][3]["object"] = ""                            # removes object from room

    def use():                                                                  # TBD - Add action check from dictionnary
        try:
            usedObject = commandInputSplit[1]                                   # object to be used
            if usedObject in inventory:                                         # checks if object is in inventory
                if usedObject in curRoomActions[curRoomId]:                     # checks if object can be used in that room
                    inventory.pop(inventory.index(usedObject))                  # removes the object from inventory when used
                    roomUpdate()
                else:
                    errormessage()
            else:
                print("You don't have a " + usedObject + " in your inventory")
        except IndexError:
            print('Use what exactly?')                                          # error message is no second word is typed in

    def push():                                                                 # WIP
        try:
            curRoomPush = curRoomDesc[curRoomId][3]["push"]                     # get current room action
            pushedUpObject = commandInputSplit[1]                               # splits input to get pushed object name
            if curRoomPush == pushedUpObject:
                roomUpdate()
            else:
                print("There's no " + pushedUpObject + " to push here.")
        except IndexError:
            print('Push what exactly?')                                         # error message is no second word is typed in

    def examine():
        print(curRoomDesc[curRoomId][3]["examine"])

    def inputerror():
        print("You can't do that. Use two words maximum. Available commands are: " + verbslist)

    def errormessage():
        error = random.choice(errorMessage)
        print(error)

    def roomUpdate():
        curRoomActions[curRoomId][4] = True
        curRoomDesc[curRoomId][1].append(curRoomActions[curRoomId][5][0])       # copies the new direction string to the room description
        curRoomDesc[curRoomId][1].append(curRoomActions[curRoomId][5][1])       # copies the new direction id to the room description
        curRoomDesc[curRoomId][2] = curRoomActions[curRoomId][3]                # replace the original description with the updated one
        print(curRoomActions[curRoomId][2])                                     # prints the object action description
        exits()

    print(welcomeMessage)
    look()

    while commandInput != 'quit':
        commandInput = input(bcolors.WARNING + 'What now? ' + bcolors.ENDC).lower()
        commandInputSplit = re.findall(r'\w+', commandInput)                    # breaks down input into an array
        verbslist = str(verbs).strip('[]')                                      # gets verbs list and strips it

        if commandInputSplit[0] not in verbs or len(commandInputSplit) > 2:     # checks input validity
            if commandInputSplit == '\n':
                break  
            else:
                inputerror()
        else:
            if commandInputSplit[0] == 'inv':                                   # inventory
                inv()
            elif commandInputSplit[0] == 'look':                                # look around -- WIP
                look()
            elif commandInputSplit[0] == 'get':                                 # pickup objects -- WIP
                get()
            elif commandInputSplit[0] == 'use':                                 # use objects in inventory -- WIP
                use()
            elif commandInputSplit[0] == 'push':                                # push objects in the world -- WIP
                push()
            elif commandInputSplit[0] == 'examine':                             # examine objects in the world -- WIP
                examine()
            elif commandInputSplit[0] in directions:                            # check if one of the directions has been typed -- WIP
                if commandInputSplit[0] in curRoomDesc[curRoomId][1]:           # check if the type direction is in exits list
                    dirIndex = curRoomDesc[curRoomId][1].index(commandInputSplit[0]) + 1
                    nextRoomId = curRoomDesc[curRoomId][1][dirIndex]
                    curRoomId = nextRoomId
                    exitsList = str(curRoomDesc[curRoomId][1][0::2]).strip("[]")
                    look()
                else:
                    print("You can't go that way!")
                    exits()
            elif commandInputSplit == 'quit':
                break
