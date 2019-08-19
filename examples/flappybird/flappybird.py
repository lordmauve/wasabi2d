import random
from wasabi2d import Scene, run, event, Storage, Vector2


scene = Scene(
    width=400,
    height=708,
    title='Flappy Bird',
)
storage = Storage()
storage.setdefault('highscore', 0)


# These constants control the difficulty of the game
GAP = 130
GRAVITY = 0.3
FLAP_STRENGTH = 6.5
SPEED = 3


score_label = scene.layers[5].add_label(
    "0",
    font='roboto_regular',
    color='white',
    pos=(scene.width / 2, 80),
    align='middle',
    fontsize=70,
)


class Bird:
    dead = False
    _score = 0
    vy = 0

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, s):
        self._score = s
        score_label.text = str(s)


bird = Bird()


scene.layers[-2].add_sprite('background', pos=(scene.width / 2, scene.height / 2))

bird.sprite = scene.layers[0].add_sprite('bird1', pos=(75, 200))


class Pipes:
    def __init__(self):
        self.top = scene.layers[-1].add_sprite('top', anchor=('left', 'bottom'))
        self.bottom = scene.layers[-1].add_sprite('bottom', anchor=('left', 'top'))
        self.x = scene.width
        self.w = self.top.width
        self.gap = 0
        self.pipe_h = self.top.height

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, x):
        self._x = x
        self.top.x = x
        self.bottom.x = x

    def set_gap(self, y):
        self.gap = y
        self.top.y = y - GAP // 2 - self.pipe_h / 2
        self.bottom.y = y + GAP // 2 + self.pipe_h / 2


pipes = Pipes()
highscore_label = scene.layers[5].add_label(
    "Best: {}".format(storage['highscore']),
    font='roboto_regular',
    color=(200, 170, 0),
    pos=(scene.width / 2, scene.height - 10),
    fontsize=30,
)


def reset_pipes():
    pipes.set_gap(random.randint(200, scene.height - 200))
    pipes.x = scene.width + pipes.w


reset_pipes()  # Set initial pipe positions.


def update_pipes():
    pipes.x -= SPEED

    if pipes.x < -0.5 * pipes.w:
        reset_pipes()
        if not bird.dead:
            bird.score += 1
            if bird.score > storage['highscore']:
                storage['highscore'] = bird.score
                highscore_label.text = f"Best: {bird.score}"


def update_bird():
    uy = bird.vy
    bird.vy += GRAVITY
    y = bird.sprite.y = bird.sprite.y + (uy + bird.vy) / 2

    if not bird.dead:
        if bird.vy < -3:
            bird.sprite.image = 'bird2'
        else:
            bird.sprite.image = 'bird1'

    px = pipes.x
    pipes_left = px - pipes.w / 2
    pipes_right = px + pipes.w / 2
    if pipes_left < bird.sprite.x < pipes_right \
            and not pipes.gap - GAP // 2 < y < pipes.gap + GAP // 2:
        bird.dead = True
        bird.sprite.image = 'birddead'

    if not 0 < bird.sprite.y < 720:
        bird.sprite.y = 200
        bird.dead = False
        bird.score = 0
        bird.vy = 0
        reset_pipes()


@event
def update():
    update_pipes()
    update_bird()


@event
def on_key_down():
    if not bird.dead:
        bird.vy = -FLAP_STRENGTH


run()
