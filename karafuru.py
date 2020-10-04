import math
import re
import tkinter as tk

from lch import lch_to_srgb, srgb_to_lch


class Karafuru(tk.Frame):
    _variables = {}
    _int_regex = re.compile(r'^$|^\d+$')
    _float_regex = re.compile(r'^$|^\d+\.?\d?$')  # TODO: how to express \.?\d? in such a way that if \d exists, \. also has to?
    _hex_regex = re.compile(r'^$|^#[\da-fA-F]{,6}$')
    _hex_strict_regex = re.compile(r'^#([\da-fA-F]{2})([\da-fA-F]{2})([\da-fA-F]{2})$')

    _update_lock = False

    _color_preview = None
    _color_preview_frame = None

    def __init__(self, master=None):
        super().__init__(master, name='karafuru')

        master.title('karafuru')
        master.iconbitmap('icon.ico')
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
        # spacers
        tk.Frame(self, width=10).grid(column=1, rowspan=4)
        tk.Frame(self, height=5).grid(row=3, columnspan=5)

        # the color preview
        self._color_preview_frame = tk.Frame(self, bg='#808080', padx=5, pady=5)
        self._color_preview_frame.grid(row=0, column=0, rowspan=3)
        self._color_preview = tk.Frame(self._color_preview_frame, bg='#000', width=75, height=75)
        self._color_preview.grid()

        # labels
        tk.Label(self, text='Red').grid(sticky=tk.W, row=0, column=2)
        tk.Label(self, text='Green').grid(sticky=tk.W, row=1, column=2)
        tk.Label(self, text='Blue').grid(sticky=tk.W, row=2, column=2)
        tk.Label(self, text='Lightness').grid(sticky=tk.W, row=5, column=2)
        tk.Label(self, text='Chroma').grid(sticky=tk.W, row=6, column=2)
        tk.Label(self, text='Hue').grid(sticky=tk.W, row=7, column=2)

        self._warning = tk.Label(self, text='', fg='#e04e39')
        self._warning.grid(row=4, column=2, columnspan=3, sticky=tk.E)

        # inputs
        validate = self.register(lambda entry, value: self._validate_entry(entry, value))
        defaults = {
            'validate': 'key',
            'validatecommand': (validate, '%W', '%P'),

            'justify': 'right',
            'relief': tk.FLAT,
            'borderwidth': 1,
            'highlightbackground': '#a0a0a0',
            'highlightcolor': '#606060',
            'highlightthickness': 1
        }

        tk.Entry(self, width=5, name='entry_red', textvariable=self._variables['red'], **defaults).grid(row=0, column=3, pady=3.5)
        tk.Entry(self, width=5, name='entry_green', textvariable=self._variables['green'], **defaults).grid(row=1, column=3, pady=3.5)
        tk.Entry(self, width=5, name='entry_blue', textvariable=self._variables['blue'], **defaults).grid(row=2, column=3, pady=3.5)
        tk.Entry(self, width=5, name='entry_lightness', textvariable=self._variables['lightness'], **defaults).grid(row=5, column=3, pady=3.5)
        tk.Entry(self, width=5, name='entry_chroma', textvariable=self._variables['chroma'], **defaults).grid(row=6, column=3, pady=3.5)
        tk.Entry(self, width=5, name='entry_hue', textvariable=self._variables['hue'], **defaults).grid(row=7, column=3, pady=3.5)

        del defaults['justify']
        tk.Entry(self, width=10, name='entry_hex', textvariable=self._variables['hex'], **defaults).grid(row=4, column=0)

        # sliders
        defaults = {
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

        tk.Scale(self, to=255, variable=self._variables['red'], **defaults).grid(row=0, column=4)
        tk.Scale(self, to=255, variable=self._variables['green'], **defaults).grid(row=1, column=4)
        tk.Scale(self, to=255, variable=self._variables['blue'], **defaults).grid(row=2, column=4)
        tk.Scale(self, to=100, resolution=0.1, variable=self._variables['lightness'], **defaults).grid(row=5, column=4)
        tk.Scale(self, to=132, resolution=0.1, variable=self._variables['chroma'], **defaults).grid(row=6, column=4)
        tk.Scale(self, to=360, resolution=0.1, variable=self._variables['hue'], **defaults).grid(row=7, column=4)


root = tk.Tk()
app = Karafuru(master=root)
app.mainloop()
