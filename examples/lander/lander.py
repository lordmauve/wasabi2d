"""Pi Lander

 * A basic Lunar Lander style game in Pygame Zero
 * Run with 'pgzrun pi_lander.py', control with the LEFT, RIGHT and UP arrow
   keys
 * Original Author Tim Martin: www.Tim-Martin.co.uk
 * Ported to Wasabi2D by Daniel Pope
 * Licence: Creative Commons Attribution-ShareAlike 4.0 International
 * http://creativecommons.org/licenses/by-sa/4.0/

"""
import random
import math
from wasabi2d import Scene, event, run, clock, keys, Vector2


WIDTH = 1600  # Screen width
HEIGHT = 1200  # Screen height

# Landscape is broken down into steps. Define number of pixels on the x axis
# per step.
STEP_SIZE = 12

scene = Scene(
    WIDTH,
    HEIGHT,
    antialias=4,
    title="Lunar Lander",
)


class LandingSpot:
    """A flat pad where it is safe for the player to land.

    Each instance defines a landing spot by where it starts, how big it is and
    how many points it's worth.
    """

    landing_spot_sizes = ["small", "medium", "large"]

    def __init__(self, starting_step):
        self.starting = starting_step
        random_size = random.choice(
            LandingSpot.landing_spot_sizes
        )  # And randomly choose size
        if random_size == "small":
            self.size = 4
            self.bonus = 8
        elif random_size == "medium":
            self.size = 10
            self.bonus = 4
        else:  # Large
            self.size = 20
            self.bonus = 2

        self.px_width = (self.size - 1) * STEP_SIZE
        self.px_x = self.starting * STEP_SIZE + self.px_width / 2
        self.px_y = 0  # updated when we generate the landscape

    def get_within_landing_spot(self, step):
        if (step >= self.starting) and (step < self.starting + self.size):
            return True
        return False


class Landscape:
    """ Stores and generates the landscape, landing spots and star field """


    world_steps = int(
        WIDTH / STEP_SIZE
    )  # How many steps can we fit horizontally on the screen
    SMALL_HEIGHT_CHANGE = 6  # Controls how bumpy the landscape is
    LARGE_HEIGHT_CHANGE = 20  # Controls how steep the landscape is
    FEATURES = ["mountain", "valley", "field"]  # What features to generate
    N_STARS = 100  # How many stars to put in the background
    n_spots = 4  # Max number of landing spots to generate

    # the boundary of starting landscape height, dependent on screen height
    MIN_START_Y = int(0.5 * HEIGHT)
    MAX_START_Y = int(0.83 * HEIGHT)

    MOUNTAIN_START_THRESHOLD = int(0.95 * HEIGHT)
    VALLEY_START_THRESHOLD = int(0.33 * HEIGHT)

    def __init__(self):
        self.world_height = []  # Holds the height of the landscape at each step
        self.star_locations = []  # Holds the x and y location of the stars
        self.landing_spots = []  # Holds the landing spots

    def get_landing_spot(self, step):
        """Get the landing spot for this step."""
        for spot in self.landing_spots:
            if spot.get_within_landing_spot(step):
                return spot
        return None

    def get_within_landing_spot(self, step):
        """ Calculate if a given step is within any of the landing spots """
        return self.get_landing_spot(step) is not None

    def get_landing_spot_bonus(self, step):
        """Get the bonus if we're at a landing spot."""
        spot = self.get_landing_spot(step)
        return spot.bonus if spot else 0

    def reset(self):
        """Generates a new landscape."""
        scene.layers[-4].clear()
        scene.layers[-3].clear()
        scene.layers[-2].clear()
        scene.layers[-1].clear()
        self.generate()

    def generate(self):
        # First: Choose which steps of the landscape will be landing spots
        del self.landing_spots[:]  # Delete any previous LandingSpot objects
        next_spot_start = 0
        # Move from left to right adding new landing spots until either
        # n_spots spots have been placed or we run out of space in the world
        while (
            len(self.landing_spots) < Landscape.n_spots
            and next_spot_start < Landscape.world_steps
        ):

            # Randomly choose location to start landing spot
            next_spot_start += random.randint(10, 50)
            # Make a new landing object at this spot
            new_landing_spot = LandingSpot(next_spot_start)
            # And store it in our list
            self.landing_spots.append(new_landing_spot)

            # Then take into account its size before choosing the next
            next_spot_start += new_landing_spot.size

        # Second: Randomise the world map
        del self.world_height[:]  # Clear any previous world height data
        feature_steps = 0  # Keep track of how many steps we are into a feature

        # Start the landscape between 300 and 500 pixels down
        self.world_height.append(random.randint(Landscape.MIN_START_Y, Landscape.MAX_START_Y))
        for step in range(1, Landscape.world_steps):
            # If feature_step is zero, we need to choose a new feature and how long it goes on for
            if feature_steps == 0:
                feature_steps = random.randint(25, 75)
                current_feature = random.choice(self.FEATURES)

            current_height = self.world_height[step - 1]
            # Generate the world by setting the range of random numbers, must be flat if in a landing spot
            spot = self.get_landing_spot(step)
            if spot is not None:
                spot.px_y = current_height
                max_up = 0  # Flat
                max_down = 0  # Flat
            elif current_feature == "mountain":
                max_up = Landscape.SMALL_HEIGHT_CHANGE
                max_down = -Landscape.LARGE_HEIGHT_CHANGE
            elif current_feature == "valley":
                max_up = Landscape.LARGE_HEIGHT_CHANGE
                max_down = -Landscape.SMALL_HEIGHT_CHANGE
            elif current_feature == "field":
                max_up = Landscape.SMALL_HEIGHT_CHANGE
                max_down = -Landscape.SMALL_HEIGHT_CHANGE

            # Generate the next piece of the landscape
            next_height = current_height + random.randint(max_down, max_up)
            self.world_height.append(next_height)
            feature_steps -= 1
            # Stop mountains getting too high, or valleys too low
            if next_height > Landscape.MOUNTAIN_START_THRESHOLD:
                current_feature = "mountain"  # Too low! Force a mountain
            elif next_height < Landscape.VALLEY_START_THRESHOLD:
                current_feature = "valley"  # Too high! Force a valley

        self.horizon = scene.layers[-2].add_line(
            self.points(),
            stroke_width=3,
            color='#555555'
        )
        for spot in self.landing_spots:
            scene.layers[-1].add_rect(
                pos=(spot.px_x, spot.px_y),
                width=spot.px_width,
                height=8,
                color='yellow'
            )
            scene.layers[-3].add_label(
                f'{spot.bonus}x',
                align='center',
                pos=(spot.px_x, spot.px_y - 20),
                fontsize=40,
                color="#888800",
            )

        # Third: Randomise the star field
        del self.star_locations[:]
        for star in range(0, Landscape.N_STARS):
            star_step = random.randint(0, Landscape.world_steps - 1)
            star_x = star_step * STEP_SIZE
            star_y = random.randint(
                0, self.world_height[star_step]
            )  # Keep the stars above the landscape

            mag = random.random()
            star = scene.layers[-4].add_star(
                points=4,
                inner_radius=2,
                outer_radius=10,
                color=(mag,) * 3,
                pos=(star_x, star_y),
            )
            star.scale = mag
            star.angle = math.radians(45)

    def points(self):
        points = []
        for step in range(0, self.world_steps):
            x = step * STEP_SIZE
            y = self.world_height[step]
            points.append((x, y))
        return points


class Ship:
    """ Holds the state of the player's ship and handles movement """

    max_fuel = 1000  # How much fuel the player starts with
    booster_power = 0.1  # Power of the ship's thrusters
    rotate_speed = 3  # How fast the ship rotates in degrees per frame
    gravity = [0.0, 0.02]  # Strength of gravity in the x and y directions

    def __init__(self):
        """ Create the variables which will describe the players ship """
        self.angle = 0  # The angle the ship is facing 0 - 360 degrees
        self.altitude = 0  # The number of pixels the ship is above the ground
        self.booster = False  # True if the player is firing their booster
        self.fuel = 0  # Amount of fuel remaining
        self.position = [0, 0]  # The x and y coordinates of the players ship
        self.velocity = [0, 0]  # The x and y velocity of the players ship
        self.acceleration = [0, 0]  # The x and y acceleration of the players ship
        self.sprite = scene.layers[0].add_sprite('lander')
        self.particles = scene.layers[0].add_particle_group(
            max_age=1,
            grow=10,
        )
        self.particles.add_color_stop(0, (5, 0, 0, 1))
        self.particles.add_color_stop(0.2, (1.5, 1.5, 0, 1))
        self.particles.add_color_stop(0.5, 'gray')
        self.particles.add_color_stop(0.75, (5, 0, 0, 0))
        scene.layers[0].set_effect('bloom', radius=4)

    def reset(self):
        """ Set the ships position, velocity and angle to their new-game values """
        self.position = [750.0, 100.0]  # Always start at the same spot
        self.sprite.pos = self.position
        self.velocity = [
            -random.random(),
            random.random(),
        ]  # But with some initial speed
        self.acceleration = [
            0.0,
            0.0,
        ]  # No initial acceleration (except gravity of course)
        self.angle = random.randint(0, 360)  # And pointing in a random direction
        self.sprite.angle = math.radians(-self.angle)
        self.fuel = Ship.max_fuel  # Fill up fuel tanks

    def rotate(self, direction):
        """ Rotate the players ship and keep the angle within the range 0 - 360 degrees """
        if direction == "left":
            self.angle -= Ship.rotate_speed
        elif direction == "right":
            self.angle += Ship.rotate_speed
        if (
            self.angle > 360
        ):  # Remember than adding or subtracting 360 degrees does not change the angle
            self.angle -= 360
        elif self.angle < 0:
            self.angle += 360
        self.sprite.angle = math.radians(-self.angle)

    def booster_on(self):
        """ When booster is firing we accelerate in the opposite direction, 180 degrees, from the way the ship is facing """
        self.booster = True
        self.sprite.image = 'lander-thrust'

        angle_r = math.radians(self.angle + 180)

        up = Vector2(math.sin(angle_r), math.cos(angle_r))

        self.acceleration[:] = Ship.booster_power * up

        self.particles.emit(
            15,
            pos=self.position - 25 * up,
            pos_spread=2,
            vel=up * -200 + Vector2(*self.velocity) * 60,
            vel_spread=50,
            spin_spread=1,
            size=1.5,
            #color='#fff0c0',
        )

        self.fuel -= 2

    def booster_off(self):
        """ When the booster is not firing we do not accelerate """
        self.sprite.image = 'lander'
        self.booster = False
        self.acceleration[0] = 0.0
        self.acceleration[1] = 0.0

    def update_physics(self):
        """ Update ship physics in X and Y, apply acceleration (and gravity) to the velocity and velocity to the position """
        for axis in range(0, 2):
            self.velocity[axis] += Ship.gravity[axis]
            self.velocity[axis] += self.acceleration[axis]
            self.position[axis] += self.velocity[axis]

        # Update player altitude. Note that STEP_SIZE * 3 is the length of the
        # ship's legs
        ship_step = int(self.position[0] / STEP_SIZE)
        if ship_step < Landscape.world_steps:
            self.altitude = (
                game.landscape.world_height[ship_step]
                - self.position[1]
                - (STEP_SIZE * 3)
            )

        self.sprite.pos = self.position

    def get_out_of_bounds(self):
        """ Check if the player has hit the ground or gone off the sides """
        return (
            self.altitude <= 0
            or self.position[0] <= 0
            or self.position[0] >= WIDTH
        )


class Game:
    """ Holds main game data, including the ship and landscape objects. Checks for game-over """

    def __init__(self):
        self.time = 0.0  # Time spent playing in seconds
        self.score = 0  # Player's score
        self.game_speed = 30  # How fast the game should run in frames per second
        self.time_elapsed = 0.0  # Time since the last frame was changed
        self.blink = True  # True if blinking text is to be shown
        self.n_frames = 0  # Number of frames processed
        self.game_on = False  # True if the game is being played
        game_label.text = "PI   LANDER\nPRESS SPACE TO START"  # Start of game message
        self.ship = Ship()  # Make a object of the Ship type
        self.landscape = Landscape()
        self.reset()  # Start the game with a fresh landscape and ship

    def reset(self):
        self.time = 0.0
        self.ship.reset()
        self.landscape.reset()

    def restart(self):
        self.reset()
        scene.layers[5].visible = False
        self.game_on = True

    def end_game(self, message):
        game_label.text = message
        scene.layers[5].visible = True
        self.game_on = False

    def check_game_over(self):
        """ Check if the game is over and update the game state if so """
        if self.ship.get_out_of_bounds() == False:
            return  # Game is not over

        self.game_on = False  # Game has finished. But did we win or loose?
        # Check if the player looses. This is if the ship's angle is > 20 degrees
        # the ship is not over a landing site, is moving too fast or is off the side of the screen
        ship_step = int(self.ship.position[0] / STEP_SIZE)
        if (
            self.ship.position[0] <= 0
            or self.ship.position[0] >= WIDTH
            or self.landscape.get_within_landing_spot(ship_step) == False
            or abs(self.ship.velocity[0]) > 1
            or abs(self.ship.velocity[1]) > 1
            or (self.ship.angle > 20 and self.ship.angle < 340)
        ):
            self.end_game(
                "YOU JUST DESTROYED A 100 MEGABUCK LANDER\n\n"
                "LOSE 250 POINTS\n\n"
                "PRESS SPACE TO RESTART"
            )
            self.score -= 250
        else:  # If the player has won! Update their score based on the amount of remaining fuel and the landing bonus
            points = self.ship.fuel / 10
            points *= self.landscape.get_landing_spot_bonus(ship_step)
            self.score += points
            self.end_game(
                "CONGRATULATIONS\nTHAT WAS A GREAT LANDING!\n\n"
                f"{round(points)} POINTS\n\nPRESS SPACE TO RESTART"
            )


game_label = scene.layers[5].add_label(
    "Press space to play",
    font='eunomia_regular',
    pos=(WIDTH / 2, HEIGHT / 5),
    align="center",
    color="green",
    fontsize=60,
)

# Create the game object
game = Game()


def toggle_spots():
    if game.game_on:
        scene.layers[-3].visible = True
    else:
        scene.layers[-3].visible ^= 1


clock.schedule_interval(toggle_spots, 0.5)

hud = scene.layers[2]

score_label = hud.add_label(
    "SCORE: " + str(round(game.score)),
    font='eunomia_regular',
    pos=(10, 55),
    fontsize=40,
)
time_label = hud.add_label(
    "TIME: " + str(round(game.time)),
    font='eunomia_regular',
    pos=(10, 95),
    fontsize=40,
)
fuel_label = hud.add_label(
    "FUEL: " + str(game.ship.fuel),
    font='eunomia_regular',
    pos=(10, 135),
    fontsize=40,
)
alt_label = hud.add_label(
    "ALTITUDE: " + str(round(game.ship.altitude)),
    font='eunomia_regular',
    pos=(WIDTH - 10, 55),
    align='right',
    fontsize=40,
)
vx_label = hud.add_label(
    "HORIZONTAL SPEED: {0:.2f}".format(game.ship.velocity[0]),
    font='eunomia_regular',
    pos=(WIDTH - 10, 95),
    align='right',
    fontsize=40,
)
vy_label = hud.add_label(
    "VERTICAL SPEED: {0:.2f}".format(-game.ship.velocity[1]),
    font='eunomia_regular',
    pos=(WIDTH - 10, 135),
    align='right',
    fontsize=40,
)


@event
def update(dt, keyboard):
    update_hud()
    update_physics(dt, keyboard)


def update_hud():
    score_label.text = f"SCORE: {round(game.score)}"
    time_label.text = f"TIME: {round(game.time)}"
    fuel_label.text = f"FUEL: {game.ship.fuel}"
    alt_label.text = f"ALTITUDE: {round(game.ship.altitude)}"

    vx, vy = game.ship.velocity
    vx_label.text = f"HORIZONTAL SPEED: {vx:.2f}"
    vy_label.text = f"VERTICAL SPEED: {-vy:.2f}"


def update_physics(dt, keyboard):
    """Updates the game physics 30 times every second."""
    game.time_elapsed += dt

    # New frame - do all the simulations
    game.n_frames += 1

    # Start the game if the player presses space when the game is not on
    if game.game_on == False:
        return

    # If the game is on, update the movement and the physics
    if keyboard.left:  # Change space ship rotation
        game.ship.rotate("left")
    elif keyboard.right:
        game.ship.rotate("right")

    if (
        keyboard.up and game.ship.fuel > 0
    ):  # Fire boosters if the player has enough fuel
        game.ship.booster_on()
    else:
        game.ship.booster_off()

    game.time += dt
    game.ship.update_physics()
    game.check_game_over()


@event
def on_key_down(key):
    if key == keys.F12:
        scene.toggle_recording()
    elif key == keys.SPACE and game.game_on == False:
        game.restart()


run()
