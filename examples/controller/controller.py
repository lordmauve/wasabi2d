import wasabi2d as w2d
from pygame import joystick
from pygame.math import Vector2


scene = w2d.Scene(
    width=400,
    height=600,
    background='white'
)

midline = 200

controllers = {}

LSTICK_CENTER = Vector2(-31.5, -2)
RSTICK_CENTER = Vector2(31.5, -2)

from wasabi2d.color import convert_color_rgb, darker
GREEN = convert_color_rgb('#88aa00')
RED = convert_color_rgb('#aa0000')
BLUE = convert_color_rgb('#0088aa')
YELLOW = convert_color_rgb('#d4aa00')
colors = [GREEN, RED, BLUE, YELLOW]


def create_gamepad(device_index):
    stick = joystick.Joystick(device_index)
    instance = stick.get_instance_id()
    if instance in controllers:
        print("Duplicate", instance)
        return

    group = w2d.Group(
        [
            scene.layers[0].add_sprite('gamepad_base'),
            scene.layers[0].add_sprite('stick', pos=LSTICK_CENTER),
            scene.layers[0].add_sprite('stick', pos=RSTICK_CENTER),
            scene.layers[0].add_sprite('button', pos=(72, -19)),
            scene.layers[0].add_sprite('button', pos=(89, -36)),
            scene.layers[0].add_sprite('button', pos=(56, -36)),
            scene.layers[0].add_sprite('button', pos=(72, -52)),
            scene.layers[0].add_label(
                stick.get_name(),
                pos=(0, 80),
                color='black',
                fontsize=14,
                align="center"
            )

        ],
        pos=(midline, len(controllers) * 200 + 100),
        scale=0.01
    )
    for button, color in zip(group[3:7], colors):
        button.color = darker(color)
        button.on_color = color

    w2d.animate(group, tween="out_elastic", scale=1.0)

    controllers[stick.get_instance_id()] = (
        stick,
        group
    )


joystick.init()


def organise():
    for idx, (_, (_, group)) in enumerate(controllers.items()):
        w2d.animate(group, duration=0.2, tween="decelerate", y=idx * 200 + 100)


@w2d.event
def on_joybutton_down(instance_id, button):
    _, group = controllers[instance_id]
    if button >= 4:
        return
    b = group[3 + button]
    b.color = b.on_color
    w2d.animate(b, 'out_elastic', scale=1.3)


@w2d.event
def on_joybutton_up(instance_id, button):
    _, group = controllers[instance_id]
    if button >= 4:
        return
    b = group[3 + button]
    b.color = darker(b.on_color)
    w2d.animate(b, duration=0.1, scale=1)


@w2d.event
def on_joyaxis_motion(joy, instance_id, axis, value):
    stick, group = controllers[instance_id]
    if axis in (0, 1):
        x = stick.get_axis(0)
        y = stick.get_axis(1)
        group[1].pos = LSTICK_CENTER + Vector2(x, y) * 10
    elif axis in (3, 4):
        x = stick.get_axis(3)
        y = stick.get_axis(4)
        group[2].pos = RSTICK_CENTER + Vector2(x, y) * 10
    else:
        print("axis", instance_id, axis, value)


@w2d.event
def on_joystick_attached(device_index, guid):
    create_gamepad(device_index)


@w2d.event
def on_joystick_detached(instance_id):
    try:
        stick, group = controllers.pop(instance_id)
    except KeyError:
        print("Detached", instance_id)
        return
    stick.quit()
    w2d.animate(group, duration=0.1, scale=0, on_finished=group.delete)
    organise()


w2d.run()
