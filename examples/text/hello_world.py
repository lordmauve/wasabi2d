from wasabi2d import Scene, clock, run


scene = Scene()


x = scene.width / 2
labels = [
    scene.layers[0].add_label("Hello", pos=(x, 200)),
    scene.layers[0].add_label("World", pos=(x, 300)),
    scene.layers[0].add_label("", pos=(x, 400)),
]


def rotate():
    """Rotate the text strings between the labels."""
    texts = [l.text for l in labels]
    texts.insert(0, texts.pop())
    for l, t in zip(labels, texts):
        l.text = t


clock.schedule_interval(rotate, 0.4)

run()
