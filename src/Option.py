class Option:
    def __init__(self, is_enable, toggling_key, callback):
        self.is_enable = is_enable
        self.toggling_key = toggling_key
        self.callback = callback
    
    def toggle(self):
        self.is_enable = not self.is_enable
    
    def process(self, image):
        if self.is_enable:
            return self.callback(image)
        return image