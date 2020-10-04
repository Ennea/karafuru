import math


# cube root
def _cbrt(n):
    return n ** (1 / 3)


# matrix multiplication
# this one is only capable of multiplying a 3x3 matrix
# with a 3x1 matrix, as this is all we need in here
def _matmul(matrix, components):
    components = (components,) * 3
    return tuple(v[0] * matrix[i][0] + v[1] * matrix[i][1] + v[2] * matrix[i][2] for (i, v) in enumerate(components))


# return true if the given sRGB values are outside the sRGB gamut
def _srgb_is_out_of_gamut(rgb):
    for value in rgb:
        if value < 0 or value > 1:
            return True
    return False


# convert an array of sRGB values in the range 0.0 - 1.0
# to linear light (un-companded) form
# https://en.wikipedia.org/wiki/SRGB
def _lin_srgb(rgb):
    return tuple(v / 12.92 if v < 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb)


# convert an array of linear-light sRGB values in the
# range 0.0 - 1.0 to gamma corrected form
# https://en.wikipedia.org/wiki/SRGB
def _gam_srgb(rgb):
    return tuple(1.055 * v ** (1 / 2.4) - 0.055 if v > 0.0031308 else 12.92 * v for v in rgb)


# convert an array of linear-light sRGB values to CIE XYZ
# using sRGB's own white, D65 (no chromatic adaptation)
# http://www.brucelindbloom.com/index.html?Eqn_RGB_XYZ_Matrix.html
# also
# https://www.image-engineering.de/library/technotes/958-how-to-convert-between-srgb-and-ciexyz
def _lin_srgb_to_xyz(rgb):
    matrix = (
        (0.4124564, 0.3575761, 0.1804375),
        (0.2126729, 0.7151522, 0.0721750),
        (0.0193339, 0.1191920, 0.9503041)
    )
    return _matmul(matrix, rgb)


# convert XYZ to linear-light sRGB
def _xyz_to_lin_srgb(xyz):
    matrix = (
        (3.2404542, -1.5371385, -0.4985314),
        (-0.9692660, 1.8760108, 0.0415560),
        (0.0556434, -0.2040259, 1.0572252)
    )
    return _matmul(matrix, xyz)


# adapt XYZ from D65 to D50 white point
def _d65_to_d50(xyz):
    matrix = (
        (1.0478112, 0.0228866, -0.0501270),
        (0.0295424, 0.9904844, -0.0170491),
        (-0.0092345, 0.0150436, 0.7521316)
    )
    return _matmul(matrix, xyz)


# adapt XYZ from D50 to D65 white point
def _d50_to_d65(xyz):
    matrix = (
        (0.9555766, -0.0230393, 0.0631636),
        (-0.0282895, 1.0099416, 0.0210077),
        (0.0122982, -0.0204830, 1.3299098)
    )
    return _matmul(matrix, xyz)


# assuming XYZ is relative to D50, convert to CIE Lab
def _xyz_to_lab(xyz):
    # from CIE standard, which now defines these as a rational fraction
    e = 216 / 24389  # 6^3/29^3
    k = 24389 / 27   # 29^3/3^3
    white = (0.96422, 1, 0.82521)  # D50 reference white

    # compute xyz, which is XYZ scaled relative to reference white
    xyz_ = tuple(v / white[i] for (i, v) in enumerate(xyz))

    # now compute f
    f = tuple(_cbrt(v) if v > e else (k * v + 16) / 116 for v in xyz_)

    return (
        (116 * f[1]) - 16,    # L
        500 * (f[0] - f[1]),  # a
        200 * (f[1] - f[2])   # b
    )


# convert Lab to D50-adapted XYZ
def _lab_to_xyz(lab):
    e = 216 / 24389  # 6^3/29^3
    k = 24389 / 27   # 29^3/3^3
    white = (0.96422, 1, 0.82521)  # D50 reference white

    # compute f, starting with the luminance-related term
    f = [0] * 3
    f[1] = (lab[0] + 16) / 116
    f[0] = lab[1] / 500 + f[1]
    f[2] = f[1] - lab[2] / 200

    # compute xyz
    xyz_ = (
        f[0] ** 3 if f[0] ** 3 > e else (116 * f[0] - 16) / k,
        ((lab[0] + 16) / 116) ** 3 if lab[0] > k * e else lab[0] / k,
        f[2] ** 3 if f[2] ** 3 > e else (116 * f[2] - 16) / k
    )

    # compute XYZ by scaling xyz by reference white
    return tuple(v * white[i] for (i, v) in enumerate(xyz_))


# convert to polar form
def _lab_to_lch(lab):
    hue = math.atan2(lab[2], lab[1]) * 180 / math.pi
    return (
        lab[0],  # lightness
        math.sqrt(lab[1] ** 2 + lab[2] ** 2),  # chroma
        hue if hue >= 0 else hue + 360  # hue
    )


# convert from polar form
def _lch_to_lab(lch):
    return (
        lch[0],  # lightness
        lch[1] * math.cos(lch[2] * math.pi / 180),  # a
        lch[1] * math.sin(lch[2] * math.pi / 180)   # b
    )


def lch_to_srgb(lch):
    # convert an array of CIE LCH values
    # to CIE Lab, and then to XYZ,
    # adapt from D50 to D65,
    # then convert XYZ to linear-light sRGB
    # and finally to gamma corrected sRGB
    # for in-gamut colors, components are in the 0.0 to 1.0 range
    # out of gamut colors may have negative components
    # or components greater than 1.0
    rgb = _gam_srgb(_xyz_to_lin_srgb(_d50_to_d65(_lab_to_xyz(_lch_to_lab(lch)))))

    # if the returned rgb values are out of gamut, find
    # a chroma via binary search where they aren't
    corrected = False
    if _srgb_is_out_of_gamut(rgb):
        corrected = True
        lower_chroma = 0
        upper_chroma = lch[1]
        chroma = lch[1] / 2

        while upper_chroma - lower_chroma > 0.01:
            rgb = _gam_srgb(_xyz_to_lin_srgb(_d50_to_d65(_lab_to_xyz(_lch_to_lab((lch[0], chroma, lch[2]))))))
            if _srgb_is_out_of_gamut(rgb):
                upper_chroma = chroma
            else:
                lower_chroma = chroma
            chroma = (lower_chroma + upper_chroma) / 2

        rgb = _gam_srgb(_xyz_to_lin_srgb(_d50_to_d65(_lab_to_xyz(_lch_to_lab((lch[0], lower_chroma, lch[2]))))))

    rgb = tuple(round(v, 10) for v in rgb)
    return (rgb, corrected)


def srgb_to_lch(rgb):
    # convert an array of gamma-corrected sRGB values
    # in the 0.0 to 1.0 range
    # to linear-light sRGB, then to CIE XYZ,
    # then adapt from D65 to D50,
    # then convert XYZ to CIE Lab
    # and finally, convert to CIE LCH
    return tuple(
        round(v, 1) for v in
        _lab_to_lch(_xyz_to_lab(_d65_to_d50(_lin_srgb_to_xyz(_lin_srgb(rgb)))))
    )
