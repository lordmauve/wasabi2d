from wasabi2d import Scene, run

scene = Scene(
    50,
    50,
    background="#ccaa88",
    pixel_art=False,
    scaler='nearest'
)

center = (25, 25)
scene.layers[0].add_sprite(
    'pixel_tank_base',
    pos=center,
    angle=0.4,
)
scene.layers[0].add_sprite(
    'pixel_tank_turret',
    pos=center,
    angle=-0.1,
)

run()
