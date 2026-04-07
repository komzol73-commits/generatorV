#!/usr/bin/env python3
"""
Cross-Stitch Pattern PDF Generator
Generates professional PDF patterns from images with DMC color palette.
Supports Cyrillic text via DejaVu Sans.
"""

import argparse, math, os, sys, io
from collections import Counter
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

# DMC to Gamma mapping (Russian thread brand)
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dmc_gamma_map import DMC_TO_GAMMA
except:
    DMC_TO_GAMMA = {}

# === reportlab imports ===
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Cyrillic fonts
FONT = 'DejaVuSans'
FONT_BOLD = 'DejaVuSans-Bold'
try:
    pdfmetrics.registerFont(TTFont(FONT, '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
except:
    FONT = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'

PAGE_W, PAGE_H = A4  # 595.27 x 841.89 points
MARGIN = 30

# === DMC Color Database (top ~120 most used colors) ===
DMC_COLORS = {
    "blanc": ("Белый", (255, 255, 255)),
    "310": ("Чёрный", (0, 0, 0)),
    "150": ("Dusty Rose-UL VY DK", (171, 2, 73)),
    "151": ("Dusty Rose-VY LT", (240, 206, 212)),
    "154": ("Grape-VY DK", (87, 36, 51)),
    "155": ("Blue Violet-MD DK", (152, 145, 182)),
    "208": ("Lavender-VY DK", (131, 91, 139)),
    "209": ("Lavender-DK", (163, 123, 167)),
    "210": ("Lavender-MD", (195, 159, 195)),
    "211": ("Lavender-LT", (227, 203, 227)),
    "221": ("Shell Pink-VY DK", (136, 62, 67)),
    "300": ("Mahogany-VY DK", (111, 47, 0)),
    "301": ("Mahogany-MD", (179, 95, 43)),
    "304": ("Christmas Red-MD", (183, 31, 51)),
    "307": ("Лимонный", (253, 237, 84)),
    "309": ("Rose-DK", (186, 74, 74)),
    "310": ("Black", (0, 0, 0)),
    "311": ("Navy Blue-MD", (28, 80, 102)),
    "312": ("Navy Blue-LT", (53, 102, 139)),
    "315": ("Antique Mauve-MD DK", (129, 73, 82)),
    "316": ("Antique Mauve-MD", (183, 115, 127)),
    "317": ("Pewter Gray", (108, 108, 108)),
    "318": ("Steel Gray-LT", (171, 171, 171)),
    "319": ("Pistachio Green-VY DK", (32, 95, 46)),
    "320": ("Pistachio Green-MD", (105, 136, 90)),
    "321": ("Christmas Red", (199, 0, 56)),
    "322": ("Navy Blue-VY LT", (90, 143, 184)),
    "326": ("Rose-VY DK", (179, 59, 75)),
    "327": ("Violet-VY DK", (99, 54, 102)),
    "333": ("Blue Violet-VY DK", (92, 84, 120)),
    "334": ("Baby Blue-MD", (92, 144, 192)),
    "335": ("Rose", (238, 84, 110)),
    "336": ("Navy Blue", (37, 59, 115)),
    "340": ("Blue Violet-MD", (173, 167, 199)),
    "341": ("Blue Violet-LT", (183, 191, 221)),
    "347": ("Salmon-VY DK", (191, 45, 45)),
    "349": ("Coral-DK", (210, 16, 53)),
    "350": ("Coral-MD", (224, 72, 72)),
    "351": ("Coral", (233, 106, 103)),
    "352": ("Coral-LT", (253, 156, 151)),
    "353": ("Peach", (254, 215, 204)),
    "355": ("Terra Cotta-DK", (152, 68, 54)),
    "356": ("Terra Cotta-MD", (197, 106, 91)),
    "367": ("Pistachio Green-DK", (97, 122, 82)),
    "368": ("Pistachio Green-LT", (166, 194, 152)),
    "369": ("Pistachio Green-VY LT", (215, 237, 204)),
    "370": ("Mustard-MD", (184, 157, 100)),
    "371": ("Mustard", (191, 166, 113)),
    "372": ("Mustard-LT", (204, 183, 132)),
    "400": ("Mahogany-DK", (143, 67, 15)),
    "402": ("Mahogany-VY LT", (247, 167, 119)),
    "407": ("Desert Sand-DK", (187, 131, 106)),
    "413": ("Pewter Gray-DK", (86, 86, 86)),
    "414": ("Steel Gray-DK", (140, 140, 140)),
    "415": ("Pearl Gray", (211, 211, 214)),
    "420": ("Hazelnut Brown-DK", (160, 112, 66)),
    "422": ("Hazelnut Brown-LT", (198, 159, 123)),
    "433": ("Brown-MD", (122, 69, 31)),
    "434": ("Brown-LT", (152, 94, 51)),
    "435": ("Brown-VY LT", (184, 119, 72)),
    "436": ("Tan", (203, 144, 81)),
    "437": ("Tan-LT", (228, 187, 142)),
    "444": ("Lemon-DK", (255, 214, 0)),
    "445": ("Lemon-LT", (255, 251, 139)),
    "451": ("Shell Gray-DK", (145, 123, 115)),
    "452": ("Shell Gray-MD", (192, 179, 174)),
    "453": ("Shell Gray-LT", (215, 206, 203)),
    "469": ("Avocado Green", (114, 132, 60)),
    "470": ("Avocado Green-LT", (148, 171, 79)),
    "471": ("Avocado Green-VY LT", (174, 191, 121)),
    "472": ("Avocado Green-UL LT", (216, 228, 152)),
    "498": ("Christmas Red-DK", (167, 19, 43)),
    "500": ("Blue Green-VY DK", (4, 77, 51)),
    "501": ("Blue Green-DK", (57, 111, 82)),
    "502": ("Blue Green", (91, 144, 113)),
    "503": ("Blue Green-MD", (123, 172, 148)),
    "504": ("Blue Green-VY LT", (196, 222, 204)),
    "517": ("Wedgwood-DK", (16, 127, 135)),
    "518": ("Wedgwood-LT", (79, 147, 167)),
    "519": ("Sky Blue", (126, 177, 200)),
    "520": ("Fern Green-DK", (102, 109, 79)),
    "522": ("Fern Green", (150, 158, 126)),
    "523": ("Fern Green-LT", (171, 177, 151)),
    "524": ("Fern Green-VY LT", (196, 205, 172)),
    "535": ("Ash Gray-VY LT", (99, 100, 88)),
    "543": ("Beige Brown-UL VY LT", (242, 227, 206)),
    "550": ("Violet-VY DK", (92, 24, 78)),
    "552": ("Violet-MD", (128, 58, 107)),
    "553": ("Violet", (163, 99, 139)),
    "554": ("Violet-LT", (219, 179, 203)),
    "561": ("Jade-VY DK", (44, 106, 69)),
    "562": ("Jade-MD", (83, 151, 106)),
    "563": ("Jade-LT", (143, 192, 152)),
    "564": ("Jade-VY LT", (167, 205, 175)),
    "580": ("Moss Green-DK", (136, 141, 51)),
    "581": ("Moss Green", (167, 174, 56)),
    "597": ("Turquoise", (91, 163, 174)),
    "598": ("Turquoise-LT", (144, 195, 204)),
    "600": ("Cranberry-VY DK", (205, 47, 99)),
    "601": ("Cranberry-DK", (209, 40, 106)),
    "602": ("Cranberry-MD", (226, 72, 116)),
    "603": ("Cranberry", (255, 115, 140)),
    "604": ("Cranberry-LT", (255, 176, 190)),
    "605": ("Cranberry-VY LT", (255, 192, 205)),
    "606": ("Bright Orange Red", (250, 50, 3)),
    "608": ("Bright Orange", (253, 93, 53)),
    "610": ("Drab Brown-DK", (121, 96, 71)),
    "611": ("Drab Brown", (150, 118, 86)),
    "612": ("Drab Brown-LT", (188, 154, 120)),
    "613": ("Drab Brown-VY LT", (220, 196, 170)),
    "632": ("Desert Sand-UL VY DK", (135, 85, 57)),
    "640": ("Beige Gray-VY DK", (133, 123, 108)),
    "642": ("Beige Gray-DK", (164, 152, 120)),
    "644": ("Beige Gray-MD", (221, 216, 203)),
    "645": ("Beaver Gray-VY DK", (110, 101, 92)),
    "646": ("Beaver Gray-DK", (135, 125, 115)),
    "647": ("Beaver Gray-MD", (176, 166, 156)),
    "648": ("Beaver Gray-LT", (188, 180, 172)),
    "666": ("Christmas Red-BRT", (227, 29, 66)),
    "676": ("Old Gold-LT", (229, 206, 151)),
    "677": ("Old Gold-VY LT", (245, 236, 203)),
    "680": ("Old Gold-DK", (188, 141, 14)),
    "699": ("Christmas Green", (5, 101, 23)),
    "700": ("Christmas Green-BRT", (7, 115, 27)),
    "701": ("Christmas Green-LT", (63, 143, 41)),
    "702": ("Kelly Green", (71, 167, 47)),
    "703": ("Chartreuse", (123, 181, 71)),
    "704": ("Chartreuse-BRT", (158, 207, 52)),
    "712": ("Cream", (255, 251, 239)),
    "718": ("Plum", (156, 36, 98)),
    "720": ("Orange Spice-DK", (229, 92, 31)),
    "721": ("Orange Spice-MD", (242, 120, 66)),
    "722": ("Orange Spice-LT", (247, 151, 111)),
    "725": ("Topaz", (255, 200, 64)),
    "726": ("Topaz-LT", (253, 215, 85)),
    "727": ("Topaz-VY LT", (255, 241, 175)),
    "728": ("Topaz-MD", (228, 180, 104)),
    "729": ("Old Gold-MD", (208, 165, 62)),
    "730": ("Olive Green-VY DK", (130, 123, 48)),
    "731": ("Olive Green-DK", (147, 139, 55)),
    "732": ("Olive Green", (148, 140, 54)),
    "733": ("Olive Green-MD", (188, 179, 76)),
    "734": ("Olive Green-LT", (199, 192, 119)),
    "738": ("Tan-VY LT", (236, 204, 158)),
    "739": ("Tan-UL VY LT", (248, 228, 200)),
    "740": ("Tangerine", (255, 131, 19)),
    "741": ("Tangerine-MD", (255, 142, 4)),
    "742": ("Tangerine-LT", (255, 183, 85)),
    "743": ("Yellow-MD", (254, 211, 118)),
    "744": ("Yellow-Pale", (255, 231, 147)),
    "745": ("Yellow-LT Pale", (255, 233, 173)),
    "746": ("Off White", (252, 252, 238)),
    "747": ("Sky Blue-VY LT", (229, 252, 253)),
    "754": ("Peach-LT", (247, 203, 191)),
    "758": ("Terra Cotta-VY LT", (238, 170, 155)),
    "760": ("Salmon", (245, 173, 173)),
    "761": ("Salmon-LT", (255, 201, 201)),
    "762": ("Pearl Gray-VY LT", (236, 236, 236)),
    "772": ("Yellow Green-VY LT", (228, 236, 212)),
    "775": ("Baby Blue-VY LT", (217, 235, 241)),
    "776": ("Pink-MD", (252, 176, 185)),
    "778": ("Antique Mauve-VY LT", (223, 179, 187)),
    "780": ("Topaz-UL VY DK", (148, 99, 26)),
    "781": ("Topaz-VY DK", (162, 109, 32)),
    "782": ("Topaz-DK", (174, 119, 32)),
    "783": ("Topaz-MD", (206, 145, 36)),
    "791": ("Cornflower Blue-VY DK", (70, 69, 99)),
    "792": ("Cornflower Blue-DK", (85, 91, 123)),
    "793": ("Cornflower Blue-MD", (112, 125, 162)),
    "794": ("Cornflower Blue-LT", (143, 156, 193)),
    "796": ("Royal Blue-DK", (17, 65, 109)),
    "797": ("Royal Blue", (19, 71, 125)),
    "798": ("Delft Blue-DK", (70, 106, 142)),
    "799": ("Delft Blue-MD", (116, 142, 182)),
    "800": ("Delft Blue-Pale", (192, 204, 222)),
    "801": ("Coffee Brown-DK", (101, 57, 25)),
    "806": ("Peacock Blue-DK", (61, 149, 165)),
    "807": ("Peacock Blue", (100, 171, 186)),
    "809": ("Delft Blue", (148, 168, 198)),
    "813": ("Blue-LT", (161, 194, 215)),
    "814": ("Garnet-DK", (123, 0, 27)),
    "815": ("Garnet-MD", (135, 7, 31)),
    "816": ("Garnet", (151, 11, 35)),
    "817": ("Coral Red-VY DK", (187, 5, 31)),
    "818": ("Baby Pink", (255, 223, 217)),
    "819": ("Baby Pink-LT", (255, 238, 235)),
    "820": ("Royal Blue-VY DK", (14, 54, 92)),
    "822": ("Beige Gray-LT", (231, 226, 211)),
    "823": ("Navy Blue-DK", (33, 48, 99)),
    "824": ("Blue-VY DK", (57, 105, 135)),
    "825": ("Blue-DK", (71, 129, 165)),
    "826": ("Blue-MD", (107, 158, 191)),
    "827": ("Blue-VY LT", (189, 221, 237)),
    "828": ("Blue-UL VY LT", (197, 232, 237)),
    "829": ("Golden Olive-VY DK", (126, 107, 66)),
    "830": ("Golden Olive-DK", (141, 120, 73)),
    "831": ("Golden Olive-MD", (170, 143, 86)),
    "832": ("Golden Olive", (189, 155, 81)),
    "833": ("Golden Olive-LT", (200, 171, 108)),
    "834": ("Golden Olive-VY LT", (219, 190, 127)),
    "838": ("Beige Brown-VY DK", (89, 73, 55)),
    "839": ("Beige Brown-DK", (103, 85, 65)),
    "840": ("Beige Brown-MD", (154, 124, 92)),
    "841": ("Beige Brown-LT", (182, 155, 126)),
    "842": ("Beige Brown-VY LT", (209, 186, 161)),
    "844": ("Beaver Gray-UL DK", (72, 72, 72)),
    "869": ("Hazelnut Brown-VY DK", (131, 94, 57)),
    "890": ("Pistachio Green-UL DK", (23, 73, 35)),
    "891": ("Carnation-DK", (255, 87, 115)),
    "892": ("Carnation-MD", (255, 121, 140)),
    "893": ("Carnation-LT", (252, 144, 162)),
    "894": ("Carnation-VY LT", (255, 178, 187)),
    "895": ("Hunter Green-VY DK", (27, 83, 0)),
    "898": ("Coffee Brown-VY DK", (73, 42, 19)),
    "899": ("Rose-MD", (242, 118, 136)),
    "900": ("Burnt Orange-DK", (209, 88, 7)),
    "902": ("Garnet-VY DK", (130, 38, 55)),
    "904": ("Parrot Green-VY DK", (85, 120, 34)),
    "905": ("Parrot Green-DK", (98, 138, 40)),
    "906": ("Parrot Green-MD", (127, 179, 53)),
    "907": ("Parrot Green-LT", (199, 230, 102)),
    "909": ("Emerald Green-VY DK", (21, 111, 73)),
    "910": ("Emerald Green-DK", (24, 126, 86)),
    "911": ("Emerald Green-MD", (24, 144, 101)),
    "912": ("Emerald Green-LT", (27, 157, 107)),
    "913": ("Nile Green-MD", (109, 171, 119)),
    "915": ("Plum-DK", (130, 0, 67)),
    "917": ("Plum-MD", (155, 19, 89)),
    "918": ("Red Copper-DK", (130, 52, 10)),
    "919": ("Red Copper", (166, 69, 16)),
    "920": ("Copper-MD", (172, 84, 20)),
    "921": ("Copper", (198, 98, 24)),
    "922": ("Copper-LT", (226, 115, 35)),
    "924": ("Gray Green-VY DK", (86, 106, 106)),
    "926": ("Gray Green-MD", (152, 174, 174)),
    "927": ("Gray Green-LT", (189, 203, 203)),
    "928": ("Gray Green-VY LT", (221, 227, 227)),
    "930": ("Antique Blue-DK", (69, 92, 113)),
    "931": ("Antique Blue-MD", (106, 133, 158)),
    "932": ("Antique Blue-LT", (162, 181, 198)),
    "934": ("Black Avocado Green", (49, 57, 25)),
    "935": ("Avocado Green-DK", (66, 77, 33)),
    "936": ("Avocado Green-VY DK", (76, 88, 38)),
    "937": ("Avocado Green-MD", (98, 113, 51)),
    "938": ("Coffee Brown-UL DK", (54, 31, 14)),
    "939": ("Navy Blue-VY DK", (27, 40, 83)),
    "943": ("Aquamarine-MD", (61, 147, 132)),
    "945": ("Tawny", (251, 213, 187)),
    "946": ("Burnt Orange-MD", (235, 99, 7)),
    "947": ("Burnt Orange", (255, 123, 77)),
    "948": ("Peach-VY LT", (254, 231, 218)),
    "950": ("Desert Sand-LT", (238, 211, 196)),
    "951": ("Tawny-LT", (255, 226, 207)),
    "954": ("Nile Green", (136, 186, 145)),
    "955": ("Nile Green-LT", (162, 214, 173)),
    "956": ("Geranium", (255, 145, 145)),
    "957": ("Geranium-Pale", (253, 181, 181)),
    "958": ("Sea Green-DK", (62, 182, 161)),
    "959": ("Sea Green-MD", (89, 199, 180)),
    "961": ("Dusty Rose-DK", (207, 115, 115)),
    "962": ("Dusty Rose-MD", (230, 138, 138)),
    "963": ("Dusty Rose-UL VY LT", (255, 215, 215)),
    "964": ("Sea Green-LT", (169, 226, 216)),
    "966": ("Baby Green-MD", (185, 215, 192)),
    "970": ("Pumpkin-LT", (247, 139, 19)),
    "971": ("Pumpkin", (246, 127, 0)),
    "972": ("Canary-DK", (255, 181, 21)),
    "973": ("Canary-BRT", (255, 227, 0)),
    "975": ("Golden Brown-DK", (145, 79, 18)),
    "976": ("Golden Brown-MD", (194, 129, 44)),
    "977": ("Golden Brown-LT", (220, 156, 68)),
    "986": ("Forest Green-VY DK", (64, 82, 48)),
    "987": ("Forest Green-DK", (88, 113, 65)),
    "988": ("Forest Green-MD", (115, 139, 91)),
    "989": ("Forest Green", (141, 166, 117)),
    "991": ("Aquamarine-DK", (71, 123, 110)),
    "992": ("Aquamarine-LT", (111, 174, 159)),
    "993": ("Aquamarine-VY LT", (144, 192, 180)),
    "995": ("Electric Blue-DK", (38, 150, 182)),
    "996": ("Electric Blue-MD", (48, 194, 236)),
    "3011": ("Khaki Green-DK", (137, 138, 88)),
    "3012": ("Khaki Green-MD", (166, 167, 93)),
    "3013": ("Khaki Green-LT", (185, 185, 130)),
    "3021": ("Brown Gray-VY DK", (79, 75, 65)),
    "3022": ("Brown Gray-MD", (142, 144, 120)),
    "3023": ("Brown Gray-LT", (177, 170, 151)),
    "3024": ("Brown Gray-VY LT", (235, 234, 231)),
    "3031": ("Mocha Brown-VY DK", (75, 60, 42)),
    "3032": ("Mocha Brown-MD", (179, 159, 139)),
    "3033": ("Mocha Brown-VY LT", (227, 216, 204)),
    "3045": ("Yellow Beige-DK", (188, 150, 106)),
    "3046": ("Yellow Beige-MD", (216, 188, 154)),
    "3047": ("Yellow Beige-LT", (231, 214, 193)),
    "3051": ("Green Gray-DK", (95, 102, 72)),
    "3052": ("Green Gray-MD", (136, 146, 104)),
    "3053": ("Green Gray", (156, 164, 130)),
    "3064": ("Desert Sand-VY LT", (208, 166, 142)),
    "3072": ("Beaver Gray-VY LT", (230, 232, 232)),
    "3078": ("Golden Yellow-VY LT", (253, 249, 205)),
    "3325": ("Baby Blue-LT", (184, 210, 230)),
    "3326": ("Rose-LT", (251, 173, 180)),
    "3328": ("Salmon-DK", (227, 109, 109)),
    "3340": ("Apricot-MD", (255, 131, 111)),
    "3341": ("Apricot", (252, 171, 152)),
    "3345": ("Hunter Green-DK", (27, 89, 21)),
    "3346": ("Hunter Green", (64, 106, 58)),
    "3347": ("Yellow Green-MD", (113, 147, 92)),
    "3348": ("Yellow Green-LT", (204, 217, 177)),
    "3350": ("Dusty Rose-UL DK", (188, 67, 101)),
    "3354": ("Dusty Rose-LT", (228, 166, 172)),
    "3362": ("Pine Green-DK", (94, 107, 71)),
    "3363": ("Pine Green-MD", (114, 130, 86)),
    "3364": ("Pine Green", (131, 151, 95)),
    "3371": ("Black Brown", (30, 17, 8)),
    "3607": ("Plum-LT", (197, 73, 137)),
    "3608": ("Plum-VY LT", (234, 156, 196)),
    "3609": ("Plum-UL LT", (244, 174, 213)),
    "3685": ("Mauve-VY DK", (136, 21, 49)),
    "3687": ("Mauve", (201, 107, 112)),
    "3688": ("Mauve-MD", (231, 169, 172)),
    "3689": ("Mauve-LT", (251, 191, 194)),
    "3705": ("Melon-DK", (255, 121, 146)),
    "3706": ("Melon-MD", (255, 173, 188)),
    "3708": ("Melon-LT", (255, 203, 213)),
    "3712": ("Salmon-MD", (241, 135, 135)),
    "3713": ("Salmon-VY LT", (255, 226, 226)),
    "3716": ("Dusty Rose-VY LT", (255, 189, 189)),
    "3721": ("Shell Pink-DK", (161, 75, 81)),
    "3722": ("Shell Pink-MD", (188, 108, 100)),
    "3726": ("Antique Mauve-DK", (155, 91, 102)),
    "3727": ("Antique Mauve-LT", (219, 169, 178)),
    "3731": ("Dusty Rose-VY DK", (218, 103, 131)),
    "3733": ("Dusty Rose", (232, 135, 155)),
    "3740": ("Antique Violet-DK", (120, 87, 98)),
    "3743": ("Antique Violet-VY LT", (215, 203, 211)),
    "3746": ("Blue Violet-DK", (119, 107, 152)),
    "3747": ("Blue Violet-VY LT", (211, 215, 237)),
    "3750": ("Antique Blue-VY DK", (56, 76, 94)),
    "3752": ("Antique Blue-VY LT", (199, 209, 219)),
    "3753": ("Antique Blue-UL VY LT", (219, 226, 233)),
    "3755": ("Baby Blue", (147, 180, 206)),
    "3756": ("Baby Blue-UL VY LT", (238, 252, 252)),
    "3760": ("Wedgwood-MD", (62, 133, 162)),
    "3761": ("Sky Blue-LT", (172, 216, 226)),
    "3765": ("Peacock Blue-VY DK", (52, 127, 140)),
    "3766": ("Peacock Blue-LT", (99, 163, 173)),
    "3768": ("Gray Green-DK", (101, 127, 127)),
    "3770": ("Tawny-VY LT", (255, 238, 227)),
    "3771": ("Terra Cotta-UL VY LT", (244, 187, 169)),
    "3772": ("Desert Sand-MD", (160, 108, 80)),
    "3773": ("Desert Sand", (182, 117, 82)),
    "3774": ("Desert Sand-VY LT", (243, 225, 215)),
    "3776": ("Mahogany-LT", (207, 121, 57)),
    "3777": ("Terra Cotta-VY DK", (134, 48, 34)),
    "3778": ("Terra Cotta-LT", (217, 137, 120)),
    "3779": ("Terra Cotta-UL VY LT", (248, 202, 200)),
    "3781": ("Mocha Brown-DK", (107, 87, 67)),
    "3782": ("Mocha Brown-LT", (210, 188, 166)),
    "3787": ("Brown Gray-DK", (98, 93, 80)),
    "3790": ("Beige Gray-UL DK", (127, 106, 85)),
    "3799": ("Pewter Gray-VY DK", (66, 66, 66)),
    "3801": ("Melon-VY DK", (231, 73, 103)),
    "3802": ("Antique Mauve-VY DK", (113, 65, 73)),
    "3803": ("Mauve-DK", (171, 51, 87)),
    "3804": ("Cyclamen Pink-DK", (224, 40, 118)),
    "3805": ("Cyclamen Pink", (243, 71, 139)),
    "3806": ("Cyclamen Pink-LT", (255, 140, 174)),
    "3807": ("Cornflower Blue", (96, 103, 140)),
    "3808": ("Turquoise-UL VY DK", (54, 105, 112)),
    "3809": ("Turquoise-VY DK", (63, 124, 133)),
    "3810": ("Turquoise-DK", (72, 142, 154)),
    "3811": ("Turquoise-VY LT", (188, 227, 230)),
    "3812": ("Sea Green-VY DK", (47, 140, 132)),
    "3813": ("Blue Green-LT", (178, 212, 189)),
    "3814": ("Aquamarine", (80, 139, 125)),
    "3815": ("Celadon Green-DK", (71, 119, 89)),
    "3816": ("Celadon Green", (101, 165, 125)),
    "3817": ("Celadon Green-LT", (153, 195, 170)),
    "3818": ("Emerald Green-UL VY DK", (17, 90, 59)),
    "3819": ("Moss Green-LT", (224, 232, 104)),
    "3820": ("Straw-DK", (223, 182, 95)),
    "3821": ("Straw", (243, 206, 117)),
    "3822": ("Straw-LT", (246, 220, 152)),
    "3823": ("Yellow-UL Pale", (255, 253, 227)),
    "3824": ("Apricot-LT", (254, 205, 194)),
    "3825": ("Pumpkin-Pale", (253, 189, 150)),
    "3826": ("Golden Brown", (173, 114, 57)),
    "3827": ("Golden Brown-Pale", (247, 187, 119)),
    "3828": ("Hazelnut Brown", (183, 139, 97)),
    "3829": ("Old Gold-VY DK", (169, 130, 4)),
    "3830": ("Terra Cotta", (185, 85, 68)),
    "3831": ("Raspberry-DK", (179, 47, 72)),
    "3832": ("Raspberry-MD", (219, 85, 110)),
    "3833": ("Raspberry-LT", (234, 134, 153)),
    "3834": ("Grape-DK", (114, 55, 93)),
    "3835": ("Grape-MD", (148, 96, 131)),
    "3836": ("Grape-LT", (186, 145, 170)),
    "3837": ("Lavender-UL DK", (108, 58, 110)),
    "3838": ("Lavender Blue-DK", (92, 114, 148)),
    "3839": ("Lavender Blue-MD", (123, 142, 171)),
    "3840": ("Lavender Blue-LT", (176, 192, 218)),
    "3841": ("Baby Blue-Pale", (205, 223, 237)),
    "3842": ("Wedgwood-DK", (50, 102, 124)),
    "3843": ("Electric Blue", (20, 170, 208)),
    "3844": ("Bright Turquoise-DK", (18, 174, 186)),
    "3845": ("Bright Turquoise-MD", (4, 196, 202)),
    "3846": ("Bright Turquoise-LT", (6, 227, 230)),
    "3847": ("Teal Green-DK", (52, 125, 117)),
    "3848": ("Teal Green-MD", (85, 156, 148)),
    "3849": ("Teal Green-LT", (82, 179, 164)),
    "3850": ("Bright Green-DK", (55, 132, 119)),
    "3851": ("Bright Green-LT", (73, 179, 161)),
    "3852": ("Straw-VY DK", (205, 157, 55)),
    "3853": ("Autumn Gold-DK", (242, 151, 70)),
    "3854": ("Autumn Gold-MD", (242, 175, 104)),
    "3855": ("Autumn Gold-LT", (250, 211, 150)),
    "3856": ("Mahogany-UL VY LT", (255, 211, 181)),
    "3857": ("Rosewood-DK", (104, 37, 26)),
    "3858": ("Rosewood-MD", (150, 74, 63)),
    "3859": ("Rosewood-LT", (186, 139, 124)),
    "3860": ("Cocoa", (125, 93, 87)),
    "3861": ("Cocoa-LT", (166, 136, 129)),
    "3862": ("Mocha Beige-DK", (138, 110, 78)),
    "3863": ("Mocha Beige-MD", (164, 131, 92)),
    "3864": ("Mocha Beige-LT", (203, 182, 156)),
    "3865": ("Winter White", (249, 247, 241)),
    "3866": ("Mocha Brn-UL VY LT", (250, 246, 240)),
}

# Symbols for chart (38 unique, easily distinguishable)
SYMBOLS = list("★ABTFWRн■●LVSKEDYZHMGNCU+×◆▲♥badeP")
EXTRA_SYMBOLS = list("☆◇○□△▽◎✦✧❖⬟⬡⬢⬣⊕⊗⊙⊛⊞⊟⊠⊡")
ALL_SYMBOLS = SYMBOLS + EXTRA_SYMBOLS


def find_nearest_dmc(rgb, palette):
    """Find the closest DMC color to the given RGB value."""
    min_dist = float('inf')
    best = None
    for code, (name, dmc_rgb) in palette.items():
        dist = sum((a - b) ** 2 for a, b in zip(rgb, dmc_rgb))
        if dist < min_dist:
            min_dist = dist
            best = code
    return best


def image_to_pattern(image_path, target_width, max_colors):
    """Convert an image to a cross-stitch pattern grid."""
    img = Image.open(image_path).convert('RGB')
    w, h = img.size
    target_height = int(target_width * h / w)

    # Resize to target stitch dimensions
    img_resized = img.resize((target_width, target_height), Image.LANCZOS)
    pixels = np.array(img_resized).reshape(-1, 3)

    # Quantize colors using KMeans
    n_colors = min(max_colors, len(set(map(tuple, pixels))))
    kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
    kmeans.fit(pixels)
    centroids = kmeans.cluster_centers_.astype(int)
    labels = kmeans.labels_

    # Map each centroid to nearest DMC color
    dmc_map = {}
    used_codes = set()
    for i, centroid in enumerate(centroids):
        palette_copy = {k: v for k, v in DMC_COLORS.items() if k not in used_codes}
        code = find_nearest_dmc(tuple(centroid), palette_copy)
        dmc_map[i] = code
        used_codes.add(code)

    # Build the grid
    grid = labels.reshape(target_height, target_width)
    dmc_grid = [[dmc_map[grid[r][c]] for c in range(target_width)] for r in range(target_height)]

    # Count stitches per color
    stitch_counts = Counter()
    for row in dmc_grid:
        for code in row:
            stitch_counts[code] += 1

    # Sort by count descending
    sorted_colors = sorted(stitch_counts.keys(), key=lambda c: -stitch_counts[c])

    # Assign symbols
    color_symbols = {}
    for i, code in enumerate(sorted_colors):
        color_symbols[code] = ALL_SYMBOLS[i] if i < len(ALL_SYMBOLS) else chr(9312 + i)

    return dmc_grid, stitch_counts, color_symbols, target_height, target_width, img_resized


# === BLEND SYMBOLS (distinct from main symbols) ===
BLEND_SYMBOLS = list("①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳")


def detect_blends(dmc_grid, stitch_counts, color_symbols):
    """Auto-detect transition zones and create blend entries.
    Returns: blend_grid (dict of (y,x)->(code1,code2)), updated stitch_counts, color_symbols.
    Blend keys are 'b:CODE1+CODE2' (sorted)."""
    grid_h = len(dmc_grid)
    grid_w = len(dmc_grid[0])
    blend_counts = {}  # (code1, code2) -> count
    blend_positions = {}  # (y, x) -> (code1, code2)

    for y in range(grid_h):
        for x in range(grid_w):
            code = dmc_grid[y][x]
            neighbors = set()
            for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < grid_h and 0 <= nx < grid_w:
                    nc = dmc_grid[ny][nx]
                    if nc != code:
                        neighbors.add(nc)
            # Only blend if exactly on a 2-color boundary (1 different neighbor color)
            if len(neighbors) == 1:
                other = neighbors.pop()
                pair = tuple(sorted([code, other]))
                # Only count if this pixel has >=2 same-color neighbors (not isolated)
                same_count = 0
                for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < grid_h and 0 <= nx < grid_w and dmc_grid[ny][nx] == code:
                        same_count += 1
                if same_count >= 1:
                    blend_counts[pair] = blend_counts.get(pair, 0) + 1
                    blend_positions[(y, x)] = pair

    # Only keep blend pairs with enough stitches (>= 20) to be meaningful
    valid_blends = {p for p, c in blend_counts.items() if c >= 20}
    # Filter positions
    blend_positions = {pos: pair for pos, pair in blend_positions.items() if pair in valid_blends}

    # Sort blends by count descending
    sorted_blends = sorted(valid_blends, key=lambda p: -blend_counts[p])
    # Limit to available blend symbols
    sorted_blends = sorted_blends[:len(BLEND_SYMBOLS)]

    # Create blend entries
    blend_symbols = {}
    for i, pair in enumerate(sorted_blends):
        key = f"b:{pair[0]}+{pair[1]}"
        blend_symbols[key] = BLEND_SYMBOLS[i]
        stitch_counts[key] = blend_counts[pair]
        color_symbols[key] = BLEND_SYMBOLS[i]

    # Build pair->key mapping
    pair_to_key = {pair: f"b:{pair[0]}+{pair[1]}" for pair in sorted_blends}

    # Update grid
    blend_grid = {}
    for (y, x), pair in blend_positions.items():
        if pair in pair_to_key:
            key = pair_to_key[pair]
            blend_grid[(y, x)] = pair
            dmc_grid[y][x] = key
            # Adjust original color counts
            orig_code = pair[0] if dmc_grid[y][x] == key else pair[1]
            # Already replaced, find which was original by checking neighbors
            # Just decrement both slightly - counts are approximate anyway

    n_blends = len(sorted_blends)
    n_stitches = sum(blend_counts[p] for p in sorted_blends) if sorted_blends else 0
    print(f"Blends: {n_blends} pairs, {n_stitches} stitches")
    return blend_grid, sorted_blends


def get_color_rgb(code):
    """Get RGB tuple for a code, including blend codes 'b:X+Y'."""
    if str(code).startswith("b:"):
        parts = str(code)[2:].split("+")
        _, rgb1 = DMC_COLORS.get(parts[0], ("?", (128,128,128)))
        _, rgb2 = DMC_COLORS.get(parts[1], ("?", (128,128,128)))
        return tuple((a+b)//2 for a,b in zip(rgb1, rgb2))
    _, rgb = DMC_COLORS.get(code, ("?", (128,128,128)))
    return rgb


def draw_footer(c, page_w, page_h, brand, brand_note, margin=MARGIN):
    """Draw footer with brand and copyright."""
    c.setFont(FONT, 7)
    c.setFillColor(colors.Color(0.5, 0.5, 0.5))
    footer_text = f"{brand}  —  {brand_note}" if brand_note else brand
    c.drawCentredString(page_w / 2, margin - 15, footer_text)


def create_title_page(c, title, grid_h, grid_w, n_colors, total_stitches,
                      aida, brand, brand_note, preview_img):
    """Page 1: Header → preview image → info box → included → footer.
    The preview image always sits between the title bar and the info section,
    scaled to fill available space while keeping aspect ratio."""

    # === 1. HEADER BAR (top) ===
    header_h = 80
    c.setFillColor(colors.Color(0.2, 0.3, 0.2))
    c.rect(0, PAGE_H - header_h, PAGE_W, header_h, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont(FONT_BOLD, 22)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 45, title)
    c.setFont(FONT, 10)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 68, "Cross-stitch pattern PDF")

    # === 2. CALCULATE BOTTOM SECTION HEIGHT ===
    # Info box: 7 lines × 22pt + padding
    cm_w = round(grid_w / aida * 2.54, 1)
    cm_h = round(grid_h / aida * 2.54, 1)
    canvas_w = round(cm_w + 16, 0)
    canvas_h = round(cm_h + 16, 0)

    info_lines = [
        ("Размер:", f"{grid_w} × {grid_h} стежков | на канве {aida} ct: {cm_w} × {cm_h} см"),
        ("Канва:", f"Aida {aida} ct: {int(canvas_w)} × {int(canvas_h)} см (с запасом 8 см)"),
        ("Палитра:", f"{n_colors} цветов (DMC)"),
        ("Всего стежков:", f"{total_stitches:,}"),
        ("Сложность:", "Средняя" if n_colors > 20 else "Начинающий"),
        ("Тип стежка:", "Полный крест (2 нити)"),
    ]
    includes = [
        "Цветной превью (пиксельный рендер)",
        "Рендер стежков на канве с картой зон",
        "Легенда цветов DMC + Гамма с символами",
        "Цветовая схема с символами",
    ]

    info_box_h = len(info_lines) * 22 + 30  # lines + padding
    includes_h = 20 + len(includes) * 16 + 10  # header + lines + gap
    separator_h = 15
    bottom_section_h = info_box_h + separator_h + includes_h
    footer_margin = 30

    # === 3. PREVIEW IMAGE (fills space between header and info) ===
    img_top = PAGE_H - header_h - 15  # 15pt gap below header
    img_bottom = footer_margin + bottom_section_h + 15  # 15pt gap above info
    avail_h_for_img = img_top - img_bottom
    avail_w_for_img = PAGE_W - 2 * MARGIN - 40

    if preview_img and avail_h_for_img > 80:
        buf = io.BytesIO()
        preview_img.save(buf, format='PNG')
        buf.seek(0)
        from reportlab.lib.utils import ImageReader
        ir = ImageReader(buf)

        aspect = grid_w / grid_h
        # Fit to available rectangle
        img_w_pts = min(avail_w_for_img, avail_h_for_img * aspect)
        img_h_pts = img_w_pts / aspect
        if img_h_pts > avail_h_for_img:
            img_h_pts = avail_h_for_img
            img_w_pts = img_h_pts * aspect

        x_img = (PAGE_W - img_w_pts) / 2
        y_img = img_bottom + (avail_h_for_img - img_h_pts) / 2  # centered vertically

        # Border
        c.setStrokeColor(colors.Color(0.6, 0.5, 0.3))
        c.setLineWidth(3)
        c.rect(x_img - 5, y_img - 5, img_w_pts + 10, img_h_pts + 10)
        c.drawImage(ir, x_img, y_img, img_w_pts, img_h_pts)

    # === 4. INFO BOX (bottom section) ===
    box_top = footer_margin + bottom_section_h
    box_y = box_top - info_box_h
    c.setFillColor(colors.Color(0.96, 0.96, 0.96))
    c.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
    c.setLineWidth(0.5)
    c.roundRect(MARGIN, box_y, PAGE_W - 2 * MARGIN, info_box_h, 4, fill=True, stroke=True)

    y = box_y + info_box_h - 22
    for label, value in info_lines:
        c.setFont(FONT_BOLD, 9)
        c.setFillColor(colors.Color(0.2, 0.2, 0.2))
        c.drawString(MARGIN + 15, y, label)
        c.setFont(FONT, 9)
        c.drawString(MARGIN + 100, y, value)
        y -= 22

    # === 5. INCLUDED SECTION ===
    y_inc = box_y - separator_h
    c.setFont(FONT_BOLD, 9)
    c.setFillColor(colors.Color(0.2, 0.2, 0.2))
    c.drawString(MARGIN + 5, y_inc, "Включено:")
    for item in includes:
        y_inc -= 16
        c.setFont(FONT, 9)
        c.drawString(MARGIN + 20, y_inc, f"→ {item}")

    # === 6. FOOTER ===
    draw_footer(c, PAGE_W, PAGE_H, brand, brand_note)
    c.showPage()


def create_stitch_render_page(c, title, dmc_grid, color_symbols, stitch_counts,
                               brand, brand_note, cell_size_mm=4.0):
    """Page 2: Stitch render on simulated Aida canvas, 30% lighter, with zone map."""
    c.setFont(FONT_BOLD, 11)
    c.setFillColor(colors.Color(0.2, 0.2, 0.2))
    c.drawString(MARGIN, PAGE_H - 40, "Имитация стежков на канве")
    c.setFont(FONT, 8)
    c.drawString(MARGIN, PAGE_H - 55,
                 "Для оценки внешнего вида готовой работы. Линии показывают зоны страниц схемы.")

    grid_h = len(dmc_grid)
    grid_w = len(dmc_grid[0])

    avail_w = PAGE_W - 2 * MARGIN - 20
    avail_h = PAGE_H - 100
    cell = min(avail_w / grid_w, avail_h / grid_h)
    total_w = cell * grid_w
    total_h = cell * grid_h
    x0 = (PAGE_W - total_w) / 2
    y0 = PAGE_H - 70 - total_h

    # Draw canvas background
    c.setFillColor(colors.Color(0.95, 0.93, 0.88))
    c.rect(x0 - 5, y0 - 5, total_w + 10, total_h + 10, fill=True)

    # Lighten factor: 30%
    LIGHTEN = 0.30

    for r in range(grid_h):
        for col in range(grid_w):
            code = dmc_grid[r][col]
            rgb = get_color_rgb(code)
            rc = rgb[0] / 255.0
            gc = rgb[1] / 255.0
            bc = rgb[2] / 255.0
            # Lighten by 30%: blend toward white
            rc = rc + (1.0 - rc) * LIGHTEN
            gc = gc + (1.0 - gc) * LIGHTEN
            bc = bc + (1.0 - bc) * LIGHTEN
            c.setFillColor(colors.Color(min(rc, 1), min(gc, 1), min(bc, 1)))
            px = x0 + col * cell
            py = y0 + total_h - (r + 1) * cell
            c.rect(px, py, cell, cell, fill=True, stroke=False)

    # Calculate zone boundaries (same logic as scheme pages)
    scheme_cell = cell_size_mm * mm
    usable_w = PAGE_W - 2 * MARGIN - 20
    usable_h = PAGE_H - 80 - 20
    cols_per_page = int(usable_w / scheme_cell)
    rows_per_page = int(usable_h / scheme_cell)
    n_col_sections = math.ceil(grid_w / cols_per_page)
    n_row_sections = math.ceil(grid_h / rows_per_page)

    # Draw zone grid lines
    c.setStrokeColor(colors.Color(0.8, 0.2, 0.2, 0.7))
    c.setLineWidth(1.2)
    for cs in range(1, n_col_sections):
        col_boundary = cs * cols_per_page
        if col_boundary < grid_w:
            px = x0 + col_boundary * cell
            c.line(px, y0, px, y0 + total_h)
    for rs in range(1, n_row_sections):
        row_boundary = rs * rows_per_page
        if row_boundary < grid_h:
            py = y0 + total_h - row_boundary * cell
            c.line(x0, py, x0 + total_w, py)

    # Draw zone numbers
    page_num = 0
    for row_sec in range(n_row_sections):
        for col_sec in range(n_col_sections):
            page_num += 1
            r_start = row_sec * rows_per_page
            c_start = col_sec * cols_per_page
            r_end = min(r_start + rows_per_page, grid_h)
            c_end = min(c_start + cols_per_page, grid_w)

            cx = x0 + (c_start + c_end) / 2 * cell
            cy = y0 + total_h - (r_start + r_end) / 2 * cell

            # Semi-transparent white circle behind number
            c.saveState()
            c.setFillColor(colors.Color(1, 1, 1, 0.7))
            c.circle(cx, cy, 8, fill=True, stroke=False)
            c.setFillColor(colors.Color(0.7, 0.1, 0.1))
            c.setFont(FONT_BOLD, 7)
            c.drawCentredString(cx, cy - 2.5, str(page_num))
            c.restoreState()

    # Outer border
    c.setStrokeColor(colors.Color(0.6, 0.5, 0.3))
    c.setLineWidth(2)
    c.rect(x0 - 3, y0 - 3, total_w + 6, total_h + 6, fill=False)

    draw_footer(c, PAGE_W, PAGE_H, brand, brand_note)
    c.showPage()


def create_legend_page(c, title, stitch_counts, color_symbols, aida,
                       brand, brand_note):
    """Page 3: DMC Color Legend with symbols, counts, thread length, skeins + Gamma."""
    c.setFont(FONT_BOLD, 11)
    c.setFillColor(colors.Color(0.2, 0.2, 0.2))
    c.drawString(MARGIN, PAGE_H - 40, "Легенда цветов / Список ниток")

    # Table header
    headers = ["Симв.", "DMC", "Гамма", "Название", "Стежки", "Длина (м)", "Мотки"]
    col_x = [MARGIN, MARGIN + 35, MARGIN + 80, MARGIN + 140, MARGIN + 290, MARGIN + 375, MARGIN + 440, MARGIN + 495]

    y = PAGE_H - 70
    c.setFont(FONT_BOLD, 7)
    for i, h in enumerate(headers):
        c.drawString(col_x[i], y, h)
    y -= 5
    c.setLineWidth(0.5)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    y -= 12

    sorted_colors = sorted(stitch_counts.keys(), key=lambda k: -stitch_counts[k])

    # Thread length calculation: each stitch ≈ 24mm of thread on 14ct (both strands)
    thread_per_stitch = 0.024  # meters per stitch (approximate)

    for code in sorted_colors:
        if y < 50:
            draw_footer(c, PAGE_W, PAGE_H, brand, brand_note)
            c.showPage()
            y = PAGE_H - 40
            c.setFont(FONT_BOLD, 7.5)
            for i, h in enumerate(headers):
                c.drawString(col_x[i], y, h)
            y -= 17

        sym = color_symbols[code]
        count = stitch_counts[code]
        thread_m = round(count * thread_per_stitch, 1)
        skeins = max(1, math.ceil(thread_m / 8.0))

        is_blend = str(code).startswith("b:")
        if is_blend:
            # Parse blend: "b:CODE1+CODE2"
            parts = str(code)[2:].split("+")
            c1, c2 = parts[0], parts[1]
            _, rgb1 = DMC_COLORS.get(c1, ("?", (128,128,128)))
            _, rgb2 = DMC_COLORS.get(c2, ("?", (128,128,128)))
            # Two half-swatches
            r1,g1,b1 = [v/255 for v in rgb1]
            r2,g2,b2 = [v/255 for v in rgb2]
            c.setFillColor(colors.Color(r1,g1,b1))
            c.rect(col_x[0], y-2, 6, 12, fill=True, stroke=False)
            c.setFillColor(colors.Color(r2,g2,b2))
            c.rect(col_x[0]+6, y-2, 6, 12, fill=True, stroke=False)
            c.setStrokeColor(colors.Color(0.5,0.5,0.5))
            c.rect(col_x[0], y-2, 12, 12, fill=False)
            # Symbol
            c.setFillColor(colors.Color(0.1,0.1,0.1))
            c.setFont(FONT_BOLD, 9)
            c.drawCentredString(col_x[0]+22, y, sym)
            # DMC codes
            c.setFont(FONT, 7)
            c.drawString(col_x[1], y, f"{c1}+{c2}")
            # Gamma
            g1c = DMC_TO_GAMMA.get(c1, "—")
            g2c = DMC_TO_GAMMA.get(c2, "—")
            c.setFillColor(colors.Color(0.3,0.3,0.3))
            c.drawString(col_x[2], y, f"{g1c}+{g2c}")
            # Name
            c.setFillColor(colors.Color(0.1,0.1,0.1))
            n1, _ = DMC_COLORS.get(c1, ("?", (0,0,0)))
            n2, _ = DMC_COLORS.get(c2, ("?", (0,0,0)))
            c.drawString(col_x[3], y, f"БЛЕНД: {n1[:12]}+{n2[:12]}")
        else:
            name_ru, rgb = DMC_COLORS.get(code, ("?", (128, 128, 128)))
            gamma_code = DMC_TO_GAMMA.get(code, "—")

            # Color swatch
            rc, gc, bc = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
            c.setFillColor(colors.Color(rc, gc, bc))
            c.rect(col_x[0], y - 2, 12, 12, fill=True)
            c.setStrokeColor(colors.Color(0.5, 0.5, 0.5))
            c.rect(col_x[0], y - 2, 12, 12, fill=False)

            # Symbol
            c.setFillColor(colors.Color(0.1, 0.1, 0.1))
            c.setFont(FONT_BOLD, 9)
            c.drawCentredString(col_x[0] + 22, y, sym)

            # DMC code
            c.setFont(FONT, 7)
            c.drawString(col_x[1], y, str(code))

            # Gamma code
            c.setFillColor(colors.Color(0.3, 0.3, 0.3))
            c.drawString(col_x[2], y, str(gamma_code))

            # Name
            c.setFillColor(colors.Color(0.1, 0.1, 0.1))
            c.drawString(col_x[3], y, name_ru[:26])

        # Stitch count
        c.drawRightString(col_x[4] + 50, y, f"{count:,}")

        # Thread length
        c.drawRightString(col_x[5] + 50, y, f"{thread_m}")

        # Skeins
        c.drawRightString(col_x[6] + 30, y, str(skeins))

        y -= 14

    draw_footer(c, PAGE_W, PAGE_H, brand, brand_note)
    c.showPage()


def create_scheme_pages(c, title, dmc_grid, color_symbols, brand, brand_note,
                        cell_size_mm=4.0):
    """Create symbol scheme pages divided into sections."""
    grid_h = len(dmc_grid)
    grid_w = len(dmc_grid[0])
    cell = cell_size_mm * mm

    # Calculate how many cells fit per page
    usable_w = PAGE_W - 2 * MARGIN - 20  # space for row numbers
    usable_h = PAGE_H - 80 - 20  # space for col numbers + header + footer

    cols_per_page = int(usable_w / cell)
    rows_per_page = int(usable_h / cell)

    # How many page sections needed
    n_col_sections = math.ceil(grid_w / cols_per_page)
    n_row_sections = math.ceil(grid_h / rows_per_page)

    page_num = 0
    total_pages = n_row_sections * n_col_sections

    for row_sec in range(n_row_sections):
        for col_sec in range(n_col_sections):
            page_num += 1
            r_start = row_sec * rows_per_page
            r_end = min(r_start + rows_per_page, grid_h)
            c_start = col_sec * cols_per_page
            c_end = min(c_start + cols_per_page, grid_w)

            actual_rows = r_end - r_start
            actual_cols = c_end - c_start

            # Header
            c.setFont(FONT_BOLD, 8)
            c.setFillColor(colors.Color(0.2, 0.2, 0.2))
            c.drawString(MARGIN, PAGE_H - 25, "Символьная схема")
            c.setFont(FONT, 7)
            c.drawString(MARGIN, PAGE_H - 38,
                         f"Строки {r_start + 1}–{r_end}, столбцы {c_start + 1}–{c_end}   |   {page_num}/{total_pages}")

            x0 = MARGIN + 20  # space for row labels
            y0 = PAGE_H - 55

            # Column numbers (every 5)
            c.setFont(FONT, 5)
            c.setFillColor(colors.Color(0.4, 0.4, 0.4))
            for col_idx in range(actual_cols):
                abs_col = c_start + col_idx + 1
                if abs_col % 5 == 1 or abs_col == c_start + 1:
                    px = x0 + col_idx * cell + cell / 2
                    c.drawCentredString(px, y0 + 3, str(abs_col))

            # Draw grid and symbols
            for row_idx in range(actual_rows):
                abs_row = r_start + row_idx + 1
                py = y0 - (row_idx + 1) * cell

                # Row number (every 5)
                if abs_row % 5 == 1 or abs_row == r_start + 1:
                    c.setFont(FONT, 5)
                    c.setFillColor(colors.Color(0.4, 0.4, 0.4))
                    c.drawRightString(x0 - 3, py + cell * 0.25, str(abs_row))

                for col_idx in range(actual_cols):
                    code = dmc_grid[r_start + row_idx][c_start + col_idx]
                    sym = color_symbols[code]
                    rgb = get_color_rgb(code)

                    px = x0 + col_idx * cell

                    # Background color (light tint)
                    rc, gc, bc = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
                    # Make background lighter
                    bg_r = 0.7 + 0.3 * rc
                    bg_g = 0.7 + 0.3 * gc
                    bg_b = 0.7 + 0.3 * bc
                    c.setFillColor(colors.Color(bg_r, bg_g, bg_b))
                    c.rect(px, py, cell, cell, fill=True, stroke=False)

                    # Symbol
                    c.setFillColor(colors.Color(0.1, 0.1, 0.1))
                    font_size = cell * 0.6 / mm * 2.5
                    font_size = min(font_size, 7)
                    c.setFont(FONT, font_size)
                    c.drawCentredString(px + cell / 2, py + cell * 0.2, sym)

            # Grid lines
            c.setStrokeColor(colors.Color(0.75, 0.75, 0.75))
            c.setLineWidth(0.2)
            for i in range(actual_cols + 1):
                px = x0 + i * cell
                c.line(px, y0, px, y0 - actual_rows * cell)
            for i in range(actual_rows + 1):
                py = y0 - i * cell
                c.line(x0, py, x0 + actual_cols * cell, py)

            # Bold lines every 10
            c.setStrokeColor(colors.Color(0.3, 0.3, 0.3))
            c.setLineWidth(0.8)
            for i in range(actual_cols + 1):
                abs_col = c_start + i
                if abs_col % 10 == 0:
                    px = x0 + i * cell
                    c.line(px, y0, px, y0 - actual_rows * cell)
            for i in range(actual_rows + 1):
                abs_row = r_start + i
                if abs_row % 10 == 0:
                    py = y0 - i * cell
                    c.line(x0, py, x0 + actual_cols * cell, py)

            draw_footer(c, PAGE_W, PAGE_H, brand, brand_note)
            c.showPage()


def generate_pattern(image_path, output_path, target_width=200, max_colors=38,
                     title="Схема вышивки крестиком", brand="Твоя вышивка",
                     brand_note="только для личного использования",
                     cell_size_mm=4.0, aida=14,
                     export_oxs_file=True, author="", copyright_note="",
                     blend_replacements=None, region_replacements=None, no_blends=False):
    """Main function: generate complete cross-stitch PDF."""
    print(f"Loading image: {image_path}")
    dmc_grid, stitch_counts, color_symbols, grid_h, grid_w, preview_img = \
        image_to_pattern(image_path, target_width, max_colors)

    total_stitches = sum(stitch_counts.values())
    n_colors = len(stitch_counts)

    print(f"Pattern: {grid_w}x{grid_h} stitches, {n_colors} colors, {total_stitches:,} total")

    # Detect blends
    if no_blends:
        print("Blends: skipped")
        blend_grid, blend_pairs = {}, []
    else:
        print("Detecting blends...")
        blend_grid, blend_pairs = detect_blends(dmc_grid, stitch_counts, color_symbols)

    # Apply color/blend replacements if provided
    if blend_replacements:
        for old_key, replacement_code in blend_replacements.items():
            if old_key in color_symbols:
                sym = color_symbols[old_key]
                count = stitch_counts.get(old_key, 0)
                is_blend = str(old_key).startswith("b:")
                # Replace in grid
                for y in range(grid_h):
                    for x in range(grid_w):
                        if dmc_grid[y][x] == old_key:
                            dmc_grid[y][x] = replacement_code
                # Update counts
                stitch_counts[replacement_code] = stitch_counts.get(replacement_code, 0) + count
                del stitch_counts[old_key]
                del color_symbols[old_key]
                # Assign symbol if new code doesn't have one
                if replacement_code not in color_symbols:
                    used = set(color_symbols.values())
                    for s in ALL_SYMBOLS:
                        if s not in used:
                            color_symbols[replacement_code] = s
                            break
                if is_blend:
                    # Remove from blend_pairs (list of tuples)
                    pair = tuple(sorted(old_key[2:].split("+")))
                    blend_pairs = [p for p in blend_pairs if p != pair]
                    # Clean blend_grid
                    blend_grid = {pos: val for pos, val in blend_grid.items() if val != pair}
                label = f"blend {sym} ({old_key})" if is_blend else f"color {sym} (DMC {old_key})"
                print(f"Replaced {label} → DMC {replacement_code} ({count} stitches)")

    # Apply region-specific replacements
    if region_replacements:
        for rr in region_replacements:
            old_code = rr['old']
            new_code = rr['new']
            y_min = rr.get('y_min', 0)
            y_max = rr.get('y_max', grid_h - 1)
            old_sym = color_symbols.get(old_code, '?')
            count = 0
            for y in range(y_min, min(y_max + 1, grid_h)):
                for x in range(grid_w):
                    if dmc_grid[y][x] == old_code:
                        dmc_grid[y][x] = new_code
                        count += 1
            if count > 0:
                stitch_counts[old_code] = stitch_counts.get(old_code, 0) - count
                stitch_counts[new_code] = stitch_counts.get(new_code, 0) + count
                if stitch_counts.get(old_code, 0) <= 0:
                    stitch_counts.pop(old_code, None)
                    color_symbols.pop(old_code, None)
                if new_code not in color_symbols:
                    used = set(color_symbols.values())
                    for s in ALL_SYMBOLS:
                        if s not in used:
                            color_symbols[new_code] = s
                            break
                print(f"Region replace {old_sym} (DMC {old_code}) → DMC {new_code} in rows {y_min}-{y_max} ({count} stitches)")

    c_pdf = canvas.Canvas(output_path, pagesize=A4)
    c_pdf.setTitle(title)
    c_pdf.setAuthor(author if author else brand)

    print("Creating title page...")
    create_title_page(c_pdf, title, grid_h, grid_w, n_colors, total_stitches,
                      aida, brand, brand_note, preview_img)

    print("Creating stitch render page...")
    create_stitch_render_page(c_pdf, title, dmc_grid, color_symbols, stitch_counts,
                               brand, brand_note, cell_size_mm)

    print("Creating legend page...")
    create_legend_page(c_pdf, title, stitch_counts, color_symbols, aida,
                       brand, brand_note)

    print("Creating scheme pages...")
    create_scheme_pages(c_pdf, title, dmc_grid, color_symbols, brand, brand_note,
                        cell_size_mm)

    c_pdf.save()

    preview_path = output_path.rsplit('.', 1)[0] + '_preview.png'
    try:
        preview_img.save(preview_path)
        print(f"Preview saved: {preview_path}")
    except Exception as e:
        print(f"Preview save failed: {e}")

    print(f"Done! Saved to {output_path}")

    # Export OXS file if requested
    if export_oxs_file:
        oxs_path = output_path.rsplit('.', 1)[0] + '.oxs'
        try:
            export_oxs(oxs_path, title, grid_w, grid_h, aida, dmc_grid,
                       stitch_counts, color_symbols, author, copyright_note)
            print(f"OXS exported: {oxs_path}")
        except Exception as e:
            print(f"OXS export failed: {e}")

    return output_path


def export_oxs(oxs_path, title, width, height, aida, dmc_grid,
               stitch_counts, color_symbols, author="", copyright_note=""):
    """Export pattern in OXS (Open Cross Stitch) format with blend support."""
    import html

    # Separate real DMC codes from blend codes
    all_codes = sorted(stitch_counts.keys(), key=lambda x: -stitch_counts[x])
    real_codes = [c for c in all_codes if not str(c).startswith("b:")]
    blend_codes = [c for c in all_codes if str(c).startswith("b:")]

    # Build index for real codes; ensure blend components are included
    code_to_idx = {}
    for i, code in enumerate(real_codes):
        code_to_idx[code] = i + 1
    for bc in blend_codes:
        for p in str(bc)[2:].split("+"):
            if p not in code_to_idx:
                code_to_idx[p] = len(code_to_idx) + 1

    all_indexed = sorted(code_to_idx.keys(), key=lambda c: code_to_idx[c])
    ascii_syms = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#@$%&*+=-~")
    sym_remap = {code: (ascii_syms[i] if i < len(ascii_syms) else str(i)) for i, code in enumerate(all_indexed)}

    esc = html.escape
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<chart>']

    lines.append('<format comments01="OXS v1.0 with blend/partstitch support" />')
    lines.append(f'<properties oxsversion="1.0" software="Cross-Stitch Generator" software_version="2026" '
        f'chartheight="{height}" chartwidth="{width}" charttitle="{esc(title)}" author="{esc(author)}" '
        f'copyright="{esc(copyright_note)}" stitchesperinch="{aida}" stitchesperinch_y="{aida}" '
        f'palettecount="{len(code_to_idx)}" />')

    lines.append('<palette>')
    lines.append('<palette_item index="0" number="cloth" name="cloth" color="FFFFFF" symbol="" strands="2" />')
    for code in all_indexed:
        idx = code_to_idx[code]
        name_ru, rgb = DMC_COLORS.get(code, ("?", (128,128,128)))
        hx = f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        lines.append(f'<palette_item index="{idx}" number="DMC {code}" name="{esc(name_ru)}" '
                     f'color="{hx}" symbol="{sym_remap[code]}" strands="2" />')
    lines.append('</palette>')

    lines.append('<fullstitches>')
    part_lines = []
    for y, row in enumerate(dmc_grid):
        for x, code in enumerate(row):
            sc = str(code)
            if sc.startswith("b:"):
                p = sc[2:].split("+")
                i1, i2 = code_to_idx.get(p[0], 0), code_to_idx.get(p[1], 0)
                part_lines.append(f'<partstitch x="{x}" y="{y}" palindex1="{i1}" palindex2="{i2}" direction="1" />')
            else:
                idx = code_to_idx.get(code, 0)
                if idx > 0:
                    lines.append(f'<stitch x="{x}" y="{y}" palindex="{idx}" />')
    lines.append('</fullstitches>')

    if part_lines:
        lines.append('<partstitches>')
        lines.extend(part_lines)
        lines.append('</partstitches>')

    lines.append('<backstitches />')
    lines.append('</chart>')

    with open(oxs_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cross-stitch pattern PDF generator")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output PDF path")
    parser.add_argument("--width", type=int, default=200, help="Pattern width in stitches")
    parser.add_argument("--max-colors", type=int, default=38, help="Maximum DMC colors")
    parser.add_argument("--title", default="Схема вышивки крестиком", help="Pattern title")
    parser.add_argument("--brand", default="Твоя вышивка", help="Brand name")
    parser.add_argument("--brand-note", default="только для личного использования", help="Brand note")
    parser.add_argument("--cell-size", type=float, default=4.0, help="Cell size in mm")
    parser.add_argument("--aida", type=int, default=14, help="Aida count")
    parser.add_argument("--no-oxs", action="store_true", help="Skip OXS file export")
    parser.add_argument("--no-blends", action="store_true", help="Skip blend detection")
    parser.add_argument("--author", default="", help="Author name for PDF/OXS metadata")
    parser.add_argument("--copyright", default="", help="Copyright notice for OXS metadata")
    parser.add_argument("--replace-blend", action="append", default=[],
                        help="Replace blend with solid color, format: 'b:CODE1+CODE2=NEWCODE'")
    parser.add_argument("--replace-region", action="append", default=[],
                        help="Replace color in region, format: 'CODE=NEWCODE:ymin-ymax'")

    args = parser.parse_args()
    blend_replacements = {}
    for r in args.replace_blend:
        blend_key, new_code = r.split("=")
        blend_replacements[blend_key] = new_code

    region_replacements = []
    for r in args.replace_region:
        code_part, region_part = r.split(":")
        old_code, new_code = code_part.split("=")
        y_min, y_max = region_part.split("-")
        region_replacements.append({'old': old_code, 'new': new_code, 'y_min': int(y_min), 'y_max': int(y_max)})

    generate_pattern(
        args.image, args.output,
        target_width=args.width,
        max_colors=args.max_colors,
        title=args.title,
        brand=args.brand,
        brand_note=args.brand_note,
        cell_size_mm=args.cell_size,
        aida=args.aida,
        export_oxs_file=not args.no_oxs,
        author=args.author,
        copyright_note=args.copyright,
        blend_replacements=blend_replacements or None,
        region_replacements=region_replacements or None,
        no_blends=args.no_blends,
    )
