import enum
from typing import List, NamedTuple, Optional, Tuple
from PIL import Image
import random
import glob
import os

class Grid:
    def __init__(self, width:int, height:int):
        self.upper:        List['Tile']         = []
        self.bottom_left:  List['Tile']         = []
        self.bottom_right: List['Tile']         = []
        self.middle:       List['Tile']         = []
        self.width  = width
        self.height = height
    def shuffle(self):
        for l in (self.upper, self.bottom_left, self.bottom_right, self.middle):
            random.shuffle(l)

@enum.unique
class TileLocation(enum.Flag):
    MIDDLE = enum.auto()
    SIDE   = enum.auto()
    UPPER  = enum.auto()

class Tile(NamedTuple):
    name: str
    path: str
    repeatable: bool
    weight: int
    location: TileLocation
    biome: str
    special: bool
    is_blank: bool

def make_grid(tileset:List[Tile]) -> Grid:
    LOWER_BLANK_PERCENTAGE = 30
    UPPER_BLANK_PERCENTAGE = 20
    SPECIAL_LIMIT = 1
    MIDDLE_AMOUNT = 3
    SIDE_AMOUNT = 3
    UPPER_AMOUNT = SIDE_AMOUNT * 2 + MIDDLE_AMOUNT
    WIDTH = UPPER_AMOUNT
    HEIGHT = 2
    grid = Grid(WIDTH, HEIGHT)
    upper_blanks:List[Tile] = []
    upper_nonblanks:List[Tile] = []
    for t in (t for t in tileset if t.location & TileLocation.UPPER):
        if t.is_blank:
            upper_blanks.append(t)
        else:
            upper_nonblanks.append(t)
    for _ in range(UPPER_AMOUNT):
        if random.random() * 100 < UPPER_BLANK_PERCENTAGE:
            grid.upper.append(random.choice(upper_blanks))
        else:
            grid.upper.append(random.choice(upper_nonblanks))

    side_blanks:List[Tile] = []
    side_nonblanks:List[Tile] = []
    for t in (t for t in tileset if t.location & TileLocation.SIDE):
        if t.is_blank:
            side_blanks.append(t)
        else:
            side_nonblanks.append(t)

    middle_blanks:List[Tile] = []
    middle_nonblanks:List[Tile] = []
    for t in (t for t in tileset if t.location & TileLocation.MIDDLE):
        if t.is_blank:
            middle_blanks.append(t)
        else:
            middle_nonblanks.append(t)
    # left
    for _ in range(SIDE_AMOUNT):
        if random.random() * 100 < LOWER_BLANK_PERCENTAGE:
            grid.bottom_left.append(random.choice(side_blanks))
        else:
            grid.bottom_left.append(random.choice(side_nonblanks))
    # middle
    for _ in range(MIDDLE_AMOUNT):
        if random.random() * 100 < LOWER_BLANK_PERCENTAGE:
            grid.middle.append(random.choice(middle_blanks))
        else:
            grid.middle.append(random.choice(middle_nonblanks))
    # right
    for _ in range(SIDE_AMOUNT):
        if random.random() * 100 < LOWER_BLANK_PERCENTAGE:
            grid.bottom_right.append(random.choice(side_blanks))
        else:
            grid.bottom_right.append(random.choice(side_nonblanks))

    # apply constraint - only 1 special
    special_count = 0
    for t in grid.middle:
        if t.special:
            special_count += 1
    if special_count > SPECIAL_LIMIT:
        specials = [t for t in grid.middle if t.special]
        nonspecials = [t for t in grid.middle if not t.special]
        middle_nonspecials = [t for t in middle_nonblanks if not t.special]
        new_middle: List[Tile] = nonspecials
        new_middle.append(random.choice(specials))
        while len(new_middle) < MIDDLE_AMOUNT:
            new_middle.append(random.choice(middle_nonspecials))
        grid.middle = new_middle
    grid.shuffle()
    return grid


class ImageCache:
    def __init__(self):
        self.cache : Dict[str, Image.Image] = {}

    def get(self, path:str) -> Image.Image:
        # note: can throw FileNotFoundError or OSError (IOError?)
        if path in self.cache:
            return self.cache[path]
        img = Image.open(path)
        self.cache[path] = img
        return img

def make_grid_image(grid:Grid, imagecache:ImageCache=ImageCache()) -> Image.Image:
    TILEWIDTH  = 250
    TILEHEIGHT = 250
    PIXELWIDTH = grid.width * TILEWIDTH
    PIXELHEIGHT = grid.height * TILEHEIGHT
    #TODO: is it HWC or WHC?

    img = Image.new('RGB', (PIXELWIDTH, PIXELHEIGHT))
    for n, t in enumerate(grid.upper):
        subimg = imagecache.get(t.path)
        img.paste(subimg.resize((TILEWIDTH, TILEHEIGHT)), (TILEWIDTH*n, 0))
    for n, t in enumerate(grid.bottom_left + grid.middle + grid.bottom_right):
        subimg = imagecache.get(t.path)
        img.paste(subimg.resize((TILEWIDTH, TILEHEIGHT)), (TILEWIDTH*n, TILEHEIGHT))
    return img

import re

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
            name = path.split('/')[-1].replace('.png', '')
            repeatable = 'Repeatable' in path
            weight = int(re.search(r'\d\d', path).group()) # type: ignore
            if 'Middle' in path:
                location = TileLocation.MIDDLE
            elif 'Side' in path:
                location = TileLocation.SIDE 
            else:
                location = TileLocation.UPPER
            biome = 'Cave'
            special = 'Special' in path
            is_blank = 'Blank' in path
            tileset.append(Tile(name, os.path.abspath(path), repeatable, weight, location, biome, special, is_blank))
        except:
            continue
    return tileset

if __name__ == '__main__':
    tileset = tiles_from_folders('.')
    grid = make_grid(tileset)
    imagecache = ImageCache()
    img = make_grid_image(grid, imagecache)
    img.save('test.png')

