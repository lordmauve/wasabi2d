# Layers, Groups and Shaders

Some thoughts on how layers and shaders for `wasabi2d` could interact.

You can already create layers, which are used for draw ordering:


```python
t = scene.layers[1].add_text(...)  # Guaranteed to draw after s
s = scene.layers[0].add_sprite(...)
```

# Groups

Another organisational structure that I think should be in the API is a
`Group`, which really exists solely to apply transforms.

As such it is effectively outside of the layers system, and can group together
objects in different layers.

```python
group = Group([t, s])
group.angle += 0.75

t.delete()  # deletes from layer and group
```

This API presents a couple of minor problems:

* It offers the opportunity for an object to be put into more than one group,
  which would have to be rejected.
* What happens when we delete a group? Does this delete the objects inside?
  More generally, what is the object ownership model? Objects were created via
  layers and so outwardly it is definitely the layers that own them.

Overall, this is a nice, useful concept that really doesn't need to cross
inside the layers system any further.

One idea I did have was to cull based on groups, by computing the union of
object bounds and testing the whole group together.


# Layer draw modes

What if we want to use additive or multiplicative blending?

This doesn't feel like a primitive level operation, and we've already discarded
Groups as being just about transformations. It makes sense to me that this
would be a layer operation, eg.

```
scene.layers[1].draw_mode = 'add'
scene.layers[2].draw_mode = 'multiply'
```

NB. this affects every primitive individually in the layer; this isn't about
how the whole layer blends. Maybe this needs to be clarified.


# Post-processing Shaders

Something that I think could play into the concept of layers is post-processing
shaders.

I would like to ensure wasabi2d includes a few cool post-processing effects.
Some ideas:

* Drop shadow
* Blur/glow
* Vignette (actually this one is more of a whole-scene effect?)
* Color matrix (black and white, invert, etc)

If draw modes are layer operations, perhaps shaders should be also?

```
scene.layer[1].set_shader('drop-shadow', blur=5)
```

This is super convenient in the simple case.

But then the shader is only affecting only affecting one layer, and one layer
does not offer ordering guarantees. How do we ensure that we can define the
draw order for objects that are being affected by one shader?

Maybe some system of sub-layers:

```
scene.layer[1].set_shader('drop_shadow')
t = scene.layers[1, 1].add_text(...)  # Guaranteed to draw after s
s = scene.layers[1, 0].add_sprite(...)
```

But an object containing both objects and sub-layers gives an ordering problem.
Perhaps we can assume `0` is the default sublayer, ie. `scene.layers[1, 0] is
scene.layers[1]`.


Sub-layers raise the prospect of sub-shaders:

```
scene.layer[1].set_shader('drop_shadow')
scene.layers[1, 1].set_shader('invert')
```

... to be continued
