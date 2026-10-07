from PIL import Image
import pytesseract
img = Image.open('/tmp/qemu_bios_screen3.png')
print(pytesseract.image_to_string(img))
