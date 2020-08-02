from grid import tiles_from_folders, make_grid, make_grid_image
import tkinter as tk
import tkinter.filedialog
from PIL import ImageTk, Image
root = tk.Tk()
root.title("make grid")

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

class App:
    def __init__(self, master):
        self.dungeon = None
        self.photo = None
        self.im = None
        self.master = master
        self.canvas = tk.Canvas()
        self.canvas.pack(side='bottom', fill='both', expand='yes')
        self.canvas.bind('<Configure>', self.display_grid)
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
        self.tiles = None

    def generate_grid(self) -> None:
        if self.tiles:
            self.im = make_grid_image(make_grid(self.tiles))
            self.display_grid()

    def get_tiles(self, *args, **kwargs) -> None:
        imagefolder = tkinter.filedialog.askdirectory(
                title = 'Where are the images',
                mustexist=True,
                )
        if imagefolder:
            self.tiles = tiles_from_folders(imagefolder)


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
# btn_new.bind('<Button-1>', generate_grid)
root.mainloop()
