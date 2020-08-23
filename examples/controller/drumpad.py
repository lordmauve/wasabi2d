import wasabi2d as w2d
from wasabi2d.color import darker
from pygame.joystick import Joystick

scene = w2d.Scene(1280, 720, fullscreen=False)

step = scene.width / 5
mid = scene.height / 2
center = scene.width / 2, mid

colors = [
    'cyan', 'green', 'red', 'yellow', 'silver'
]

particles = scene.layers[0].add_particle_group(
    max_age=2,
    drag=0.5,
)
particles.add_color_stop(0, (1, 1, 1, 1))
particles.add_color_stop(2, (1, 1, 1, 0))

sounds = [
    w2d.sounds.cymbal,
    w2d.sounds.snare1,
    w2d.sounds.snare2,
    w2d.sounds.hihat,
    w2d.sounds.kick,
]

SMALL = scene.height / 10
BIG = step / 2

params = dict(
    radius=SMALL,
#    fill=False,
#    stroke_width=3,
)

pads = [
    scene.layers[0].add_circle(**params, pos=(3 * step, mid), color=darker('cyan')),
    scene.layers[0].add_circle(**params, pos=(4 * step, mid), color=darker('green')),
    scene.layers[0].add_circle(**params, pos=(1 * step, mid), color=darker('red')),
    scene.layers[0].add_circle(**params, pos=(2 * step, mid), color=darker('yellow')),
    scene.layers[-1].add_circle(radius=mid, pos=center, color='black')
]


pad = None


@w2d.event
def on_joystick_attached(device_index):
    global pad
    if pad is None:
        pad = Joystick(device_index)


@w2d.event
def on_joystick_detached(instance_id):
    global pad
    if pad and instance_id == pad.get_instance_id():
        pad.quit()
        pad = None


@w2d.event
def on_joybutton_down(button):
    if button in range(4):
        pad = pads[button]
        pad.radius = BIG
        pad.color = colors[button]

        w2d.animate(
            pad,
            duration=0.1,
            radius=SMALL,
            color=darker(pad.color)
        )

        particles.emit(100,
            pos=pad.pos,
            pos_spread=SMALL,
            vel_spread=300,
            color=pad.color,
        )
    elif button == 4:
        pad = pads[button]
        pad.radius = mid
        pad.color = (0.8, 0.8, 0.8, 1.0)
        w2d.animate(
            pad,
            radius=mid / 2,
            duration=0.3,
            color=(0, 0, 0, 1.0)
        )
        particles.emit(100,
            pos=pad.pos,
            pos_spread=100,
            vel_spread=400,
            color=(1, 1, 1, 1.0),
        )

    if 0 <= button <= 4:
        sounds[button].play()


w2d.run()
