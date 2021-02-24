import ctypes
from functools import partial
import math
import os
import re
import sys
import tkinter as tk
from tkinter import ttk

from lch import lch_to_srgb, srgb_to_lch
from PIL import Image, ImageTk, ImageGrab


class Karafuru(tk.Frame):
    _variables = {}
    _int_regex = re.compile(r'^$|^\d+$')
    _float_regex = re.compile(r'^$|^\d+\.?\d?$')
    _hex_regex = re.compile(r'^$|^#[\da-fA-F]{,6}$')
    _hex_strict_regex = re.compile(r'^#([\da-fA-F]{2})([\da-fA-F]{2})([\da-fA-F]{2})$')

    _update_lock = False

    _color_preview = None
    _color_preview_frame = None
    _picker_preview = None
    _picker_preview_frame = None
    _picker_button = None

    def __init__(self, master=None):
        super().__init__(master, name='karafuru')

        master.title('karafuru')
        master.iconphoto(False, tk.PhotoImage(file=os.path.join(os.path.dirname(sys.argv[0]), 'icon16.png')),
                         tk.PhotoImage(file=os.path.join(os.path.dirname(sys.argv[0]), 'icon.png')),
                         tk.PhotoImage(file=os.path.join(os.path.dirname(sys.argv[0]), 'icon256.png')))
        master.resizable(False, False)
        self.master = master
        self.grid(padx=5, pady=5)
        self.grid_columnconfigure(3, pad=20)

        self._create_variables()
        self._create_widgets()
        self.hex = '#000000'

    # variable getters and setters
    def _get_variable_value(self, variable):
        value = self._variables[variable].get()
        return 0 if value == '' else value

    def _set_variable_value(self, variable, value):
        self._variables[variable].set(value)

    @property
    def hex(self):
        return self._get_variable_value('hex')

    @hex.setter
    def hex(self, value):
        self._set_variable_value('hex', value)

    @property
    def red(self):
        return self._get_variable_value('red')

    @red.setter
    def red(self, value):
        self._set_variable_value('red', value)

    @property
    def green(self):
        return self._get_variable_value('green')

    @green.setter
    def green(self, value):
        self._set_variable_value('green', value)

    @property
    def blue(self):
        return self._get_variable_value('blue')

    @blue.setter
    def blue(self, value):
        self._set_variable_value('blue', value)

    @property
    def lightness(self):
        return self._get_variable_value('lightness')

    @lightness.setter
    def lightness(self, value):
        self._set_variable_value('lightness', value)

    @property
    def chroma(self):
        return self._get_variable_value('chroma')

    @chroma.setter
    def chroma(self, value):
        self._set_variable_value('chroma', value)

    @property
    def hue(self):
        return self._get_variable_value('hue')

    @hue.setter
    def hue(self, value):
        self._set_variable_value('hue', value)

    # change handlers
    def _reset_warning(self):
        self._warning.config(text='')

    def _update_color_from_rgb(self, changed_component=None, changed_value=None):
        if self._update_lock:
            return

        rgb = {
            'red': self.red,
            'green': self.green,
            'blue': self.blue
        }
        if changed_component and changed_value:
            rgb[changed_component] = changed_value

        self._reset_warning()
        hex_ = '#{:02x}{:02x}{:02x}'.format(rgb['red'], rgb['green'], rgb['blue'])
        lch = srgb_to_lch((rgb['red'] / 255, rgb['green'] / 255, rgb['blue'] / 255))
        self._update_lock = True
        self.hex = hex_
        self.lightness = lch[0]
        self.chroma = lch[1]
        self.hue = lch[2]
        self._update_lock = False
        self._color_preview.config(background=hex_)

    def _update_color_from_lch(self, changed_component=None, changed_value=None):
        if self._update_lock:
            return

        lch = {
            'lightness': self.lightness,
            'chroma': self.chroma,
            'hue': self.hue
        }
        if changed_component and changed_value:
            lch[changed_component] = changed_value

        self._reset_warning()
        (rgb, corrected) = lch_to_srgb((lch['lightness'], lch['chroma'], lch['hue']))
        if corrected:
            self._warning.config(text='Color has been auto-corrected to RGB boundaries.')
        rgb = tuple(round(v * 255) for v in rgb)
        hex_ = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
        self._update_lock = True
        self.hex = hex_
        self.red = rgb[0]
        self.green = rgb[1]
        self.blue = rgb[2]
        self._update_lock = False
        self._color_preview.config(background=hex_)

    def _update_color_from_hex(self, hex_):
        if self._update_lock:
            return

        match = self._hex_strict_regex.match(hex_)
        if match is None:
            return

        self._reset_warning()
        rgb = tuple(int(v, 16) for v in match.groups())
        lch = srgb_to_lch(tuple(v / 255 for v in rgb))
        self._update_lock = True
        self.red = rgb[0]
        self.green = rgb[1]
        self.blue = rgb[2]
        self.lightness = lch[0]
        self.chroma = lch[1]
        self.hue = lch[2]
        self._update_lock = False
        self._color_preview.config(background=hex_)

    # using the validate function to also cross update
    # all other values, and the preview color. magic!
    def _validate_entry(self, widget, value):
        variable = widget.rsplit('_', 1)[1]
        is_hex = variable == 'hex'
        is_rgb = variable in ('red', 'green', 'blue')
        is_lch = variable in ('lightness', 'chroma', 'hue')

        if is_hex:
            regex = self._hex_regex
        elif is_lch:
            regex = self._float_regex
        else:
            regex = self._int_regex

        match = regex.match(value)
        if match is None:
            return False

        # update color preview
        if is_rgb and value != '':
            self._update_color_from_rgb(variable, min(255, int(value)))
        elif is_lch and value != '':
            upper_limit = self._variables[variable].upper_limit
            self._update_color_from_lch(variable, min(upper_limit, float(value)))
        elif is_hex:
            self._update_color_from_hex(value)

        return True

    # color picker event handlers
    def _handle_picker_move(self, event):
        x = event.x + self._picker_button.winfo_rootx()
        y = event.y + self._picker_button.winfo_rooty()
        # image = ImageGrab.grab(bbox=(x - 12, y - 12, x + 13, y + 13), all_screens=True)
        image = ImageGrab.grab(bbox=(x - 7, y - 7, x + 8, y + 8), all_screens=True)
        image = image.resize((75, 75), resample=Image.NEAREST)
        self._picker_preview.original_image = image
        self._picker_preview.image = ImageTk.PhotoImage(image)
        self._picker_preview.config(image=self._picker_preview.image)

        (red, green, blue) = image.getpixel((37, 37))
        self._set_variable_value('red', red)
        self._set_variable_value('green', green)
        self._set_variable_value('blue', blue)

    def _handle_preview_click(self, event):
        x = max(0, min(74, event.x))
        y = max(0, min(74, event.y))
        (red, green, blue) = self._picker_preview.original_image.getpixel((x, y))
        self._set_variable_value('red', red)
        self._set_variable_value('green', green)
        self._set_variable_value('blue', blue)

    # initialization methods
    def _create_variables(self):
        self._variables['hex'] = tk.StringVar()
        self._variables['red'] = tk.IntVar()
        self._variables['green'] = tk.IntVar()
        self._variables['blue'] = tk.IntVar()
        self._variables['lightness'] = tk.DoubleVar()
        self._variables['lightness'].upper_limit = 100
        self._variables['chroma'] = tk.DoubleVar()
        self._variables['chroma'].upper_limit = 132
        self._variables['hue'] = tk.DoubleVar()
        self._variables['hue'].upper_limit = 360

    def _create_widgets(self):
        # validation helper function
        validate = self.register(lambda entry, value: self._validate_entry(entry, value))

        # base layout
        frame_left = tk.Frame(self)
        frame_left.grid(row=0, column=0)
        frame_right = tk.Frame(self)
        frame_right.grid(row=0, column=1)
        tk.Frame(frame_right, width=10).grid(row=0, column=0)

        # color preview
        self._color_preview_frame = tk.Frame(frame_left, bg='#808080', padx=5, pady=5)
        self._color_preview_frame.pack()
        self._color_preview = tk.Frame(self._color_preview_frame, bg='#000', width=75, height=75)
        self._color_preview.pack()

        params = {
            'validate': 'key',
            'validatecommand': (validate, '%W', '%P'),

            'relief': tk.FLAT,
            'borderwidth': 1,
            'highlightbackground': '#a0a0a0',
            'highlightcolor': '#606060',
            'highlightthickness': 1
        }
        tk.Entry(frame_left, width=10, name='entry_hex', textvariable=self._variables['hex'], **params).pack(pady=5)

        # color picker preview
        self._picker_preview_frame = tk.Frame(frame_left, bg='#000', padx=1, pady=1)
        self._picker_preview_frame.pack(pady=5)
        self._picker_preview = tk.Label(self._picker_preview_frame, borderwidth=0)
        self._picker_preview.original_image = Image.new('RGB', (75, 75), 0x808080)
        self._picker_preview.image = ImageTk.PhotoImage(self._picker_preview.original_image)
        self._picker_preview.config(image=self._picker_preview.image)
        self._picker_preview.pack()
        self._picker_preview.bind('<Button-1>', partial(self._handle_preview_click))
        self._picker_preview.bind('<B1-Motion>', partial(self._handle_preview_click))

        # color picker button
        self._picker_button = ttk.Button(self, text='Pick color')
        self._picker_button.grid(row=10, column=0)
        self._picker_button.bind('<Button-1>', partial(self._handle_picker_move))
        self._picker_button.bind('<B1-Motion>', partial(self._handle_picker_move))

        # labels
        tk.Label(frame_right, text='Red').grid(sticky=tk.W, row=0, column=1)
        tk.Label(frame_right, text='Green').grid(sticky=tk.W, row=1, column=1)
        tk.Label(frame_right, text='Blue').grid(sticky=tk.W, row=2, column=1)
        tk.Label(frame_right, text='Lightness').grid(sticky=tk.W, row=4, column=1)
        tk.Label(frame_right, text='Chroma').grid(sticky=tk.W, row=5, column=1)
        tk.Label(frame_right, text='Hue').grid(sticky=tk.W, row=6, column=1)

        self._warning = tk.Label(frame_right, text='', fg='#e04e39')
        self._warning.grid(row=3, column=1, columnspan=3, sticky=tk.E)

        # inputs
        params = {
            'validate': 'key',
            'validatecommand': (validate, '%W', '%P'),

            'justify': 'right',
            'relief': tk.FLAT,
            'borderwidth': 1,
            'highlightbackground': '#a0a0a0',
            'highlightcolor': '#606060',
            'highlightthickness': 1
        }

        tk.Entry(frame_right, width=5, name='entry_red', textvariable=self._variables['red'], **params).grid(row=0, column=2, padx=10, pady=3.5)
        tk.Entry(frame_right, width=5, name='entry_green', textvariable=self._variables['green'], **params).grid(row=1, column=2, padx=10, pady=3.5)
        tk.Entry(frame_right, width=5, name='entry_blue', textvariable=self._variables['blue'], **params).grid(row=2, column=2, padx=10, pady=3.5)
        tk.Entry(frame_right, width=5, name='entry_lightness', textvariable=self._variables['lightness'], **params).grid(row=4, column=2, padx=10, pady=3.5)
        tk.Entry(frame_right, width=5, name='entry_chroma', textvariable=self._variables['chroma'], **params).grid(row=5, column=2, padx=10, pady=3.5)
        tk.Entry(frame_right, width=5, name='entry_hue', textvariable=self._variables['hue'], **params).grid(row=6, column=2, padx=10, pady=3.5)

        # sliders
        params = {
            'from_': 0,
            'orient': tk.HORIZONTAL,
            'length': 300,
            'showvalue': False,
            'repeatdelay': 150,
            'repeatinterval': 25,

            'sliderrelief': tk.FLAT,
            'borderwidth': 0,
            'foreground': '#00ff00',
            'troughcolor': '#c0c0c0',
            'highlightbackground': '#a0a0a0',
            'highlightthickness': 1,

            'background': '#e0e0e0',
            'activebackground': '#f0f0f0'
        }

        tk.Scale(frame_right, to=255, variable=self._variables['red'], **params).grid(row=0, column=3)
        tk.Scale(frame_right, to=255, variable=self._variables['green'], **params).grid(row=1, column=3)
        tk.Scale(frame_right, to=255, variable=self._variables['blue'], **params).grid(row=2, column=3)
        tk.Scale(frame_right, to=100, resolution=0.1, variable=self._variables['lightness'], **params).grid(row=4, column=3)
        tk.Scale(frame_right, to=132, resolution=0.1, variable=self._variables['chroma'], **params).grid(row=5, column=3)
        tk.Scale(frame_right, to=360, resolution=0.1, variable=self._variables['hue'], **params).grid(row=6, column=3)


# on windows, set our own app id to ensure the task bar renders our icon instead of python's
if sys.platform == 'win32':
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ennea.karafuru')
    # https://stackoverflow.com/questions/36514158/tkinter-output-blurry-for-icon-and-text-python-2-7
    ctypes.windll.shcore.SetProcessDpiAwareness(1)

root = tk.Tk()
app = Karafuru(master=root)
app.mainloop()
