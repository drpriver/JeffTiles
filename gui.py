from appdirs import user_data_dir
from typing import Callable, List, Optional, Any, Dict, Tuple
from grid import tiles_from_folders, make_grid, make_grid_image, Tile, Grid, imagecache, load_tile
import pickle
import tkinter as tk
import tkinter.filedialog
from PIL import ImageTk, Image
import os
import atexit
DATADIR = user_data_dir(appname='JeffTiles', appauthor='David')
DATAPATH = os.path.join(DATADIR, 'tiledata.pickle')
root = tk.Tk()
root.title("make grid")
root.geometry('1400x700')

def resize_image(img:Image.Image, width:int, height:int) -> Image.Image:
    rx = width/img.width
    ry = height/img.height
    if rx < ry:
        new_width = width
        new_height = int(img.height*rx)
    else:
        new_width = int(img.width*ry)
        new_height = height
    return img.resize((new_width, new_height))

class Constrained:
    def __init__(self, type_:type, min_, max_):
        self.type_ = type_
        self.min_ = min_
        self.max_ = max_
    def __call__(self, text:str):
        val = self.type_(text)
        if self.min_ is not None:
            if val < self.min_:
                raise ValueError
        if self.max_ is not None:
            if val > self.max_:
                raise ValueError
        return val


class GeneratorConfig:
    def __init__(self):
        self.lower_blank_percentage = 30
        self.upper_blank_percentage = 30
        self.special_limit = 1
        self.middle_size = 3
        self.side_size = 3
        self.tile_px = 250

    def make_grid(self, tiles:List[Tile]) -> Grid:
        return make_grid(
                tiles,
                lower_blank_percentage = self.lower_blank_percentage,
                upper_blank_percentage = self.upper_blank_percentage,
                special_limit          = self.special_limit,
                middle_size            = self.middle_size,
                side_size              = self.side_size,
                )
    def make_grid_image(self, grid:Grid) -> Image:
        return make_grid_image(grid, tiledim = self.tile_px)

def setter(thing:Any, attr:str, type_:Constrained, sv, entry) -> Callable:
    def set_val(*args, **kwargs):
        text = sv.get()
        try:
            val = type_(text.strip())
        except ValueError:
            entry.configure(bg='#ff8888')
            return
        else:
            entry.configure(bg='white')
        setattr(thing, attr, val)
    return set_val

def boolsetter(thing:Any, attr:str, bv) -> Callable:
    def set_val(*args, **kwargs):
        val = bv.get()
        setattr(thing, attr, val)
    return set_val


class App:
    def __init__(self, master) -> None:
        self.photo:Optional[ImageTk] = None
        self.im:Optional[Image] = None
        self.grid:Optional[Grid] = None
        self.tiles:List[Tile] = []
        self.all_tiles : Dict[str, List[Tile]] = {}
        self.tileset_names: List[str] = []
        self.config = GeneratorConfig()
        self.maybe_load_tile_data()
        self.master = master
        self.canvas = tk.Canvas()
        self.canvas.pack(side='bottom', fill='both', expand='yes')
        self.canvas.bind('<Configure>', self.display_grid)
        self.make_buttons()
        self.make_inputs()
        self.make_tile_configurer()
        if self.tileset_names:
            for name in self.tileset_names:
                self.tileset_lb.insert(tk.END, name)
            self.tiles = self.all_tiles[self.tileset_names[0]]
            self.tileset_lb.activate(0)
        if self.tiles:
            self.fill_tile_configurer()

    def maybe_load_tile_data(self) -> None:
        try:
            with open(DATAPATH, 'rb') as fp:
                data, config = pickle.load(fp)
            self.all_tiles = data
            self.config = config
            self.tileset_names = sorted(self.all_tiles.keys())
        except Exception as e:
            return

    def save_tile_data(self) -> None:
        if not os.path.isdir(DATADIR):
            os.makedirs(DATADIR)
        with open(DATAPATH, 'wb') as fp:
            pickle.dump((self.all_tiles, self.config), fp)

    def make_tile_configurer(self) -> None:
        self.tile_labels = [
            ('Repeatable', 'repeatable', bool,),
            ('Weight', 'weight', Constrained(int, 1, 100),),
            ('Special', 'special', bool,),
            ('Blank', 'is_blank', bool,),
            ('Side', 'side', bool,),
            ('Middle', 'middle', bool,),
            ('Upper', 'upper', bool,),
            ]
        frm_tileconf = tk.Frame()
        frm_tileconf.pack(side='left', padx=10)
        self.preview_tile = None
        def lb_callback(*args, **kwargs):
            lb_sel = self.tile_list_lb.curselection()
            if not lb_sel:
                return
            tile = self.tiles[lb_sel[0]]
            img = imagecache.get(tile.path)
            self.preview_tile=ImageTk.PhotoImage(img)
            self.tile_list_canvas.create_image(0, 0, image=self.preview_tile, anchor='nw')
            for (text, attrname, typ) in self.tile_labels:
                if isinstance(typ, Constrained):
                    entry, sv = self.tile_input_controls[attrname]
                    if attrname in self.tile_input_controls_cbname:
                        sv.trace_remove('write', self.tile_input_controls_cbname[attrname])
                    sv.set(str(getattr(tile, attrname)))
                    self.tile_input_controls_cbname[attrname] = sv.trace_add("write", setter(tile, attrname, typ, sv, entry))
                else:
                    checkbox, bv = self.tile_input_controls[attrname]
                    if attrname in self.tile_input_controls_cbname:
                        bv.trace_remove('write', self.tile_input_controls_cbname[attrname])
                    bv.set(getattr(tile, attrname))
                    self.tile_input_controls_cbname[attrname] = bv.trace_add("write", boolsetter(tile, attrname, bv))

        def tileset_lb_callback(*args, **kwargs):
            lb_sel = self.tileset_lb.curselection()
            if not lb_sel:
                return
            tileset_name = self.tileset_lb.get(*lb_sel)
            self.tiles = self.all_tiles[tileset_name]
            self.fill_tile_configurer()

        self.tileset_sv = tk.StringVar()
        frm_tileset_lb_meta = tk.Frame(frm_tileconf)
        frm_tileset_lb_meta.grid(row=0, column=0, sticky='n')
        frm_tileset_lb = tk.Frame(frm_tileset_lb_meta)
        frm_tileset_lb.grid(row=0, column=0, sticky='n')
        self.tileset_lb = tk.Listbox(frm_tileset_lb, listvariable=self.tileset_sv, selectmode='single', height=12)
        self.tileset_lb.bind('<ButtonRelease>', tileset_lb_callback)
        self.tileset_lb.pack(side='left',fill='y')
        self.tileset_sb = tk.Scrollbar(frm_tileset_lb)
        self.tileset_sb.pack(side='left', fill='y')
        self.tileset_lb.config(yscrollcommand=self.tileset_sb.set)
        self.tileset_sb.config(command=self.tileset_lb.yview)
        def tileset_deleter(*args, **kwargs):
            lb_sel = self.tileset_lb.curselection()
            if not lb_sel:
                return
            tileset_name = self.tileset_lb.get(*lb_sel)
            self.tileset_names.remove(tileset_name)
            del self.all_tiles[tileset_name]
            self.tileset_lb.delete(lb_sel[0])
            self.tiles = []
            self.fill_tile_configurer()
        frm_tileset_buttons = tk.Frame(frm_tileset_lb_meta)
        frm_tileset_buttons.grid(row=1, column=0, sticky='n')
        self.tileset_add_entry = tk.Entry(frm_tileset_buttons, width=10)
        self.tileset_add_entry.grid(row=0, column=0)
        def add_tileset(*args, **kwargs):
            name = self.tileset_add_entry.get().strip()
            if not name:
                return
            self.tileset_add_entry.delete(0, tk.END)
            if name in self.all_tiles:
                return
            self.tileset_names.append(name)
            self.tileset_lb.insert(tk.END, name)
            self.all_tiles[name] = []
            self.tiles = []
            self.fill_tile_configurer()
        self.tileset_add_button = tk.Button(frm_tileset_buttons, text='New Tileset', command=add_tileset)
        self.tileset_add_button.grid(row=0, column=1)

        self.tileset_delete_button = tk.Button(frm_tileset_buttons, text='Delete Tileset', command=tileset_deleter)
        self.tileset_delete_button.grid(row=1, column=0, columnspan=2)

        self.tile_list_sv = tk.StringVar()
        frm_listbox_meta = tk.Frame(frm_tileconf)
        frm_listbox_meta.grid(row=0, column=1, sticky='n')
        frm_listbox = tk.Frame(frm_listbox_meta)
        frm_listbox.pack()
        self.tile_list_lb = tk.Listbox(frm_listbox, listvariable=self.tile_list_sv, selectmode='single', height=14)
        self.tile_list_lb.bind('<ButtonRelease>', lb_callback)
        self.tile_list_lb.pack(side='left',fill='y')
        self.tile_list_sb = tk.Scrollbar(frm_listbox)
        self.tile_list_sb.pack(side='left', fill='y')
        self.tile_list_lb.config(yscrollcommand=self.tile_list_sb.set)
        self.tile_list_sb.config(command=self.tile_list_lb.yview)

        btn_choose = tk.Button(text='Load Tiles', master=frm_listbox_meta, command=self.get_tiles)
        btn_choose.pack(side=tk.TOP, padx=10, ipadx=10)
        self.btn_choose = btn_choose

        btn_add_tile = tk.Button(text='Add Tile', master=frm_listbox_meta, command=self.add_tile)
        btn_add_tile.pack(side=tk.TOP, padx=10, ipadx=10)
        self.btn_add_tile = btn_add_tile

        def delete_tile(*args, **kwargs) -> None:
            sel = self.tile_list_lb.curselection()
            if not sel:
                return
            index = sel[0]
            assert isinstance(index, int)
            self.tiles.pop(index)
            self.fill_tile_configurer()

        btn_delete_tile = tk.Button(text='Delete Tile', master=frm_listbox_meta, command=delete_tile)
        btn_delete_tile.pack(side=tk.LEFT, padx=10, ipadx=10)
        self.btn_delete_tile = btn_delete_tile


        self.tile_list_canvas = tk.Canvas(frm_tileconf, width=250, height=250,border=1)
        self.tile_list_canvas.grid(row=0, column=2, sticky='n')

        frm_tile_inputs = tk.Frame(frm_tileconf)
        frm_tile_inputs.grid(row=0, column=3, sticky='n')
        self.tile_input_controls:Dict[str, Tuple] = {}
        self.tile_input_controls_cbname: Dict[str, Any] = {}

        for n, (text, attrname, typ) in enumerate(self.tile_labels):
            label = tk.Label(master=frm_tile_inputs, text=text)
            self.input_labels.append(label)
            if isinstance(typ, Constrained):
                sv = tk.StringVar()
                entry = tk.Entry(master=frm_tile_inputs, width = 5, textvariable=sv)
                label.grid(row=n, column=0, sticky='e')
                entry.grid(row=n, column=1)
                self.tile_input_controls[attrname] = (entry, sv)
            else:
                label.grid(row=n, column=0, sticky='e')
                bv = tk.BooleanVar()
                checkbox = tk.Checkbutton(master=frm_tile_inputs, variable=bv)
                checkbox.grid(row=n, column=1, sticky='w')
                self.tile_input_controls[attrname] = (checkbox, bv)

    def fill_tile_configurer(self) -> None:
        self.tile_list_canvas.delete("all")
        self.tile_list_lb.delete("0", tk.END)
        for (text, attrname, typ) in self.tile_labels:
            if isinstance(typ, Constrained):
                entry, sv = self.tile_input_controls[attrname]
                if attrname in self.tile_input_controls_cbname:
                    sv.trace_remove('write', self.tile_input_controls_cbname[attrname])
                    del self.tile_input_controls_cbname[attrname]
                sv.set('')
            else:
                checkbox, bv = self.tile_input_controls[attrname]
                if attrname in self.tile_input_controls_cbname:
                    bv.trace_remove('write', self.tile_input_controls_cbname[attrname])
                    del self.tile_input_controls_cbname[attrname]
                bv.set(False)

        for n, t in enumerate(self.tiles):
            self.tile_list_lb.insert(n+1, t.name)

    def add_tile(self) -> None:
        imagefile = tkinter.filedialog.askopenfilename(
            title='Choose an image',
            )
        if not os.path.isfile(imagefile):
            return
        tile = load_tile(imagefile)
        self.tiles.append(tile)
        self.fill_tile_configurer()

    def get_tiles(self, *args, **kwargs) -> None:
        lb_sel = self.tileset_lb.curselection()
        if not lb_sel:
            return
        tileset_name = self.tileset_lb.get(*lb_sel)

        imagefolder = tkinter.filedialog.askdirectory(
                title = 'Where are the images',
                mustexist=True,
                )
        if not os.path.isdir(imagefolder):
            return
        if imagefolder:
            self.tiles = tiles_from_folders(imagefolder)
            if self.tiles:
                self.all_tiles[tileset_name] = self.tiles
                self.fill_tile_configurer()

    def make_inputs(self) -> None:
        self.input_labels: List[tk.Label] = []
        self.input_entries: List[tk.Entry] = []
        self.svs: List[tk.StringVar] = []
        frm_form = tk.Frame(relief=tk.SUNKEN, borderwidth=3)
        frm_form.pack(side='left', padx=10, anchor='nw')
        labels = [
            ('Lower Blank%', 'lower_blank_percentage', Constrained(float, 0, 100)),
            ('Upper Blank%', 'upper_blank_percentage', Constrained(float, 0, 100)),
            ('Special Limit', 'special_limit',         Constrained(int, 0, 3)),
            ('Middle Size',   'middle_size',           Constrained(int, 1, 10)),
            ('Side Size',     'side_size',             Constrained(int, 1, 10)),
            ('Tile Px',       'tile_px',               Constrained(int, 25, 500)),
            ]
        for n, (text, attrname, type_) in enumerate(labels):
            label = tk.Label(master=frm_form, text=text)
            self.input_labels.append(label)
            sv = tk.StringVar(value=str(getattr(self.config, attrname)))
            entry = tk.Entry(master=frm_form, width = 5, textvariable=sv)
            sv.trace_add("write", setter(self.config, attrname, type_, sv, entry))
            self.svs.append(sv)
            label.grid(row=n, column=0, sticky='e')
            entry.grid(row=n, column=1)

    def make_buttons(self) -> None:
        frm_buttons = tk.Frame()
        frm_buttons.pack(side='top', fill=tk.X, ipadx=5, ipady=5)
        self.frm_buttons = frm_buttons
        btn_new = tk.Button(text='New Map', master=frm_buttons, command=self.generate_grid)
        btn_new.pack(side=tk.LEFT, padx=10, ipadx=10)
        self.btn_new = btn_new
        btn_save = tk.Button(text='Save Map', master=frm_buttons, command=self.save_grid)
        btn_save.pack(side=tk.LEFT, padx=10, ipadx=10)
        self.btn_save = btn_save

    def generate_grid(self) -> None:
        if self.tiles:
            self.grid = self.config.make_grid(self.tiles)
            self.im = self.config.make_grid_image(self.grid)
            self.display_grid()

    def display_grid(self, *args, **kwargs) -> None:
        if self.im:
            width = self.canvas.winfo_width() - 20
            height = self.canvas.winfo_width() - 20
            resized = resize_image(self.im, width, height)
            self.photo=ImageTk.PhotoImage(resized)
            self.canvas.create_image(10, 10, image=self.photo, anchor='nw')

    def save_grid(self, *args, **kwargs) -> None:
        if self.im:
            savepath = tkinter.filedialog.asksaveasfilename(
                    title='Where to save',
                    defaultextension='.png',
                    )
            if not savepath:
                return
            self.im.save(savepath)
        return

app = App(root)
atexit.register(app.save_tile_data)
root.mainloop()
