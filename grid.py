import enum
from typing import List, NamedTuple, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import random
import glob
import os
import re

class Grid:
    def __init__(self, width:int, height:int):
        self.upper:        List[List['Tile']] = [ [] for _ in range(height-1)]
        self.bottom_left:  List['Tile'] = []
        self.bottom_right: List['Tile'] = []
        self.middle:       List['Tile'] = []
        self.width  = width
        self.height = height

    def shuffle(self):
        for l in [self.bottom_left, self.bottom_right, self.middle] + self.upper:
            random.shuffle(l)

@enum.unique
class TileLocation(enum.Flag):
    MIDDLE = enum.auto()
    SIDE   = enum.auto()
    UPPER  = enum.auto()

@dataclass
class Tile:
    name: str
    path: str
    repeatable: bool
    weight: int
    middle: bool
    side: bool
    upper: bool
    biome: str
    special: bool
    is_blank: bool

def select(tiles:List[Tile])->Tile:
    return random.choices(tiles, weights=[t.weight for t in tiles])[0]


def make_grid(
        tileset:List[Tile],
        lower_blank_percentage:float,
        upper_blank_percentage:float,
        special_limit:int,
        middle_size:int,
        side_size:int,
        height:int,
        ) -> Grid:
    width = side_size * 2 + middle_size
    grid = Grid(width, height)
    upper_blanks:List[Tile] = []
    upper_nonblanks:List[Tile] = []
    for t in (t for t in tileset if t.upper):
        if t.is_blank:
            upper_blanks.append(t)
        else:
            upper_nonblanks.append(t)

    for i in range(height-1):
        upper = grid.upper[i]
        for _ in range(width):
            if random.random() * 100 < upper_blank_percentage:
                upper.append(select(upper_blanks))
            else:
                upper.append(select(upper_nonblanks))

    side_blanks:List[Tile] = []
    side_nonblanks:List[Tile] = []
    for t in (t for t in tileset if t.side):
        if t.is_blank:
            side_blanks.append(t)
        else:
            side_nonblanks.append(t)

    middle_blanks:List[Tile] = []
    middle_nonblanks:List[Tile] = []
    for t in (t for t in tileset if t.middle):
        if t.is_blank:
            middle_blanks.append(t)
        else:
            middle_nonblanks.append(t)
    # left
    for _ in range(side_size):
        if random.random() * 100 < lower_blank_percentage:
            grid.bottom_left.append(select(side_blanks))
        else:
            grid.bottom_left.append(select(side_nonblanks))
    # middle
    for _ in range(middle_size):
        if random.random() * 100 < lower_blank_percentage:
            grid.middle.append(select(middle_blanks))
        else:
            grid.middle.append(select(middle_nonblanks))
    # right
    for _ in range(side_size):
        if random.random() * 100 < lower_blank_percentage:
            grid.bottom_right.append(select(side_blanks))
        else:
            grid.bottom_right.append(select(side_nonblanks))

    # apply constraint - only 1 special
    special_count = 0
    for t in grid.middle:
        if t.special:
            special_count += 1
    if special_count > special_limit:
        specials = [t for t in grid.middle if t.special]
        nonspecials = [t for t in grid.middle if not t.special]
        middle_nonspecials = [t for t in middle_nonblanks if not t.special]
        new_middle: List[Tile] = nonspecials
        new_middle.append(select(specials))
        while len(new_middle) < middle_size:
            new_middle.append(select(middle_nonspecials))
        grid.middle = new_middle
    grid.shuffle()
    return grid


class ImageCache:
    def __init__(self):
        self.cache : Dict[str, Image.Image] = {}

    def get(self, path:str) -> Image.Image:
        # TODO: can throw FileNotFoundError or OSError (IOError?)
        # we don't really handle that anywhere
        if path in self.cache:
            return self.cache[path]
        img = Image.open(path)
        self.cache[path] = img
        return img

imagecache = ImageCache()
def make_grid_image(grid:Grid, imagecache:ImageCache=imagecache, tiledim:int=250) -> Image.Image:
    TILEWIDTH  = tiledim
    TILEHEIGHT = tiledim
    PIXELWIDTH = grid.width * TILEWIDTH
    PIXELHEIGHT = grid.height * TILEHEIGHT
    img = Image.new('RGB', (PIXELWIDTH, PIXELHEIGHT))
    for i in range(grid.height-1):
        upper = grid.upper[i]
        for n, t in enumerate(upper):
            subimg = imagecache.get(t.path)
            img.paste(subimg.resize((TILEWIDTH, TILEHEIGHT)), (TILEWIDTH*n, TILEHEIGHT*i))
    for n, t in enumerate(grid.bottom_left + grid.middle + grid.bottom_right):
        subimg = imagecache.get(t.path)
        img.paste(subimg.resize((TILEWIDTH, TILEHEIGHT)), (TILEWIDTH*n, (grid.height-1)*TILEHEIGHT))
    return img



def load_tile(path:str) -> Tile:
    name, _ = os.path.splitext(os.path.basename(path))
    repeatable = 'Repeatable' in path
    try:
        weight = int(re.search(r'\d\d', path).group()) # type: ignore
    except:
        weight = 5
    middle = 'Middle' in path
    side = 'Side' in path
    upper = 'Upper' in path
    biome = 'Cave'
    special = 'Special' in path
    is_blank = 'Blank' in path
    return Tile(
        name=name,
        path=os.path.abspath(path),
        repeatable=repeatable,
        weight=weight,
        middle=middle,
        side=side,
        upper=upper,
        biome=biome,
        special=special,
        is_blank=is_blank
        )


def tiles_from_folders(folderpath:str) -> List[Tile]:
    extensions = [
            'png',
            'PNG',
            'jpg',
            'jpeg',
            'JPG',
            'JPEG',
            'bmp',
            'BMP',
            'gif',
            'GIF',
            'webp',
            'WEBP',
            ]
    paths: List[str] = []
    for ext in extensions:
        globpath = os.path.join(folderpath, '**/*.'+ext)
        paths.extend(glob.glob(globpath, recursive=True))
    paths = sorted(set(paths))
    tileset : List[Tile] = []
    for path in paths:
        try:
            tileset.append(load_tile(path))
        except:
            continue
    return tileset

if __name__ == '__main__':
    tileset = tiles_from_folders('.')
    grid = make_grid(
            tileset,
            lower_blank_percentage=30,
            upper_blank_percentage=20,
            special_limit=1,
            middle_size=3,
            side_size=3,
            height=2,
            )
    imagecache = ImageCache()
    img = make_grid_image(grid, imagecache)
