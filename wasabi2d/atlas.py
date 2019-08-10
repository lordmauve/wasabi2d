"""Pack sprites into texture atlases."""
import numpy as np
import pygame
import rectpack


class Atlas:
    def __init__(self, ctx, sprites, *, padding=2):
        self.padding = padding

        self.next_id = 0
        self.packer = rectpack.newPacker()
        self.packer.add_bin(512, 512, count=10)
        self.sprites = {}

        self.tex_for_name = {}

        for sprite in sprites:
            self._add(sprite)

        self.packer.pack()

        n_texs = len(self.packer)
        self.surfs = [
            pygame.Surface((512, 512), pygame.SRCALPHA, depth=32)
            for _ in range(n_texs)
        ]

        for bin, x, y, w, h, (img, spritename) in self.packer.rect_list():
            orig_w, orig_h = img.get_size()
            rotated = False
            if orig_w != w:
                img = pygame.transform.rotate(img, -90)
                rotated = True

            dest = self.surfs[bin]
            dest.blit(img, (x + self.padding, y + self.padding))

            l = (x + self.padding) / 512
            t = 1.0 - (y + self.padding) / 512
            r = (x + w - self.padding) / 512
            b = 1.0 - (y + h - self.padding) / 512

            if rotated:
                texcoords = np.array([
                    (r, t),
                    (r, b),
                    (l, b),
                    (l, t),
                ], dtype='f4')
            else:
                texcoords = np.array([
                    (l, t),
                    (r, t),
                    (r, b),
                    (l, b),
                ], dtype='f4')
            verts = np.array([
                (0, orig_h, 1),
                (orig_w, orig_h, 1),
                (orig_w, 0, 1),
                (0, 0, 1),
            ], dtype='f4')
            verts -= (orig_w / 2, orig_h / 2, 0)
            self.tex_for_name[spritename] = (bin, texcoords, verts)

        # Save textures, for debugging
        for i, s in enumerate(self.surfs):
            pygame.image.save(s, f'atlas{i}.png')

        self.texs = []
        for t in self.surfs:
            tex = ctx.texture(
                t.get_size(),
                4,
                data=pygame.image.tostring(t, "RGBA", 1),
            )
            tex.build_mipmaps(max_level=2)
            self.texs.append(tex)

        for name, (bin, uvs, vs) in self.tex_for_name.items():
            self.tex_for_name[name] = self.texs[bin], uvs, verts

    def __getitem__(self, k):
        return self.tex_for_name[k]

    def _add(self, spritename):
        id = self.next_id
        self.next_id += 1

        img = pygame.image.load(spritename)
        self.sprites[spritename] = (img, id)

        pad = self.padding * 2
        w, h = img.get_size()
        self.packer.add_rect(w + pad, h + pad, (img, spritename))
