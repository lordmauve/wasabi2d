import wasabi2d as w2d

scene = w2d.Scene()

PATCH = w2d.NinePatch('patch', (4, 28), (4, 28))


patch = scene.layers[0].add_ninepatch(
    PATCH,
    pos=(scene.width / 2, scene.height / 2),
    width=300,
    height=100,
)

w2d.run()
