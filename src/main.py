import cv2
import mss
import pygame
import numpy as np
import pytesseract
import concurrent.futures

from PIL import Image
from Option import Option
from Subtitle import Subtitle
from googletrans import Translator
from screeninfo import get_monitors

def preprocess(image):
    image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    image = cv2.GaussianBlur(image, (3, 3), 0)
    kernel = np.array([[0, -1, 0],
        [-1, 5,-1],
        [0, -1, 0]])
    image = cv2.filter2D(image, -1, kernel)
    _, image = cv2.threshold(image, 225, 255, cv2.THRESH_BINARY)
    image = cv2.morphologyEx(image, cv2.MORPH_DILATE, np.ones((2, 2)))
    return image

def get_text_info(image, preprocessed):
    translator = Translator()
    
    if not preprocessed:
        image = preprocess(image)

    image = Image.fromarray(image)

    text_data = pytesseract.image_to_data(image, output_type = pytesseract.Output.DATAFRAME)
    text_data = text_data.fillna('')

    orig_words_info = []
    line_nums = []
    line_data = {}
    bbox = {'left': 0, 'top': 0, 'right': image.width, 'bottom': image.height}
    for block_num in range(text_data['block_num'].max() + 1):
        line_data = text_data[(text_data['block_num'] == block_num) & (text_data['conf'] != -1)]
        if line_data.empty or not any(line_data['text'].astype(str).iloc[i].endswith(':') for i in range(line_data['text'].shape[0])):
            continue

        orig_words_info = line_data[['text', 'left', 'top', 'width', 'height', 'conf']].to_dict(orient = 'records')
        line_nums += line_data['line_num'].tolist()
        bbox = {
            'left': line_data['left'].min(),
            'top': line_data['top'].min(),
            'right': line_data['left'].max() + line_data[line_data['left'] == line_data['left'].max()].iloc[0]['width'],
            'bottom': line_data['top'].max() + line_data[line_data['top'] == line_data['top'].max()].iloc[0]['height'],
        }
        break
    
    words = [word_info['text'] for word_info in orig_words_info]
    if len(words) > 0:
        text = ' '.join(words).replace('|', 'I')
        text = translator.translate(text, src = 'en', dest = 'pt').text
        words = text.split()

        n_lines = max(1, len(set(line_nums)))
        words_per_line = np.ceil(len(words)/n_lines).astype(int)
        for i in range(words_per_line, len(words), words_per_line):
            words[i-1] += '\n'
    
    text = ' '.join(words)
    return text, bbox['left'], bbox['top'], bbox['right'], bbox['bottom'], orig_words_info

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor() as executor:
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        screens = get_monitors()
        size_factor = 0.7 if len(screens) == 1 else 1 # tela não-cheia se tela única, para testes
        dest_wh = (int(size_factor*screens[-1].width), int(size_factor*screens[-1].height))

        pygame.init()
        screen = pygame.display.set_mode(dest_wh, display = len(screens) - 1)
        clock = pygame.time.Clock()

        with mss.mss() as sct:
            subtitle = Subtitle(screen.get_width(), screen.get_height())
            future = None
            running = True

            options = {
                'preprocess': Option(is_enable = False, toggling_key = pygame.K_d, callback = preprocess),
                'show_bbox': Option(is_enable = False, toggling_key = pygame.K_b, callback = subtitle.draw_bbox),
                'show_word_bbox': Option(is_enable = False, toggling_key = pygame.K_w, callback = subtitle.draw_word_bbox),
                'show_translation': Option(is_enable = True, toggling_key = pygame.K_t, callback = subtitle.draw),
            }

            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        running = False
                    for option in options.values():
                        if event.type == pygame.KEYDOWN and event.key == option.toggling_key:
                            option.toggle()
                
                if running:
                    image = sct.grab((0, 0, screens[0].width, screens[0].height))

                    # Convertendo a imagem capturada para um formato compatível com pygame
                    image = np.array(image)[:, :, :3]
                    image = np.flip(image, axis = 2)  # Ajustar o formato de cor BGR para RGB

                    image = options['preprocess'].process(image)

                    if future is None:
                        future = executor.submit(get_text_info, image, preprocessed = options['preprocess'].is_enable)
                    if future.done():
                        subtitle.update(*future.result())
                        future = None

                    if options['preprocess'].is_enable:
                        image = np.stack(3*[image], axis = 2) # gray to "rgb"

                    for option_name, option in options.items():
                        if option_name.startswith('show_'):
                            image = options[option_name].process(image)
                    image = cv2.resize(image, dest_wh)
                    image = np.moveaxis(image, (0, 1, 2), (1, 0, 2)) # HWC -> WHC
                    image = pygame.surfarray.make_surface(image)

                    # Desenhar a imagem no segundo monitor
                    screen.blit(image, (0, 0))
                    pygame.display.flip()
                    clock.tick(60)  # Limita a 60 frames por segundo

            pygame.quit()
