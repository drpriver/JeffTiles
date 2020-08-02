from appdirs import user_data_dir
from typing import Callable, List, Optional, Any, Dict, Tuple
from grid import tiles_from_folders, make_grid, make_grid_image, Tile, Grid, imagecache
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

    def make_grid(self, tiles:List[Tile]) -> Grid:
        return make_grid(
                tiles, 
                lower_blank_percentage = self.lower_blank_percentage,
                upper_blank_percentage = self.upper_blank_percentage,
                special_limit          = self.special_limit,
                middle_size            = self.middle_size,
                side_size              = self.side_size,
                )

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
        self.maybe_load_tile_data()
        self.config = GeneratorConfig()
        self.master = master
        self.canvas = tk.Canvas()
        self.canvas.pack(side='bottom', fill='both', expand='yes')
        self.canvas.bind('<Configure>', self.display_grid)
        self.make_buttons()
        self.make_inputs()
        self.make_tile_configurer()
        if self.tiles:
            self.fill_tile_configurer()

    def maybe_load_tile_data(self) -> None:
        try:
            with open(DATAPATH, 'rb') as fp:
                data = pickle.load(fp)
            self.all_tiles = data
            if 'Cave' in self.all_tiles:
                self.tiles = self.all_tiles['Cave']
        except:
            return

    def save_tile_data(self) -> None:
        print(DATAPATH)
        print(len(self.all_tiles))
        if not os.path.isdir(DATADIR):
            os.makedirs(DATADIR)
        with open(DATAPATH, 'wb') as fp:
            pickle.dump(self.all_tiles, fp)

    def make_tile_configurer(self) -> None:
        self.tile_labels = [
            ('Repeatable', 'repeatable', bool,),
            ('Weight', 'weight', Constrained(int, 1, 100),),
            ('Special', 'special', bool,),
            ('Blank', 'is_blank', bool,),
            ]
        frm_tileconf = tk.Frame()
        frm_tileconf.pack(side='left', padx=10)
        self.preview_tile = None
        self.tile_list_sv = tk.StringVar()
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


        frm_listbox = tk.Frame(frm_tileconf)
        frm_listbox.grid(row=0, column=0, sticky='n')
        self.tile_list_lb = tk.Listbox(frm_listbox, listvariable=self.tile_list_sv, selectmode='single', height=14)
        self.tile_list_lb.bind('<ButtonRelease>', lb_callback)
        self.tile_list_lb.pack(side='left',fill='y')
        self.tile_list_sb = tk.Scrollbar(frm_listbox)
        self.tile_list_sb.pack(side='left', fill='y')
        self.tile_list_lb.config(yscrollcommand=self.tile_list_sb.set)
        self.tile_list_sb.config(command=self.tile_list_lb.yview)


        self.tile_list_canvas = tk.Canvas(frm_tileconf, width=250, height=250,border=1)
        self.tile_list_canvas.grid(row=0, column=1, sticky='n')

        frm_tile_inputs = tk.Frame(frm_tileconf)
        frm_tile_inputs.grid(row=0, column=2, sticky='n')
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
            self.tile_list_lb.insert(n, t.name)

    def get_tiles(self, *args, **kwargs) -> None:
        imagefolder = tkinter.filedialog.askdirectory(
                title = 'Where are the images',
                mustexist=True,
                )
        if imagefolder:
            self.tile_list_lb.delete("1", tk.END)
            self.tiles = tiles_from_folders(imagefolder)
            if self.tiles:
                self.fill_tile_configurer()
                self.all_tiles['Cave'] = self.tiles



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
        btn_choose = tk.Button(text='Load Tiles', master=frm_buttons, command=self.get_tiles)
        btn_choose.pack(side=tk.LEFT, padx=10, ipadx=10)
        self.btn_choose = btn_choose


    def generate_grid(self) -> None:
        if self.tiles:
            self.grid = self.config.make_grid(self.tiles)
            self.im = make_grid_image(self.grid)
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
            self.im.save(savepath)
        return

app = App(root)
root.mainloop()
atexit.register(app.save_tile_data)
