import ST7735
from PIL import Image, ImageDraw, ImageFont
from fonts.ttf import RobotoMedium as UserFont


class Display:
    def __init__(self):
        self.disp: ST7735 = ST7735.ST7735(
            port=0, cs=1, dc=9, backlight=12, rotation=270, spi_speed_hz=10000000
        )
        self.disp.begin()

        self.WIDTH: int = self.disp.width
        self.HEIGHT: int = self.disp.height

        # Text settings
        font_size: int = 25
        self.font = ImageFont.truetype(UserFont, font_size)
        self.text_colour = (255, 255, 255)
        self.back_colour = (0, 170, 170)

    def write_text(self, message: str):
        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)

        size_x, size_y = draw.textsize(message, self.font)

        # Calculate text position
        x = (self.WIDTH - size_x) / 2
        y = (self.HEIGHT / 2) - (size_y / 2)

        # Draw background rectangle and write text.
        draw.rectangle((0, 0, 160, 80), self.back_colour)
        draw.text((x, y), message, font=self.font, fill=self.text_colour)
        self.disp.display(img)
