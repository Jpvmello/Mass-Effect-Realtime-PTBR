import numpy as np

from BoundingBox import BoundingBox
from PIL import Image, ImageDraw, ImageFont

class Subtitle:
    def __init__(self, image_width, image_height):
        self.text = ''
        self.bbox = BoundingBox(left = 0, top = 0, right = image_width, bottom = image_height)
        
        self.font = ImageFont.truetype(r'C:\Windows\Fonts\GOTHICB.TTF', size = int(0.03 * image_height))
        self.font_color = tuple(3 * [255])
        self.font_descent = self.font.getmetrics()[1] # descent é a distância da base do texto ao menor ponto (letras como 'j' or 'p' "vazam" para baixo)

        self.word_conf_font = ImageFont.load_default(size = int(0.02 * image_height))
        self.transl_fill_padding_x = int(0.009 * image_width)
        self.transl_fill_padding_y = int(0.015 * image_height)

        self.orig_sub_info = []

    def update(self, text, left, top, right, bottom, orig_sub_info):
        self.text = text
        self.bbox = BoundingBox(left = left, top = top, right = right, bottom = bottom)
        self.orig_sub_info = orig_sub_info
    
    def draw(self, image):
        if len(self.text) == 0:
            return image

        image = Image.fromarray(image)
        draw = ImageDraw.Draw(image)

        transl_lines_bboxes = [self.font.getmask(line).getbbox() for line in self.text.split('\n')]
        
        transl_text_bbox = BoundingBox(
            left = 0,
            top = 0,
            right = np.max([b[2] for b in transl_lines_bboxes]),
            bottom = sum([b[3] + self.font_descent for b in transl_lines_bboxes])
        )
        transl_text_bbox.left = max(0, min(self.bbox.left, self.bbox.center_x - transl_text_bbox.width//2))
        transl_text_bbox.top = max(0, min(self.bbox.top, self.bbox.center_y - transl_text_bbox.height//2))
        transl_text_bbox.right = min(image.width - 1, max(self.bbox.right, self.bbox.center_x + transl_text_bbox.width//2))
        transl_text_bbox.bottom = min(image.height - 1, max(self.bbox.bottom, self.bbox.center_y + transl_text_bbox.height//2))

        transl_fill_bbox = BoundingBox(
            left = transl_text_bbox.left - self.transl_fill_padding_x,
            top = transl_text_bbox.top - self.transl_fill_padding_y,
            right = transl_text_bbox.right + self.transl_fill_padding_x,
            bottom = transl_text_bbox.bottom + self.transl_fill_padding_y,
        )

        draw.rectangle([(transl_fill_bbox.left, transl_fill_bbox.top), (transl_fill_bbox.right, transl_fill_bbox.bottom)], fill = "black")
        draw.text((transl_text_bbox.left, transl_text_bbox.top), self.text, font = self.font, fill = self.font_color)
        
        return np.array(image)
    
    def draw_bbox(self, image):
        image = Image.fromarray(image)
        draw = ImageDraw.Draw(image)
        draw.rectangle([(self.bbox.left, self.bbox.top), (self.bbox.right, self.bbox.bottom)], outline = "yellow", width = 3)
        return np.array(image)

    def draw_word_bbox(self, image):
        image = Image.fromarray(image)
        draw = ImageDraw.Draw(image)
        if len(self.orig_sub_info) > 0:
            for word_info in self.orig_sub_info:
                color = (0, int(255 * word_info['conf']), 0)
                draw.rectangle([(word_info['left'], word_info['top']), (word_info['left'] + word_info['width'], word_info['top'] + word_info['height'])],
                               outline = color)
                draw.text((word_info['left'], word_info['top'] + word_info['height']), str(int(word_info['conf'])) + '%',
                          font = self.word_conf_font, fill = color)
        return np.array(image)