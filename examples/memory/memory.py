#
# TODO: Add sound effects
#       Ignore clicks after displaying second card until
#       either hit or miss is reported.
#       Consider re-casting the data structure as a dict
#       with two-element tuple keys.
#       Configure window size according to COLS and ROWS
#
from wasabi2d.actor import Actor
from wasabi2d import Scene, run, event, mouse, clock, animate

import random
import time

scene = Scene(
    width=800,
    height=600,
    title='Memory',
)
scene.background = (1, 1, 1)

COLS = 4
ROWS= 3
IMSIZE = 200
STATUS = []        # cells that have been clicked on
ignore = []        # cells that have been matches and are no longer in play

# Create two of each card image, then randomize before creating the board
START_IMAGES= [ "im"+str(i+1) for i in range(COLS*ROWS//2)]*2
random.shuffle(START_IMAGES)

STATUS=[]

class Card(Actor):

    def __init__( self, title, *args, **kwargs ):
        self.title = title
        card_back = scene.layers[1].add_sprite('card_back')
        super().__init__( card_back, *args, **kwargs )

    def flip(self):
        if self.prim.image == 'card_back':
            self.prim.image = self.title
        elif self.prim.image == 'checkmark':
            pass
        else:
            self.prim.image = 'card_back'

    def complete(self):
        self.prim.image = 'checkmark'



board = []                    # initialize the board
for row in range(ROWS):
    new_row=[]
    for col in range(COLS):
        image_name = START_IMAGES.pop()
        temp = Card(image_name)
        angle = temp.prim.angle = random.uniform(-1, 1)
        animate(
            temp, 
            duration=0.3,
            topleft=(col * IMSIZE, row * IMSIZE)
        )
        animate(
            temp.prim, 
            duration=0.3,
            angle=0.1 * angle,
        )
        new_row.append(temp)
    board.append(new_row)


def findTile(pos):
    y, x = pos
    result = x // IMSIZE , y // IMSIZE
    return result


def showTile():
    pass


@event
def on_mouse_down(pos, button):
    if len(STATUS) == 2: # ignore until timeout redisplays
        return
    if pos in ignore: # has already been matched
        return
    if button == mouse.LEFT and (pos):
    # not sure why "and (pos)" - especially the parens!
        coords = findTile(pos)
        board[coords[0]][coords[1]].flip()
        if coords not in STATUS:
            STATUS.append(coords) # now they are

            if len(STATUS) == 1:  # 1st click - turn not yet over
                pass
            elif len(STATUS) == 2: # 2nd click - check for match
                (x1, y1), (x2, y2) = STATUS # an "unpacking assignment"
                if board[x1][y1].title == board[x2][y2].title:
                    print("Success sound")
                    # add cards to list of non-clickable positions
                    for pos in STATUS:
                        ignore.append(pos)
                        board[pos[0]][pos[1]].complete()
                    del STATUS[:]
                else:
                    print("Failure sound")
                    clock.schedule_unique(next_turn, 2.0)


def next_turn():
    # hide cards after a timeout
    for pos in STATUS:
        board[pos[0]][pos[1]].flip()
    del STATUS[:]


run()
