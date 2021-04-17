import os
import random
import shutil
from decimal import getcontext, Decimal
from typing import List, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageSequence, ImageDraw


class ImageGlitcher:
    # Handles Image/GIF Glitching Operations

    __version__ = '1.0.2'

    def __init__(self):
        # Setting up global variables needed for glitching
        self.pixel_tuple_len = 0
        self.img_width, self.img_height = 0, 0
        self.img_mode = 'Unknown'

        # Creating 3D arrays for pixel data
        self.inputarr = None
        self.outputarr = None

        # Getting PATH of temp folders
        self.lib_path = os.path.split(os.path.abspath(__file__))[0]
        self.gif_dirpath = os.path.join(self.lib_path, 'Glitched GIF')

        # Setting glitch_amount max and min
        self.glitch_max = 10.0
        self.glitch_min = 0.1

        self.effects = (self.__glitch_effect_33,
                        self.__glitch_effect_analog_noise,
                        self.__rgb_split,
                        self.__tile_jittered,
                        self.__screen_jump_effect,
                        self.__image_block,
                        self.__screen_shake_effect)

    def __isgif(self, img: Union[str, Image.Image]) -> bool:
        # Returns true if input image is a GIF and/or animated
        if isinstance(img, str):
            if not os.path.isfile(img):
                return False
            img = Image.open(img)
        index = 0
        for _ in ImageSequence.Iterator(img):
            # More than one frames means image is animated
            index += 1
            if index >= 2:
                return True
        return False

    def __open_image(self, img_path: str) -> Image.Image:
        # Returns an Image object
        # Will throw exception if img_path doesn't point to Image
        if img_path.endswith('.gif'):
            # Do not convert GIF file
            return Image.open(img_path)
        elif img_path.endswith('.png'):
            # Convert the Image to RGBA if it's png
            return Image.open(img_path).convert('RGBA')
        else:
            # Otherwise convert it to RGB
            return Image.open(img_path).convert('RGB')

    def __fetch_image(self,
                      src_img: Union[str, Image.Image],
                      gif_allowed: bool
                      ) -> Image.Image:
        """
         The following code resolves whether input was a path or an Image
         Then returns an Image object
         Raises an exception if `img` param is not an Image
        """
        if isinstance(src_img, str) and (gif_allowed or not src_img.endswith('.gif')):
            """
             An str object was passed
             If GIF is not allowed and the Image path is a GIF
             the function will raise an Exception
             If GIF is allowed, any Image path is good to go
            """
            # Sanity Check if the path exists
            if not os.path.isfile(src_img):
                raise FileNotFoundError('Path not found')
            try:
                # Open the image at given path
                img = self.__open_image(src_img)
            except:
                # File is not an Image
                raise Exception('Wrong format')
        elif isinstance(src_img, Image.Image) and (gif_allowed or not self.__isgif(src_img)):
            """
             An Image object was passed
             If GIF is not allowed and the Image object is a GIF
             the function will raise an Exception
             If GIF is allowed, any Image object is good to go
            """
            if src_img.format == 'GIF':
                # Do not convert GIF file
                return src_img
            elif src_img.format == 'PNG':
                # Convert the Image to RGBA if it's png
                img = src_img.convert('RGBA')
            else:
                # Otherwise convert it to RGB
                img = src_img.convert('RGB')
        else:
            # File is not an Image
            # OR it's a GIF but GIF is not allowed

            # Raise the GENERIC exception here
            raise Exception('Wrong format')
        return img

    def glitch_image(self,
                     src_img: Union[str, Image.Image],
                     glitch_amount: Union[int, float],
                     seed: Optional[Union[int, float]] = None,
                     glitch_change: Union[int, float] = 0.0,
                     color_offset: bool = False,
                     scan_lines: bool = False,
                     gif: bool = False,
                     cycle: bool = False,
                     frames: int = 23,
                     step: int = 1,
                     effect_type_seq: tuple[int] = ()
                     ) -> Union[Image.Image, List[Image.Image]]:
        """
         Sets up values needed for glitching the image
         Returns created Image object if gif=False
         Returns list of Image objects if gif=True
         PARAMETERS:-
         src_img: Either the path to input Image or an Image object itself
         glitch_amount: Level of glitch intensity, [0.1, 10.0] (inclusive)
         glitch_change: Increment/Decrement in glitch_amount after every glitch
         cycle: Whether or not to cycle glitch_amount back to glitch_min or glitch_max
                if it over/underflows
         color_offset: Specify True if color_offset effect should be applied
         scan_lines: Specify True if scan_lines effect should be applied
         gif: True if output should be ready to be saved as GIF
         frames: How many glitched frames should be generated for GIF
         step: Glitch every step'th frame, defaults to 1 (i.e all frames)
         seed: Set a random seed for generating similar images across runs,
               defaults to None (random seed).
        """

        # Sanity checking the inputs
        if not ((isinstance(glitch_amount, float)
                 or isinstance(glitch_amount, int))
                and self.glitch_min <= glitch_amount <= self.glitch_max):
            raise ValueError('glitch_amount parameter must be a positive number '
                             f'in range {self.glitch_min} to {self.glitch_max}, inclusive')
        if not ((isinstance(glitch_change, float)
                 or isinstance(glitch_change, int))
                and -self.glitch_max <= glitch_change <= self.glitch_max):
            raise ValueError(
                f'glitch_change parameter must be a number between {-self.glitch_max} and {self.glitch_max}, inclusive')
        if seed and not (isinstance(seed, float) or isinstance(seed, int)):
            raise ValueError(
                f'seed parameter must be a number')
        if not (frames > 0 and isinstance(frames, int)):
            raise ValueError(
                'frames param must be a positive integer value greater than 0')
        if not step > 0 or not isinstance(step, int):
            raise ValueError(
                'step parameter must be a positive integer value greater than 0')
        if not isinstance(cycle, bool):
            raise ValueError('cycle param must be a boolean')
        if not isinstance(color_offset, bool):
            raise ValueError('color_offset param must be a boolean')
        if not isinstance(scan_lines, bool):
            raise ValueError('scan_lines param must be a boolean')
        if not isinstance(gif, bool):
            raise ValueError('gif param must be a boolean')

        self.seed = seed
        if self.seed:
            # Set the seed if it was given
            self.__reset_rng_seed()

        try:
            # Get Image, whether input was an str path or Image object
            # GIF input is NOT allowed in this method
            img = self.__fetch_image(src_img, gif_allowed=False)
        except FileNotFoundError:
            # Throw DETAILED exception here (Traceback will be present from previous exceptions)
            raise FileNotFoundError(f'No image found at given path: {src_img}')
        except:
            # Throw DETAILED exception here (Traceback will be present from previous exceptions)
            raise Exception(
                'File format not supported - must be a non-animated image file')

        # Fetching image attributes
        self.pixel_tuple_len = len(img.getbands())
        self.img_width, self.img_height = img.size
        self.img_mode = img.mode

        # Assigning the 3D arrays with pixel data
        self.inputarr = np.asarray(img)
        self.outputarr = np.array(img)

        # Glitching begins here
        if not gif:
            # Return glitched image
            return self.__get_glitched_img(glitch_amount, color_offset, scan_lines)

        # Return glitched GIF
        # Set up directory for storing glitched images
        if os.path.isdir(self.gif_dirpath):
            shutil.rmtree(self.gif_dirpath)
        os.mkdir(self.gif_dirpath)

        # Set up decimal precision for glitch_change
        original_prec = getcontext().prec
        getcontext().prec = 4

        glitched_imgs = []
        for i in range(frames):
            """
             * Glitch the image for n times
             * Where n is 0,1,2...frames
             * Save the image the in temp directory
             * Open the image and append a copy of it to the list
            """
            if not i % step == 0:
                # Only every step'th frame should be glitched
                # Other frames will be appended as they are
                glitched_imgs.append(img.copy())
                continue
            glitched_img = self.__get_glitched_img(
                glitch_amount, color_offset, scan_lines, effect_type_seq)
            file_path = os.path.join(self.gif_dirpath, 'glitched_frame.png')
            glitched_img.save(file_path, compress_level=3)
            glitched_imgs.append(Image.open(file_path).copy())
            # Change glitch_amount by given value
            glitch_amount = self.__change_glitch(
                glitch_amount, glitch_change, cycle)

        # Set decimal precision back to original value
        getcontext().prec = original_prec
        # Cleanup
        shutil.rmtree(self.gif_dirpath)
        return glitched_imgs

    def glitch_gif(self,
                   src_gif: Union[str, Image.Image],
                   glitch_amount: Union[int, float],
                   seed: Union[int, float] = None,
                   glitch_change: Union[int, float] = 0.0,
                   color_offset: bool = False,
                   scan_lines: bool = False,
                   gif: bool = False, cycle: bool = False,
                   step=1
                   ) -> Tuple[List[Image.Image], float, int]:
        """
         Glitch each frame of input GIF
         Returns the following:
         * List of PngImage objects,
         * Average duration (in centiseconds)
           of each frame in the original GIF,
         * Number of frames in the original GIF
         NOTE: This is a time consuming process, especially for large GIFs
               with many frames
         PARAMETERS:-
         src_gif: Either the path to input Image or an Image object itself
         glitch_amount: Level of glitch intensity, [0.1, 10.0] (inclusive)
         glitch_change: Increment/Decrement in glitch_amount after every glitch
         cycle: Whether or not to cycle glitch_amount back to glitch_min or glitch_max
                if it over/underflows
         color_offset: Specify True if color_offset effect should be applied
         scan_lines: Specify True if scan_lines effect should be applied
         step: Glitch every step'th frame, defaults to 1 (i.e all frames)
         seed: Set a random seed for generating similar images across runs,
               defaults to None (random seed)
        """

        # Sanity checking the params
        if not ((isinstance(glitch_amount, float)
                 or isinstance(glitch_amount, int))
                and self.glitch_min <= glitch_amount <= self.glitch_max):
            raise ValueError('glitch_amount parameter must be a positive number '
                             f'in range {self.glitch_min} to {self.glitch_max}, inclusive')
        if not ((isinstance(glitch_change, float)
                 or isinstance(glitch_change, int))
                and -self.glitch_max <= glitch_change <= self.glitch_max):
            raise ValueError(
                f'glitch_change parameter must be a number between {-self.glitch_max} and {self.glitch_max}, inclusive')
        if seed and not (isinstance(seed, float) or isinstance(seed, int)):
            raise ValueError(
                f'seed parameter must be a number')
        if not step > 0 or not isinstance(step, int):
            raise ValueError(
                'step parameter must be a positive integer value greater than 0')
        if not isinstance(cycle, bool):
            raise ValueError('cycle param must be a boolean')
        if not isinstance(color_offset, bool):
            raise ValueError('color_offset param must be a boolean')
        if not isinstance(scan_lines, bool):
            raise ValueError('scan_lines param must be a boolean')
        if not self.__isgif(src_gif):
            raise Exception(
                'Input image must be a path to a GIF or be a GIF Image object')

        self.seed = seed
        if self.seed:
            # Set the seed if it was given
            self.__reset_rng_seed()

        try:
            # Get Image, whether input was an str path or Image object
            # GIF input is allowed in this method
            gif = self.__fetch_image(src_gif, gif_allowed=True)
        except FileNotFoundError:
            # Throw DETAILED exception here (Traceback will be present from previous exceptions)
            raise FileNotFoundError(f'No image found at given path: {src_gif}')
        except:
            # Throw DETAILED exception here (Traceback will be present from previous exceptions)
            raise Exception('File format not supported - must be an image file')

        # Set up directory for storing glitched images
        if os.path.isdir(self.gif_dirpath):
            shutil.rmtree(self.gif_dirpath)
        os.mkdir(self.gif_dirpath)

        # Set up decimal precision for glitch_change
        original_prec = getcontext().prec
        getcontext().prec = 4

        i = 0
        duration = 0
        glitched_imgs = []
        for frame in ImageSequence.Iterator(gif):
            """
             * Save each frame in the temp directory (always png)
             * Glitch the saved image
             * Save the glitched image in temp directory
             * Open the image and append a copy of it to the list
            """
            try:
                duration += frame.info['duration']
            except KeyError as e:
                # Override error message to provide more info
                e.args = (
                    'The key "duration" does not exist in frame.'
                    'This means PIL(pillow) could not extract necessary information from the input image',
                )
                raise
            src_frame_path = os.path.join(self.gif_dirpath, 'frame.png')
            frame.save(src_frame_path, compress_level=3)
            if not i % step == 0:
                # Only every step'th frame should be glitched
                # Other frames will be appended as they are
                glitched_imgs.append(Image.open(src_frame_path).copy())
                i += 1
                continue
            glitched_img: Image.Image = self.glitch_image(src_frame_path, glitch_amount, color_offset=color_offset,
                                                          scan_lines=scan_lines)
            file_path = os.path.join(self.gif_dirpath, 'glitched_frame.png')
            glitched_img.save(file_path, compress_level=3)
            glitched_imgs.append(Image.open(file_path).copy())
            # Change glitch_amount by given value
            glitch_amount = self.__change_glitch(
                glitch_amount, glitch_change, cycle)
            i += 1

        # Set decimal precision back to original value
        getcontext().prec = original_prec
        # Cleanup
        shutil.rmtree(self.gif_dirpath)
        return glitched_imgs, duration / i, i

    def __change_glitch(self, glitch_amount: Union[int, float], glitch_change: Union[int, float], cycle: bool) -> float:
        # A function to change glitch_amount by given increment/decrement
        glitch_amount = float(Decimal(glitch_amount) + Decimal(glitch_change))
        # glitch_amount must be between glith_min and glitch_max
        if glitch_amount < self.glitch_min:
            # If it's less, it will be cycled back to max when cycle=True
            # Otherwise, it'll stay at the least possible value -> glitch_min
            glitch_amount = float(Decimal(self.glitch_max) + Decimal(glitch_amount)) if cycle else self.glitch_min
        if glitch_amount > self.glitch_max:
            # If it's more, it will be cycled back to min when cycle=True
            # Otherwise, it'll stay at the max possible value -> glitch_max
            glitch_amount = float(Decimal(glitch_amount) % Decimal(self.glitch_max)) if cycle else self.glitch_max
        return glitch_amount

    def __get_glitched_img(self,
                           glitch_amount: Union[int, float],
                           color_offset: int,
                           scan_lines: bool,
                           effect_type_seq: tuple[int] = ()
                           ) -> Image.Image:
        """
         Glitches the image located at given path
         Intensity of glitch depends on glitch_amount
        """
        max_offset = int((glitch_amount ** 2 / 100) * self.img_width)
        doubled_glitch_amount = int(glitch_amount * 2)

        for shift_number in range(0, doubled_glitch_amount):

            if self.seed:
                # This is not deterministic as glitch amount changes the amount of shifting,
                # so get the same values on each iteration on a new pseudo-seed that is
                # offseted by the index we're iterating
                self.__reset_rng_seed(offset=shift_number)

            # Setting up offset needed for the randomized glitching
            current_offset = random.randint(-max_offset, max_offset)

            if current_offset == 0:
                # Can't wrap left OR right when offset is 0, End of Array
                continue
            if current_offset < 0:
                # Grab a rectangle of specific width and heigh, shift it left
                # by a specified offset
                # Wrap around the lost pixel data from the right
                self.__glitch_left(-current_offset)
            else:
                # Grab a rectangle of specific width and height, shift it right
                # by a specified offset
                # Wrap around the lost pixel data from the left
                self.__glitch_right(current_offset)

        if self.seed:
            # Get the same channels on the next call, we have to reset the rng seed
            # as the previous loop isn't fixed in size of iterations and depends on glitch amount
            self.__reset_rng_seed()

        if color_offset:
            # Get the next random channel we'll offset, needs to be before the random.randints
            # arguments because they will use up the original seed (if a custom seed is used)
            random_channel = self.__get_random_channel()
            # Add color channel offset if checked true
            self.__color_offset(random.randint(-doubled_glitch_amount, doubled_glitch_amount),
                                random.randint(-doubled_glitch_amount,
                                               doubled_glitch_amount),
                                random_channel)

        if scan_lines:
            # Add scan lines if checked true
            self.__add_scan_lines()

        image = Image.fromarray(self.outputarr, self.img_mode)

        if len(effect_type_seq) > 0:
            for i in effect_type_seq:
                image = self.effects[i](image)

        # Creating glitched image from output array
        # return Image.fromarray(self.outputarr, self.img_mode)
        return image

    def __add_scan_lines(self):
        # Make every other row have only black pixels
        # Only the R, G, and B channels are assigned 0 values
        # Alpha is left untouched (if present)
        self.outputarr[::2, :, :3] = [0, 0, 0]

    def __glitch_left(self, offset: int):
        """
         Grabs a rectange from inputarr and shifts it leftwards
         Any lost pixel data is wrapped back to the right
         Rectangle's Width and Height are determined from offset
         Consider an array like so-
         [[ 0, 1, 2, 3],
         [ 4, 5, 6, 7],
         [ 8, 9, 10, 11],
         [12, 13, 14, 15]]
         If we were to left shift the first row only, starting from the 1st index;
         i.e a rectangle of width = 3, height = 1, starting at (0, 0)
         We'd grab [1, 2, 3] and left shift it until the start of row
         so it'd look like [[1, 2, 3, 3]]
         Now we wrap around the lost values, i.e 0
         now it'd look like [[1, 2, 3, 0]]
         That's the end result!
        """
        # Setting up values that will determine the rectangle height
        start_y = random.randint(0, self.img_height)
        chunk_height = random.randint(1, int(self.img_height / 4))
        chunk_height = min(chunk_height, self.img_height - start_y)
        stop_y = start_y + chunk_height

        # For copy
        start_x = offset
        # For paste
        stop_x = self.img_width - start_x

        left_chunk = self.inputarr[start_y:stop_y, start_x:]
        wrap_chunk = self.inputarr[start_y:stop_y, :start_x]
        self.outputarr[start_y:stop_y, :stop_x] = left_chunk
        self.outputarr[start_y:stop_y, stop_x:] = wrap_chunk

    def __glitch_right(self, offset: int):
        """
         Grabs a rectange from inputarr and shifts it rightwards
         Any lost pixel data is wrapped back to the left
         Rectangle's Width and Height are determined from offset
         Consider an array like so-
         [[ 0, 1, 2, 3],
         [ 4, 5, 6, 7],
         [ 8, 9, 10, 11],
         [12, 13, 14, 15]]
         If we were to right shift the first row only, starting from
         the 0th index;
         i.e a rectangle of width = 3, height = 1 starting at (0, 0)
         We'd grab [0, 1, 2] and right shift it until the end of row
         so it'd look like [[0, 0, 1, 2]]
         Now we wrap around the lost values, i.e 3
         now it'd look like [[3, 0, 1, 2]]
         That's the end result!
        """
        # Setting up values that will determine the rectangle height
        start_y = random.randint(0, self.img_height)
        chunk_height = random.randint(1, int(self.img_height / 4))
        chunk_height = min(chunk_height, self.img_height - start_y)
        stop_y = start_y + chunk_height

        # For copy
        stop_x = self.img_width - offset
        # For paste
        start_x = offset

        right_chunk = self.inputarr[start_y:stop_y, :stop_x]
        wrap_chunk = self.inputarr[start_y:stop_y, stop_x:]
        self.outputarr[start_y:stop_y, start_x:] = right_chunk
        self.outputarr[start_y:stop_y, :start_x] = wrap_chunk

    def __color_offset(self, offset_x: int, offset_y: int, channel_index: int):
        """
         Takes the given channel's color value from inputarr,
         starting from (0, 0)
         and puts it in the same channel's slot in outputarr,
         starting from (offset_y, offset_x)
        """
        # Make sure offset_x isn't negative in the actual algo
        offset_x = offset_x if offset_x >= 0 else self.img_width + offset_x
        offset_y = offset_y if offset_y >= 0 else self.img_height + offset_y

        # Assign values from 0th row of inputarr to offset_y th row of outputarr
        # If outputarr's columns run out before inputarr's does, wrap the remaining values around
        self.outputarr[offset_y, offset_x:, channel_index] = self.inputarr[0, :self.img_width - offset_x, channel_index]
        self.outputarr[offset_y, :offset_x, channel_index] = self.inputarr[0, self.img_width - offset_x:, channel_index]

        # Continue afterwards till end of outputarr
        # Make sure the width and height match for both slices
        self.outputarr[offset_y + 1:, :, channel_index] = self.inputarr[1:self.img_height - offset_y, :, channel_index]

        # Restart from 0th row of outputarr and go until the offset_y th row
        # This will assign the remaining values in inputarr to outputarr
        self.outputarr[:offset_y, :, channel_index] = self.inputarr[self.img_height - offset_y:, :, channel_index]

    def __get_random_channel(self) -> int:
        # Returns a random index from 0 to pixel_tuple_len
        # For an RGB image, a 0th index represents the RED channel
        # For an RGB image, a 0th index represents the RED channel

        return random.randint(0, self.pixel_tuple_len - 1)

    def __reset_rng_seed(self, offset: int = 0):
        """
        Calls random.seed() with self.seed variable
        offset is for looping and getting new positions for each iteration that cointains the
        previous one, otherwise we would get the same position on every loop and different
        results afterwards on non fixed size loops
        """
        random.seed(self.seed + offset)

    def clamp(self, x, max, min=0):
        if x < min:
            return min
        elif x > max:
            return max
        else:
            return x

    def __glitch_effect_33(self, image):
        colors = ["#b4b2b5", "#dfd73f", "#6ed2dc", "#66cf5d", "#c542cb", "#d0535e", "#3733c9"]
        canvas_height = self.img_height
        canvas_width = self.img_width
        bnw_layer = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(bnw_layer)
        for i in range(1000):
            x0 = int(random.random() * canvas_width)
            y0 = int(random.random() * canvas_height)
            dx = int(random.random() * 25)
            dy = int(random.random() * 25)
            alpha_w = int(255 * 0.1 * random.random())
            alpha_b = int(255 * 0.1 * random.random())
            draw.rectangle([x0, y0, x0 + dx, y0 + dy], fill=(0, 0, 0, alpha_b))
            draw.rectangle([x0, y0, x0 + dx, y0 + dy], fill=(255, 255, 255, alpha_w))

        color_index = random.randint(0, 6)
        y = int(random.random() * canvas_height)
        x = int(random.random() * canvas_width)
        draw.rectangle([x, y, min(x + x, canvas_width), min(y + y, canvas_height)], fill=colors[color_index])

        return Image.alpha_composite(image, bnw_layer)

    def __glitch_effect_analog_noise(self, image: Image.Image, mean=0, stddev=30) -> Image.Image:

        def add_noise(x, mean, stddev):
            return min(max(0, x + random.normalvariate(mean, stddev)), 255)

        def add_noise_one_pixel(im, x, y, mean=0, stddev=50):
            pixel = im.getpixel((x, y))
            pixel = tuple(int(add_noise(channel, mean, stddev)) for channel in pixel)
            im.putpixel((x, y), pixel)

        for x in range(image.width):
            for y in range(image.height):
                add_noise_one_pixel(image, x, y, mean, stddev)
        return image

    def __rgb_split(self, image, mean=0, stddev=0.003) -> Image.Image:

        x_offset = random.normalvariate(mean, stddev) * image.width
        y_offset = random.normalvariate(mean, stddev) * image.height

        original = image.copy()

        width = image.width
        height = image.height
        for y in range(height):
            for x in range(width):
                image.putpixel((x, y),
                               (original.getpixel((self.clamp(x + x_offset, width - 1), self.clamp(y + y_offset, height - 1)))[0],
                                original.getpixel((self.clamp(x - x_offset, width - 1), self.clamp(y - y_offset, height - 1)))[1],
                                original.getpixel((self.clamp(x, width), self.clamp(y, height)))[2],
                                original.getpixel((x, y))[3]))
        return image

    def __tile_jittered(self, image, strip_height=50, mean=0, stddev=0.1) -> Image.Image:
        x_offset = random.normalvariate(mean, stddev) * image.width
        original = image.copy()

        width = image.width
        height = image.height
        was_jittered = False
        prev_strip = -1

        for y in range(height):
            current_strip = y // strip_height
            is_jittered = current_strip % 2 == 0
            if prev_strip != current_strip:
                x_offset = int(random.normalvariate(mean, stddev) * image.width)
            prev_strip = current_strip
            for x in range(width):
                if is_jittered:
                    image.putpixel((x, y), original.getpixel(((x + x_offset) % width, y)))
        return image

    def __screen_jump_effect(self, image, vertical=True):
        if not vertical:
            start_y = 0
            stop_y = self.img_height

            # For copy
            start_x = int(0.15 * self.img_width)
            # For paste
            stop_x = self.img_width - start_x

            left_chunk = self.outputarr[start_y:stop_y, start_x:]
            wrap_chunk = self.outputarr[start_y:stop_y, :start_x]
            self.outputarr[start_y:stop_y, :stop_x] = left_chunk
            self.outputarr[start_y:stop_y, stop_x:] = wrap_chunk
        else:
            start_x = 0
            stop_x = self.img_width

            # For copy
            start_y = int(0.15 * self.img_height)
            # For paste
            stop_y = self.img_height - start_y

            up_chunk = self.outputarr[start_y:, start_x:stop_x]
            wrap_chunk = self.outputarr[:start_y, start_x:stop_x]
            self.outputarr[:stop_y, start_x:stop_x] = up_chunk
            self.outputarr[stop_y:, start_x:stop_x] = wrap_chunk

        return Image.fromarray(self.outputarr, self.img_mode)

    def __screen_shake_effect(self, image, amplitude=5):
        start_y = 0
        stop_y = self.img_height

        # For copy
        offset = random.random()
        if offset < 0.5:
            offset = offset / amplitude
        else:
            offset = 1 - offset / amplitude

        start_x = int(offset * self.img_width)
        # For paste
        stop_x = self.img_width - start_x
        shake_array = self.outputarr.copy()

        left_chunk = self.outputarr[start_y:stop_y, start_x:]
        wrap_chunk = self.outputarr[start_y:stop_y, :start_x]
        shake_array[start_y:stop_y, :stop_x] = left_chunk
        shake_array[start_y:stop_y, stop_x:] = wrap_chunk

        return Image.fromarray(shake_array, self.img_mode)

    def __image_block(self, image, color_effect=True,
                      num_mean=20, num_stddev=10,
                      size_mean=0.09, size_stddev=0.03,
                      offset_mean=0, offset_stddev=0.05) -> Image.Image:
        original = image.copy()
        block_num = int(random.normalvariate(num_mean, num_stddev))
        height = image.height
        width = image.width
        colors = ["#b4b2b5", "#dfd73f", "#6ed2dc", "#66cf5d", "#c542cb", "#d0535e", "#3733c9"]

        for _ in range(block_num):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)

            len_x = int(random.normalvariate(size_mean, size_stddev) * width)
            len_y = int(random.normalvariate(size_mean, size_stddev) * height)

            offset_x = int(random.normalvariate(offset_mean, offset_stddev) * width)
            offset_y = int(random.normalvariate(offset_mean, offset_stddev) * height)

            color = np.random.randint(3, size=4).tolist()

            if color_effect:
                for j in range(y, y + len_y):
                    for i in range(x, x + len_x):
                        image.putpixel((self.clamp(i, width - 1, 0), self.clamp(j, height - 1, 0)),
                                       tuple(min(m * n, 255) for (m, n) in zip(color,
                                                                      original.getpixel(((i + offset_x) % width,
                                                                                         (j + offset_y) % height)))))
            else:
                for j in range(y, y + len_y):
                    for i in range(x, x + len_x):
                        image.putpixel((self.clamp(i, width - 1, 0), self.clamp(j, height - 1, 0)),
                                       original.getpixel(((i + offset_x) % width, (j + offset_y) % height)))
        return image
