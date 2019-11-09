Sound and Music
===============

Sounds
------

wasabi2d can load sounds in ``.wav`` and ``.ogg`` formats. WAV is great for
small sound effects, while OGG is a compressed format that is more suited to
music. You can find free .ogg and .wav files online that can be used in your
game.

We need to ensure a sounds directory is set up. If your project contains the
following files::

    drum_kit.py
    sounds/drum.wav

Then ``drum_kit.py`` could play the drum sound whenever the mouse is clicked
with this code::

    def on_mouse_down():
        sounds.drum.play()

Each loaded sound is a Pygame ``Sound``, and has various methods to play and
stop the sound as well as query its length in seconds:

.. class:: Sound

    .. method:: play()

        Play the sound.

    .. method:: play(loops)

        Play the sound, but loop it a number of times.

        :param loops: The number of times to loop. If you pass ``-1`` as the
                      number of times to loop, the sound will loop forever (or
                      until you call :meth:`.Sound.stop()`

    .. method:: stop()

        Stop playing the sound.

    .. method:: get_length()

        Get the duration of the sound in seconds.

You should avoid using the ``sounds`` object to play longer pieces of music.
Because the sounds sytem will fully load the music into memory before playing
it, this can use a lot of memory, as well as introducing a delay while the
music is loaded.

.. _music:

Music
-----

.. warning::

    The music API is experimental and may be subject to cross-platform
    portability issues.

    In particular:

    * MP3 may not be available on some Linux distributions.
    * Some OGG Vorbis files seem to hang Pygame with 100% CPU.

    In the case of the latter issue, the problem may be fixed by re-encoding
    (possibly with a different encoder).


A built-in object called ``music`` provides access to play music from within
a ``music/`` directory (alongside your ``images/`` and ``sounds/`` directories,
if you have them). The music system will load the track a little bit at a time
while the music plays, avoiding the problems with using ``sounds`` to play
longer tracks.

Another difference to the sounds system is that only one music track can be
playing at a time. If you play a different track, the previously playing track
will be stopped.


.. function:: music.play(name)

    Play a music track from the given file. The track will loop indefinitely.

    This replaces the currently playing track and cancels any tracks previously
    queued with ``queue()``.

    You do not need to include the extension in the track name; for example, to
    play the file ``handel.mp3`` on a loop::

        music.play('handel')

.. function:: music.play_once(name)

    Similar to ``play()``, but the music will stop after playing through once.

.. function:: music.queue(name)

    Similar to ``play_once()``, but instead of stopping the current music, the
    track will be queued to play after the current track finishes (or after
    any other previously queued tracks).

.. function:: music.stop()

    Stop the music.

.. function:: music.pause()

    Pause the music temporarily. It can be resumed by calling
    ``unpause()``.

.. function:: music.unpause()

    Unpause the music.

.. function:: music.is_playing()

    Returns True if the music is playing (and is not paused), False otherwise.

.. function:: music.fadeout(duration)

    Fade out and eventually stop the current music playback.

    :param duration: The duration in seconds over which the sound will be faded
                    out. For example, to fade out over half a second, call
                    ``music.fadeout(0.5)``.

.. function:: music.set_volume(volume)

    Set the volume of the music system.

    This takes a number between 0 (meaning silent) and 1 (meaning full volume).

.. function:: music.get_volume()

    Get the current volume of the music system.


If you have started a music track playing using :func:`music.play_once()`, you
can use the :func:`on_music_end() hook <on_music_end>` to do something when the
music ends - for example, to pick another track at random.


Tone Generator
--------------

Wasabi2D can play tones using a built-in synthesizer.

.. function:: tone.play(pitch, duration, *, waveform='sin', volume=1.0)

    Play a note at the given pitch for the given duration.

    Duration is in seconds.

    The `pitch` can be specified as a number in which case it is the frequency
    of the note in hertz.

    Waveform is a string - either 'sin', 'square', or 'saw'.

    Alternatively, the pitch can be specified as a string representing a note
    name and octave. For example:

    * ``'E4'`` would be E in octave 4.
    * ``'A#5'`` would be A-sharp in octave 5.
    * ``'Bb3'`` would be B-flat in octave 3.

Creating notes, particularly long notes, takes time - up to several
milliseconds. You can create your notes ahead of time so that this doesn't slow
your game down while it is running:

.. function:: tone.create(pitch, duration *, waveform='sin', volume=1.0)

    Create and return a Sound object.

    The arguments are as for play(), above.

This could be used in a Wasabi2D program like this::

    beep = tone.create('A3', 0.5)

    def on_mouse_down():
        beep.play()
